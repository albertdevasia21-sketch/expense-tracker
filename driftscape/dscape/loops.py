"""Step 3 - build per-clip loop sources.

loop     : body [in, out) with its tail dissolved into its head -> seamless when repeated
oneshot  : whole clip, never repeated back-to-back (entered and left with dissolves)
pingpong : forward then reversed (smooth, but reversed motion; review rain/snow/fire!)

Inputs are opened several times with -ss instead of split/buffer, so memory
stays flat even for 4K sources.
"""
from __future__ import annotations

from . import ff
from .config import Project, file_sig, is_fresh, mark_fresh
from .encode import mezz_args


def build_loop(src, out, i: int, j: int, xf: int, fps: float, v: dict) -> None:
    n = j - i
    t = lambda fr: f"{fr / fps:.6f}"
    ss = lambda fr: f"{max(0.0, (fr - 0.5) / fps):.6f}"   # half-frame early: frame-exact seek
    # tail = frames [j-xf, j), head = [i, i+xf), body = [i+xf, j-xf)
    fc = (f"[0:v]trim=end_frame={xf},setpts=PTS-STARTPTS[tail];"
          f"[1:v]trim=end_frame={xf},setpts=PTS-STARTPTS[head];"
          f"[tail][head]xfade=transition=fade:duration={t(xf)}:offset=0[seam];"
          f"[2:v]trim=end_frame={n - 2 * xf},setpts=PTS-STARTPTS[body];"
          f"[seam][body]concat=n=2:v=1:a=0,fps={fps:g}[v]")
    ff.run(["-ss", ss(j - xf), "-i", str(src), "-ss", ss(i), "-i", str(src), "-ss", ss(i + xf), "-i", str(src),
            "-filter_complex", fc, "-map", "[v]", "-frames:v", str(n - xf)] + mezz_args(v) + [str(out)],
           desc="build loop")


def build_oneshot(src, out, v: dict) -> None:
    ff.run(["-i", str(src), "-map", "0:v:0"] + mezz_args(v) + [str(out)], desc="oneshot")


def build_pingpong(src, out, i: int, j: int, fps: float, v: dict) -> None:
    n = j - i
    fc = (f"[0:v]trim=start_frame={i}:end_frame={j},setpts=PTS-STARTPTS,split[a][b];"
          f"[b]reverse,trim=start_frame=1:end_frame={n - 1},setpts=PTS-STARTPTS[r];"
          f"[a][r]concat=n=2:v=1:a=0[v]")
    if int(v["width"]) > 2000:
        print("    note: pingpong buffers the clip in RAM; at 4K this can use ~3 GB")
    ff.run(["-i", str(src), "-filter_complex", fc, "-map", "[v]"] + mezz_args(v) + [str(out)], desc="pingpong")


def run(proj: Project) -> dict:
    v = proj.video
    fps = float(v["fps"])
    manifest = proj.load_json("work/manifest.json")
    an = proj.load_json("work/analysis.json")
    ext = ".mov" if v.get("mezz_codec") == "prores" else ".mp4"
    built = {}
    for cid, a in an["clips"].items():
        if a["excluded"]:
            print(f"  skip {cid} (excluded)")
            continue
        src = proj.root / manifest["clips"][cid]["mezz"]
        mode = a["mode"]
        i, j = a["loop_in"], a["loop_out"]
        cc = proj.clip_cfg(cid)
        i = int(round(cc.get("loop_in", i / fps) * fps)) if "loop_in" in cc else i
        j = int(round(cc.get("loop_out", j / fps) * fps)) if "loop_out" in cc else j
        xf = int(round(min(float(cc.get("loop_crossfade", v["loop_crossfade"])) * fps, (j - i) / 4)))
        xf = max(2, xf)
        out = proj.p("work", "loops", cid + ext)
        spec = {"src": file_sig(src), "mode": mode, "i": i, "j": j, "xf": xf, "codec": mezz_args(v)}
        if not is_fresh(out, spec):
            print(f"  {mode:8s} {cid}")
            if mode == "loop":
                build_loop(src, out, i, j, xf, fps, v)
            elif mode == "pingpong":
                build_pingpong(src, out, i, j, fps, v)
            else:
                build_oneshot(src, out, v)
            mark_fresh(out, spec)
        else:
            print(f"  cached   {cid}")
        frames = ff.count_frames(out)
        expected = {"loop": (j - i) - xf, "pingpong": 2 * (j - i) - 2, "oneshot": a["frames"]}[mode]
        if frames != expected:
            raise SystemExit(f"Loop build for {cid} produced {frames} frames, expected {expected}")
        built[cid] = {"file": str(out.relative_to(proj.root)), "mode": mode, "frames": frames,
                      "loop_in": i, "loop_out": j, "xf": xf}
    if not built:
        raise SystemExit("No usable clips after analysis.")
    proj.save_json("work/loops.json", built)
    return built
