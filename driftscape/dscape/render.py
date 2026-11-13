"""Steps 5/6 - render preview and final video from the timeline.

Only the unique cycle (default 10 min) is encoded, one short segment at a time
(low RAM, resumable: finished segments are cached by content hash). The
3-hour file is then assembled by stream copy, which costs almost no CPU.
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

from . import audio, ff
from .config import Project, file_sig, is_fresh, mark_fresh, spec_hash
from .encode import delivery_args


def _profile(proj: Project, preview: bool):
    v = proj.video
    if preview:
        p = proj.cfg["preview"]
        return "preview", int(p["width"]), int(p["height"]), delivery_args(v, p)
    return "final", int(v["width"]), int(v["height"]), delivery_args(v)


def _src_trim(loops: dict, proj: Project, cid: str, start: int, length: int):
    """Input args + trim filter for `length` frames of clip cid's stream from `start`."""
    L = loops[cid]
    f = str(proj.root / L["file"])
    if L["mode"] == "oneshot":
        if start + length > L["frames"]:
            raise SystemExit(f"timeline overran oneshot clip {cid}")
        return [], f, start
    s = start % L["frames"]
    return ["-stream_loop", "-1"], f, s


def render_segment(proj: Project, loops: dict, seg: dict, prof, out: Path, fx: str = "") -> None:
    name, W, H, enc = prof
    fps = float(proj.video["fps"])
    scale = f"scale={W}:{H}:flags=bicubic" if (W, H) != (int(proj.video["width"]), int(proj.video["height"])) else "null"
    n = seg["len"]
    if seg["type"] == "body":
        ia, f, s = _src_trim(loops, proj, seg["clip"], seg["s"], n)
        fc = f"[0:v]trim=start_frame={s}:end_frame={s + n},setpts=PTS-STARTPTS,{scale}{fx},format=yuv420p[v]"
        inputs = ia + ["-i", f]
    else:
        ia, fa, sa = _src_trim(loops, proj, seg["a"], seg["sa"], n)
        ib, fb, sb = _src_trim(loops, proj, seg["b"], 0, n)
        fc = (f"[0:v]trim=start_frame={sa}:end_frame={sa + n},setpts=PTS-STARTPTS[a];"
              f"[1:v]trim=start_frame={sb}:end_frame={sb + n},setpts=PTS-STARTPTS[b];"
              f"[a][b]xfade=transition=fade:duration={n / fps:.6f}:offset=0,{scale}{fx},format=yuv420p[v]")
        inputs = ia + ["-i", fa] + ib + ["-i", fb]
    tmp = out.with_suffix(".part.mp4")
    ff.run(inputs + ["-filter_complex", fc, "-map", "[v]", "-frames:v", str(n), "-r", f"{fps:g}", "-an"]
           + enc + [str(tmp)], desc=f"segment {out.name}")
    got = ff.count_frames(tmp)
    if got != n:
        raise SystemExit(f"segment {out.name}: {got} frames, expected {n}")
    tmp.replace(out)


def _concat(files: list[Path], listfile: Path, out: Path, extra: list[str] | None = None,
            long_running=False) -> None:
    listfile.write_text("".join(f"file '{f.resolve()}'\n" for f in files))
    ff.run(["-f", "concat", "-safe", "0", "-i", str(listfile)] + (extra or ["-map", "0:v", "-c", "copy"])
           + [str(out)], desc=f"concat {out.name}", long_running=long_running)


def build_cycle(proj: Project, tl: dict, preview: bool) -> dict:
    loops = proj.load_json("work/loops.json")
    prof = _profile(proj, preview)
    name = prof[0]
    fps = float(proj.video["fps"])
    wdir = proj.work / f"render_{name}"
    wdir.mkdir(parents=True, exist_ok=True)
    seg_files = []
    t0 = time.time()
    total = len(tl["segments"])
    for k, seg in enumerate(tl["segments"]):
        L = [loops[c] for c in ([seg["clip"]] if seg["type"] == "body" else [seg["a"], seg["b"]])]
        spec = {"seg": {x: y for x, y in seg.items() if x != "at"}, "prof": prof,
                "src": [file_sig(proj.root / l["file"]) for l in L]}
        out = wdir / f"seg_{spec_hash(spec)}.mp4"
        if not is_fresh(out, spec):
            print(f"  [{name}] segment {k + 1}/{total} {seg['type']:5s} {seg['len'] / fps:5.1f}s")
            render_segment(proj, loops, seg, prof, out)
            mark_fresh(out, spec)
        seg_files.append(out)
    # intro variant of the first body (fade from black) and the outro tail (fade to black)
    s0 = tl["segments"][0]
    fi = tl["fade_in"] / fps
    intro_spec = {"intro": s0, "prof": prof, "fi": fi, "src": file_sig(seg_files[0])}
    intro = wdir / f"intro_{spec_hash(intro_spec)}.mp4"
    if not is_fresh(intro, intro_spec):
        print(f"  [{name}] intro (fade in {fi:.1f}s)")
        render_segment(proj, loops, s0, prof, intro, fx=f",fade=t=in:st=0:d={fi:.3f}" if fi > 0 else "")
        mark_fresh(intro, intro_spec)
    first = tl["units"][0]["clip"]
    outro_seg = {"type": "body", "clip": first, "s": tl["T"], "len": tl["outro"]}
    fo = tl["outro"] / fps
    outro_spec = {"outro": outro_seg, "prof": prof, "src": file_sig(proj.root / loops[first]["file"])}
    outro = wdir / f"outro_{spec_hash(outro_spec)}.mp4"
    if tl["outro"] > 0 and not is_fresh(outro, outro_spec):
        print(f"  [{name}] outro (fade out {fo:.1f}s)")
        render_segment(proj, loops, outro_seg, prof, outro, fx=f",fade=t=out:st=0:d={fo:.3f}")
        mark_fresh(outro, outro_spec)
    cycle = wdir / "cycle.mp4"
    cyc_spec = [str(f) for f in seg_files]
    if not is_fresh(cycle, cyc_spec):
        _concat(seg_files, wdir / "cycle.txt", cycle)
        mark_fresh(cycle, cyc_spec)
    got = ff.count_frames(cycle)
    if got != tl["C"]:
        raise SystemExit(f"cycle has {got} frames, expected {tl['C']}")
    print(f"  [{name}] cycle ready: {cycle} ({time.time() - t0:.0f}s)")
    return {"cycle": cycle, "intro": intro, "outro": outro if tl["outro"] > 0 else None,
            "segs": seg_files, "wdir": wdir}


