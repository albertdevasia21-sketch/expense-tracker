"""Step 2 - analyse: loop compatibility, best loop points, source artifacts, clip-to-clip fit.

All metrics run on 160x90 greyscale frames (~14 KB each), so a 10 s clip costs
a few MB of RAM even if the source is 4K.
"""
from __future__ import annotations

import numpy as np

from . import ff
from .config import Project

AW, AH = 160, 90


def _rolling_median(x: np.ndarray, win: int) -> np.ndarray:
    if len(x) == 0:
        return x
    half = max(1, win // 2)
    pad = np.pad(x, half, mode="edge")
    return np.array([np.median(pad[i:i + 2 * half + 1]) for i in range(len(x))])


def frame_diff(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a.astype(np.float32) - b.astype(np.float32))))


def find_loop_points(f: np.ndarray, fps: float) -> tuple[int, int, float]:
    """Choose loop [i, j) so frame j (the frame that 'would' follow j-1) matches frame i."""
    n = len(f)
    head = range(0, max(1, min(int(fps * 1.0), int(n * 0.12))))
    tail = range(max(n - max(2, min(int(fps * 1.5), int(n * 0.15))), 1), n)
    min_len = int(n * 0.7)
    ff32 = f.astype(np.float32)
    best = (0, n - 1, float("inf"))
    for i in head:
        for j in tail:
            if j - i < min_len:
                continue
            c = float(np.mean(np.abs(ff32[j] - ff32[i])))
            if c < best[2]:
                best = (i, j, c)
    return best


