"""Step 9 - quality control: seam/discontinuity scan of the rendered cycle + final file checks."""
from __future__ import annotations

import json
import re
import subprocess

import numpy as np

from . import ff
from .config import Project

QW, QH = 160, 90


def keyframes(path, fps: float) -> set[int]:
    p = subprocess.run([ff.FFPROBE, "-v", "error", "-skip_frame", "nokey", "-select_streams", "v:0",
                        "-show_entries", "frame=pts_time", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    vals = [x.strip(", ") for x in p.stdout.split()]
    return {int(round(float(x) * fps)) for x in vals if x and x != "N/A"}


def clip_at(tl: dict, frame: int) -> str:
    for u in tl["units"]:
        if u["start"] <= frame < u["start"] + u["body"]:
            return u["clip"]
        if u["start"] + u["body"] <= frame < u["start"] + u["body"] + tl["T"]:
            return f"dissolve out of {u['clip']}"
    return "?"


def scan_cycle(path, fps: float, events: list[dict], C: int, preview: bool = False) -> dict:
    prev, first, diffs = None, None, []
    for chunk in ff.iter_frames(path, QW, QH, "gray"):
        c = chunk.astype(np.float32)
        if first is None:
            first = c[0]
        if prev is not None:
            diffs.append(float(np.mean(np.abs(c[0] - prev))))
        diffs.extend(np.mean(np.abs(np.diff(c, axis=0)), axis=(1, 2)).tolist())
        prev = c[-1]
    wrap = float(np.mean(np.abs(first - prev)))
    d = np.array([wrap] + diffs)           # d[k] = change from frame k-1 into frame k (k=0 is the wrap)
    n = len(d)
    win = int(2 * fps)

    def local(k):
        idx = [(k + o) % n for o in range(-win, win + 1) if abs(o) > 3]
        return float(np.median(d[idx])) + 0.05

    kf = keyframes(path, fps) if preview else set()
    # Low-bitrate previews 'pulse' on keyframes; that is a preview-only encoder effect.
    pulse = lambda k, jump, ratio: preview and k in kf and jump < 6.0   # real footage pulses ~4.5 at 360p
    results, flagged_frames, pulses = [], set(), 0
    for e in events:
        k = e["frame"] % n
        near = [(k + o) % n for o in range(-1, 2)]
        peak = max(d[x] for x in near)
        ratio = peak / local(k)
        bad = ratio > 3.0 and peak > 1.0
        if bad and any(pulse(x, d[x], d[x] / local(x)) for x in near if d[x] == peak):
            bad, pulses = False, pulses + 1
        results.append({**e, "t": round(e["frame"] / fps, 3), "jump": round(peak, 2),
                        "x_local": round(ratio, 2), "flag": bad})
        flagged_frames.update(near)
    # spikes anywhere else = artifacts carried over from the source clips
    unexplained = []
    for k in range(n):
        if k in flagged_frames:
            continue
        lm = local(k)
        if d[k] / lm > 4.0 and d[k] > 2.0:
            if pulse(k, d[k], d[k] / lm):
                pulses += 1
                continue
            unexplained.append({"frame": k, "t": round(k / fps, 3), "jump": round(float(d[k]), 2),
                                "x_local": round(float(d[k] / lm), 1)})
    return {"frames": n, "expected_frames": C, "median_motion": round(float(np.median(d)), 3),
            "events": results, "unexplained_spikes": unexplained, "keyframe_pulses": pulses}


def loudness(path) -> dict:
    err = ff.run(["-i", str(path), "-map", "0:a:0", "-af", "ebur128=peak=true", "-f", "null", "-"],
                 desc="ebur128", capture=True)
    summ = err[err.rfind("Summary:"):]
    I = re.search(r"I:\s+(-?[\d.]+) LUFS", summ)
    LRA = re.search(r"LRA:\s+(-?[\d.]+) LU", summ)
    TP = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summ)
    return {"integrated_lufs": float(I.group(1)) if I else None, "lra": float(LRA.group(1)) if LRA else None,
            "true_peak_dbtp": float(TP.group(1)) if TP and TP.group(1) != "-inf" else None}


def run(proj: Project, final: bool = False) -> dict:
    tl = proj.load_json("work/timeline.json")
    fps = tl["fps"]
    name = "final" if final else "preview"
    cycle = proj.work / f"render_{name}" / "cycle.mp4"
    if not cycle.exists():
        raise SystemExit(f"No {name} cycle rendered yet. Run: ./ds {'render' if final else 'preview'} <project>")
    print(f"  scanning {name} cycle for discontinuities ...")
    scan = scan_cycle(cycle, fps, tl["events"], tl["C"], preview=not final)
    for sp in scan["unexplained_spikes"]:
        sp["clip"] = clip_at(tl, sp["frame"])
    rep = {"profile": name, "scan": scan, "checks": []}
    chk = rep["checks"]
    chk.append(("cycle frame count", scan["frames"] == tl["C"], f"{scan['frames']} / {tl['C']}"))
    bad = [e for e in scan["events"] if e["flag"]]
    chk.append(("seams (dissolves, loop wraps, joins, cycle wrap)", not bad,
                f"{len(scan['events']) - len(bad)}/{len(scan['events'])} clean"))
    chk.append(("no unexplained frame jumps", not scan["unexplained_spikes"],
                f"{len(scan['unexplained_spikes'])} found"))
    an = proj.load_json("work/analysis.json")
    used = {u["clip"] for u in tl["units"]}
    src_issues = {c: a["issues"] for c, a in an["clips"].items() if c in used and a["issues"]}
    chk.append(("source clips free of detected artifacts", not src_issues, f"{len(src_issues)} clip(s) with issues"))

    if final:
        fj = proj.load_json("work/final.json")
        info = ff.probe(fj["file"])
        vs, as_ = ff.video_stream(info), ff.audio_stream(info)
        dur = float(info["format"]["duration"])
        chk.append(("duration", abs(dur - proj.duration) < 1.0, f"{dur:.2f}s vs target {proj.duration:.0f}s"))
        chk.append(("video stream", bool(vs) and int(vs["width"]) == int(proj.video["width"]),
                    f"{vs.get('codec_name')} {vs.get('width')}x{vs.get('height')} {vs.get('avg_frame_rate')}"
                    if vs else "missing"))
        chk.append(("audio stream", bool(as_), f"{as_.get('codec_name')} {as_.get('sample_rate')} Hz "
                    f"{as_.get('channels')}ch" if as_ else "missing"))
        if as_:
            vd = float(vs.get("duration", dur)) if vs else dur
            ad = float(as_.get("duration", dur))
            chk.append(("audio/video length match", abs(vd - ad) < 0.5, f"video {vd:.2f}s audio {ad:.2f}s"))
            print("  measuring final loudness (decodes the whole audio track) ...")
            L = loudness(fj["file"])
            rep["loudness"] = L
            tgt = float(proj.cfg["audio"]["target_lufs"])
            okL = L["integrated_lufs"] is not None and abs(L["integrated_lufs"] - tgt) <= 1.0
            chk.append(("loudness", okL, f"{L['integrated_lufs']} LUFS (target {tgt}), "
                        f"peak {L['true_peak_dbtp']} dBTP"))
    aj = proj.work / "audio" / f"mix_{name}.json"
    if aj.exists():
        a = json.loads(aj.read_text())
        bad_a = [f for f, s in a["layer_seams"].items() if not s["ok"]]
        chk.append(("audio layer loop seams", not bad_a, ", ".join(bad_a) or "all clean"))
        rep["audio"] = a
    rep["checks"] = [{"check": c, "pass": bool(p), "detail": d} for c, p, d in chk]
    advisory = {"source clips free of detected artifacts"}
    rep["pass"] = all(c["pass"] for c in rep["checks"] if c["check"] not in advisory)
    proj.save_json(f"out/reports/qc_{name}.json", rep)
    write_md(proj, rep, src_issues, fps)
    return rep


def write_md(proj, rep, src_issues, fps):
    L = [f"# QC report ({rep['profile']}) - {proj.cfg['project']['title']}", "",
         f"**Overall: {'PASS' if rep['pass'] else 'NEEDS ATTENTION'}** "
         "(source-clip artifacts are advisory - review them in the preview)", "",
         "| check | result | detail |", "|---|---|---|"]
    for c in rep["checks"]:
        L.append(f"| {c['check']} | {'pass' if c['pass'] else '**FAIL**'} | {c['detail']} |")
    L += ["", "## Seams", "", "Jump = mean pixel change into that frame (0-255). x-local = jump / normal motion "
          "around it; >3 is flagged as a visible discontinuity.", "",
          "| time | seam | jump | x-local | status |", "|---|---|---|---|---|"]
    for e in rep["scan"]["events"]:
        if e["kind"] == "segment join" and not e["flag"]:
            continue
        L.append(f"| {e['t']:.2f}s | {e['kind']} | {e['jump']} | {e['x_local']} | "
                 f"{'**VISIBLE**' if e['flag'] else 'clean'} |")
    joins = [e for e in rep["scan"]["events"] if e["kind"] == "segment join"]
    L.append(f"\nSegment joins (stream-copy boundaries): {sum(not e['flag'] for e in joins)}/{len(joins)} clean.")
    if rep["scan"]["unexplained_spikes"]:
        L += ["", "## Frame jumps not at a seam (source artifacts)", ""]
        L += [f"- {s['t']:.2f}s in **{s['clip']}**: jump {s['jump']} ({s['x_local']}x local motion)"
              for s in rep["scan"]["unexplained_spikes"][:50]]
    if rep["scan"].get("keyframe_pulses"):
        L += ["", f"Preview-only: {rep['scan']['keyframe_pulses']} small keyframe 'pulses' from the low-bitrate "
              "preview encoder were ignored (not present at final quality; `./ds qc <project> --final` checks)."]
    if src_issues:
        L += ["", "## Source clip issues (from analysis)", ""]
        L += [f"- **{c}**: " + "; ".join(i) for c, i in src_issues.items()]
    if "audio" in rep:
        L += ["", "## Audio", "", f"- mix: {rep['audio']['output_i']} LUFS integrated, "
              f"{rep['audio']['output_tp']} dBTP ({rep['audio']['normalization_type']} normalisation)"]
        for f, s in rep["audio"]["layer_seams"].items():
            L.append(f"- loop seam `{f}`: click x{s['click_ratio']}, level step {s['level_step_db']} dB "
                     f"-> {'clean' if s['ok'] else '**AUDIBLE?**'}")
    L += ["", "Not machine-checkable: AI morphing/warping, physically wrong motion, visible watermarks, "
          "and whether a dissolve 'ghosts' two very different scenes. Watch out/seams_review.mp4."]
    path = proj.p("out", "reports", f"qc_{rep['profile']}.md")
    path.write_text("\n".join(L) + "\n")
    print(f"  QC {'PASS' if rep['pass'] else 'NEEDS ATTENTION'} -> {path}")