def _gb(b: float) -> str:
    return f"{b / 1e9:.1f} GB"


def preview(proj: Project) -> Path:
    from . import sequence
    tl = sequence.plan(proj)
    r = build_cycle(proj, tl, preview=True)
    fps = float(proj.video["fps"])
    extra = float(proj.cfg["preview"]["extra_seconds"])
    dur = min(tl["C"] / fps + extra, tl["D"] / fps)
    mix = audio.render_mix(proj, dur, proj.p("work", "audio", "mix_preview.m4a"), preview=True)
    files = [r["intro"]] + r["segs"][1:] + [r["cycle"]]
    out = proj.p("out", "preview.mp4")
    extra_args = ["-i", str(mix), "-map", "0:v", "-map", "1:a", "-c", "copy", "-t", f"{dur:.3f}",
                  "-movflags", "+faststart"]
    _concat(files, r["wdir"] / "preview.txt", out, extra_args)
    print(f"  preview: {out} ({dur / 60:.1f} min - full visual cycle + wrap-around)")
    seams_reel(proj, tl, r["cycle"])
    return out


def seams_reel(proj: Project, tl: dict, cycle: Path, max_events: int = 40) -> Path | None:
    """Short reel: 2 s before -> 2 s after every dissolve / loop wrap / cycle wrap."""
    fps = tl["fps"]
    C = tl["C"]
    events = [e for e in tl["events"] if e["kind"] != "segment join"][:max_events]
    wdir = proj.work / "render_preview" / "seams"
    if wdir.exists():
        shutil.rmtree(wdir)
    wdir.mkdir(parents=True)
    text_ok = ff.has_filter("drawtext")
    parts = []
    for k, e in enumerate(events):
        start = (e["frame"] - 2 * fps) / fps
        label = f"{e['kind']} @ {e['frame'] / fps:.1f}s".replace(":", r"\:").replace("'", "")
        dt = (f",drawtext=text='{label}':x=10:y=h-30:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.5"
              if text_ok else "")
        out = wdir / f"e{k:03d}.mp4"
        # double the cycle so windows that straddle the wrap work
        inp = ["-stream_loop", "1", "-ss", f"{start % (C / fps):.3f}", "-i", str(cycle)]
        ff.run(inp + ["-t", "4", "-vf", f"null{dt}", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                      "-pix_fmt", "yuv420p", str(out)], desc="seam clip")
        parts.append(out)
    if not parts:
        return None
    reel = proj.p("out", "seams_review.mp4")
    _concat(parts, wdir / "list.txt", reel)
    print(f"  seam review reel: {reel} ({len(parts)} seams x 4 s)")
    return reel


def final(proj: Project) -> Path:
    from . import sequence
    audio.require_licenses(proj)
    tl = sequence.plan(proj)
    r = build_cycle(proj, tl, preview=False)
    fps = tl["fps"]
    D = tl["D"] / fps
    mix = audio.render_mix(proj, D, proj.p("work", "audio", "mix_final.m4a"))
    cyc_size = r["cycle"].stat().st_size
    est = cyc_size * tl["N"] + mix.stat().st_size
    free = shutil.disk_usage(proj.out.parent if proj.out.exists() else proj.root).free
    print(f"  estimated final size {_gb(est)}, free disk {_gb(free)}")
    if est * 1.05 > free:
        raise SystemExit(f"Not enough disk space: need ~{_gb(est)}, have {_gb(free)}. "
                         "Free space or lower video.crf / vt_bitrate / resolution.")
    files = [r["intro"]] + r["segs"][1:] + [r["cycle"]] * (tl["N"] - 1) + ([r["outro"]] if r["outro"] else [])
    slug = "".join(ch if ch.isalnum() else "_" for ch in proj.cfg["project"]["title"]).strip("_")[:60]
    out = proj.p("out", f"{slug or 'final'}.mp4")
    tmp = out.with_suffix(".part.mp4")
    t0 = time.time()
    _concat(files, r["wdir"] / "final.txt", tmp,
            ["-i", str(mix), "-map", "0:v", "-map", "1:a", "-c", "copy", "-t", f"{D:.3f}"], long_running=True)
    tmp.replace(out)
    print(f"  final: {out} ({_gb(out.stat().st_size)}, assembled in {time.time() - t0:.0f}s)")
    proj.save_json("work/final.json", {"file": str(out), "duration": D})
    return out