def analyse_clip(path, fps: float) -> dict:
    g = ff.read_frames(path, AW, AH, "gray")
    rgb = ff.read_frames(path, 32, 18, "rgb24")
    n = len(g)
    if n < 8:
        return {"frames": n, "grade": "F", "issues": ["clip too short to analyse"], "mode": "oneshot"}
    gf = g.astype(np.float32)
    d = np.mean(np.abs(np.diff(gf, axis=0)), axis=(1, 2))          # motion per frame step
    motion = float(np.median(d)) + 1e-3
    issues: list[str] = []

    # --- artifacts ------------------------------------------------------
    rm = _rolling_median(d, int(fps))
    spike_idx = np.where(d > np.maximum(3.5 * rm, rm + 2.5))[0]
    spikes = [{"t": round((k + 1) / fps, 3), "jump": round(float(d[k]), 2),
               "x_normal": round(float(d[k] / (rm[k] + 1e-3)), 1)} for k in spike_idx]
    if spikes:
        issues.append(f"{len(spikes)} sudden frame jump(s) (cut/flash/morph glitch) at "
                      + ", ".join(f"{s['t']:.2f}s" for s in spikes[:6]))
    luma = gf.mean(axis=(1, 2))
    k = max(3, int(fps))
    smooth = np.convolve(np.pad(luma, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), mode="same")[k:-k]
    flicker = float(np.std(luma - smooth))
    if flicker > 1.5:
        issues.append(f"brightness flicker (std {flicker:.2f} levels)")
    drift = float(luma[-int(fps):].mean() - luma[:int(fps)].mean())
    if abs(drift) > 6:
        issues.append(f"exposure drift {drift:+.1f} levels start->end (loop seam will 'pulse')")
    black = int(np.sum(luma < 12))
    if black:
        issues.append(f"{black} near-black frame(s)")
    still = d < 0.05
    run_len, longest = 0, 0
    for s in still:
        run_len = run_len + 1 if s else 0
        longest = max(longest, run_len)
    if longest >= int(fps * 0.5):
        issues.append(f"frozen frames for {longest / fps:.2f}s")

    # --- loopability ----------------------------------------------------
    i, j, cost = find_loop_points(g, fps)
    seam_ratio = cost / motion
    # 'progressive' motion: does the picture keep drifting away from itself (camera move,
    # zoom, evolving scene) or does it hover around a steady state (fog, water, rain)?
    short_lag = max(1, min(int(fps), n // 6))
    long_lag = max(short_lag + 1, int(n * 0.6))
    def lag_diff(L):
        idx = np.arange(0, n - L, max(1, (n - L) // 40))
        return float(np.mean([np.mean(np.abs(gf[t + L] - gf[t])) for t in idx]))
    progressive = lag_diff(long_lag) / (lag_diff(short_lag) + 1e-3)

    # Static-scene check: average 1 s at each end (blurs moving rain/fog/water, keeps trees,
    # rocks, horizon) and correlate the edge maps. ~1.0 = locked-off camera and unchanged
    # scenery, so a crossfade loop only has to hide the moving elements. Calibrated on real
    # Gemini/Veo clips (0.93-0.98) vs a slow zoom (0.62).
    def _edges(m):
        gx = m[:, 2:] - m[:, :-2]
        gy = m[2:, :] - m[:-2, :]
        return np.hypot(gx[1:-1, :], gy[:, 1:-1]).ravel()
    k1 = max(2, int(fps))
    ea, eb = _edges(gf[:k1].mean(axis=0)), _edges(gf[-k1:].mean(axis=0))
    structure = float(np.corrcoef(ea, eb)[0, 1]) if ea.std() > 1e-3 and eb.std() > 1e-3 else 0.0
    static_scene = structure >= 0.85

    # Grade = how natural a crossfade loop will look. A stationary texture (water, rain,
    # fog) dissolves into itself invisibly even when the two frames differ; a drifting or
    # evolving shot visibly "resets" at every loop.
    if seam_ratio <= 1.5:
        grade = "A"
    elif (progressive <= 1.6 or static_scene) and abs(drift) <= 6:
        grade = "B"
    elif static_scene and abs(drift) <= 12:
        grade = "C"
    elif progressive <= 2.2 and abs(drift) <= 12:
        grade = "C"
    else:
        grade = "D"
    if spikes and grade < "D":
        grade = chr(ord(grade) + 1)
    mode = "loop" if grade in ("A", "B", "C") else "oneshot"
    if motion < 0.15:
        issues.append("almost no motion: loop will look like a still image")
    if progressive > 2.2 and not static_scene:
        issues.append(f"progressive motion x{progressive:.1f} (camera move/zoom or evolving scene): "
                      "a self-loop would visibly reset -> auto mode uses it once per cycle (oneshot); "
                      "set mode = \"loop\" if the reset is acceptable (e.g. soft fog)")

    # colour signature of the loop's head and tail (for clip ordering)
    def hist(frames):
        h = [np.histogram(frames[..., c], bins=8, range=(0, 256))[0] for c in range(3)]
        h = np.concatenate(h).astype(np.float64)
        return (h / h.sum()).round(5).tolist()
    sec = max(1, int(fps))
    return {
        "frames": n, "motion": round(motion, 3), "flicker": round(flicker, 3),
        "exposure_drift": round(drift, 2), "spikes": spikes,
        "loop_in": int(i), "loop_out": int(j), "seam_cost": round(cost, 3),
        "seam_ratio": round(seam_ratio, 2), "progressive": round(progressive, 2), "structure": round(structure, 3),
        "grade": grade, "mode": mode, "issues": issues,
        "head_hist": hist(rgb[:sec]), "tail_hist": hist(rgb[-sec:]),
        "head_luma": round(float(luma[:sec].mean()), 2), "tail_luma": round(float(luma[-sec:].mean()), 2),
    }


def compat(a: dict, b: dict) -> float:
    """Cost of dissolving from clip a's tail into clip b's head (0 = identical look)."""
    ha, hb = np.array(a["tail_hist"]), np.array(b["head_hist"])
    return round(float(np.abs(ha - hb).sum() / 2 + abs(a["tail_luma"] - b["head_luma"]) / 64), 4)


GRADE_TEXT = {
    "A": "seamless - loop points match naturally",
    "B": "good - short crossfade hides the seam",
    "C": "fair - crossfade works, mild ghosting possible",
    "D": "poor - not self-loopable; used once per cycle with dissolves",
    "E": "poor - not self-loopable; used once per cycle with dissolves",
    "F": "unusable",
}


def run(proj: Project) -> dict:
    manifest = proj.load_json("work/manifest.json")
    fps = float(proj.video["fps"])
    res = {}
    for cid, c in manifest["clips"].items():
        print(f"  analyse {cid}")
        a = analyse_clip(proj.root / c["mezz"], fps)
        a["import_notes"] = c.get("notes", [])
        override = proj.clip_cfg(cid).get("mode") or (proj.video["mode"] if proj.video["mode"] != "auto" else None)
        a["mode_auto"] = a["mode"]
        if override:
            a["mode"] = override
        cc = proj.clip_cfg(cid)
        if "exclude" in cc:
            a["excluded"] = bool(cc["exclude"])
        else:  # flashes / jump cuts are unacceptable in a relaxation video -> opt back in explicitly
            a["excluded"] = a["grade"] == "F" or bool(a.get("spikes"))
            if a.get("spikes"):
                a["issues"].append("auto-excluded because of frame jumps (set [clips.%s] exclude = false "
                                   "to use anyway)" % cid)
        res[cid] = a
    ids = list(res)
    matrix = {x: {y: compat(res[x], res[y]) for y in ids if y != x} for x in ids}
    data = {"fps": fps, "clips": res, "compat": matrix}
    proj.save_json("work/analysis.json", data)
    write_report(proj, data)
    return data


def write_report(proj: Project, data: dict) -> None:
    fps = data["fps"]
    lines = [f"# Loop analysis - {proj.cfg['project']['title']}", "",
             "| clip | len | grade | mode | seam x-motion | progressive | static | loop in-out | issues |",
             "|---|---|---|---|---|---|---|---|---|"]
    for cid, a in data["clips"].items():
        loop = f"{a.get('loop_in', 0) / fps:.2f}-{a.get('loop_out', 0) / fps:.2f}s"
        iss = "; ".join(a["issues"] + a.get("import_notes", [])) or "-"
        mode = a["mode"] + (" (excluded)" if a["excluded"] else "")
        lines.append(f"| {cid} | {a['frames'] / fps:.1f}s | {a['grade']} | {mode} | {a.get('seam_ratio', '-')} | "
                     f"{a.get('progressive', '-')} | {a.get('structure', '-')} | {loop} | {iss} |")
    lines += ["", "**Grades:** " + "; ".join(f"{g} = {t}" for g, t in GRADE_TEXT.items() if g != "E"), "",
              "*seam x-motion*: difference between the chosen loop end and start, as a multiple of the clip's "
              "normal frame-to-frame motion (1.0 = indistinguishable from a normal frame step).", "",
              "*progressive*: how far the picture drifts from itself over the clip (>2.2 = camera move / "
              "evolving scene).", "",
              "*static*: how well the fixed scenery (trees, rocks, horizon) lines up between the start and "
              "end of the clip (>=0.85 = locked-off camera; such clips loop well even with drifting fog).", "",
              "Automated checks catch cuts, flashes, flicker, exposure drift, freezes and black frames. They "
              "**cannot** judge AI morphing (warping objects, melting textures, physics errors) - review the "
              "preview for those.", ""]
    proj.p("out", "reports", "analysis.md").write_text("\n".join(lines))
    print(f"  report: {proj.out / 'reports' / 'analysis.md'}")
