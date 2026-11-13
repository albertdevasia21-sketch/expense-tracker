"""Step 1 - import: normalise every clip to a common mezzanine (res, fps, colour, no audio)."""
from __future__ import annotations

from pathlib import Path

from . import ff
from .config import VIDEO_EXT, Project, file_sig, is_fresh, mark_fresh, slugify
from .encode import mezz_args


def find_clips(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT
                  and not p.name.startswith("."))


def run(proj: Project, source: Path | None = None) -> dict:
    v = proj.video
    folder = Path(source).expanduser() if source else proj.inbox
    clips = find_clips(folder)
    if not clips:
        raise SystemExit(f"No video clips found in {folder}")
    manifest = proj.load_json("work/manifest.json", default={"clips": {}})
    W, H, fps = int(v["width"]), int(v["height"]), float(v["fps"])
    if v.get("fit") == "pad":
        geom = (f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2")
    else:
        geom = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}"
    ext = ".mov" if v.get("mezz_codec") == "prores" else ".mp4"

    seen = set()
    for src in clips:
        cid = slugify(src.stem)
        while cid in seen:
            cid += "_b"
        seen.add(cid)
        info = ff.probe(src)
        vs = ff.video_stream(info)
        if not vs:
            print(f"  ! {src.name}: no video stream, skipped")
            continue
        src_fps = ff.parse_rate(vs.get("avg_frame_rate")) or ff.parse_rate(vs.get("r_frame_rate"))
        notes = []
        if abs(src_fps - fps) > 0.01:
            notes.append(f"frame rate converted {src_fps:.3f} -> {fps:g} fps (may add slight judder)")
        sw, sh = int(vs["width"]), int(vs["height"])
        if sw < W or sh < H:
            notes.append(f"upscaled from {sw}x{sh} to {W}x{H} (softer image)")
        if abs(sw / sh - W / H) > 0.01:
            notes.append(f"aspect {sw}x{sh} {'cropped' if v.get('fit') != 'pad' else 'letterboxed'} to {W}x{H}")
        if ff.audio_stream(info):
            notes.append("embedded clip audio dropped (audio is produced separately)")

        out = proj.p("work", "mezz", cid + ext)
        spec = {"src": file_sig(src), "W": W, "H": H, "fps": fps, "fit": v.get("fit"), "codec": mezz_args(v)}
        if not is_fresh(out, spec):
            print(f"  import {src.name} -> {out.name}")
            vf = f"{geom},fps={fps:g},setsar=1"
            ff.run(["-i", str(src), "-map", "0:v:0", "-an", "-sn", "-dn", "-vf", vf]
                   + mezz_args(v) + [str(out)], desc=f"import {src.name}")
            mark_fresh(out, spec)
        else:
            print(f"  cached {src.name}")
        frames = ff.count_frames(out)
        manifest["clips"][cid] = {
            "id": cid, "source": str(src), "mezz": str(out.relative_to(proj.root)),
            "frames": frames, "duration": frames / fps,
            "source_res": f"{sw}x{sh}", "source_fps": round(src_fps, 3),
            "source_codec": vs.get("codec_name"), "notes": notes,
        }
        if frames / fps < 3:
            notes.append("very short clip (<3 s): limited loop options")
    # drop clips whose source vanished from this import folder
    keep = {slugify(c.stem) for c in clips} | seen
    manifest["clips"] = {k: c for k, c in manifest["clips"].items() if k in keep}
    proj.save_json("work/manifest.json", manifest)
    print(f"  {len(manifest['clips'])} clip(s) in manifest")
    return manifest
