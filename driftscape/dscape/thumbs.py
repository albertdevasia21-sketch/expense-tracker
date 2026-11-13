"""Step 7 - thumbnails: score frames (sharpness, colour, exposure), compose 1280x720 JPEGs."""
from __future__ import annotations

import subprocess
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from . import ff
from .config import Project

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Futura.ttc",
    "/System/Library/Fonts/Avenir Next.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
MAX_BYTES = 2 * 1024 * 1024


def score_frames(path, fps_sample=2.0):
    frames = ff.read_frames(path, 320, 180, "rgb24", vf_extra=f"fps={fps_sample}")
    out = []
    for k, f in enumerate(frames):
        x = f.astype(np.float32)
        g = x.mean(axis=2)
        lap = (np.abs(4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:])).var()
        rg, yb = x[..., 0] - x[..., 1], 0.5 * (x[..., 0] + x[..., 1]) - x[..., 2]
        colorful = np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
        mean = g.mean() / 255
        clip = np.mean((g < 4) | (g > 251))
        expo = 1 - min(1, abs(mean - 0.45) / 0.45)
        s = np.log1p(lap) * 0.5 + colorful / 40 + expo * 1.5 - clip * 4
        out.append((float(s), k / fps_sample))
    return out


def _font(cfg_font: str, size: int):
    for f in ([cfg_font] if cfg_font else []) + FONT_CANDIDATES:
        if f and Path(f).exists():
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                continue
    return ImageFont.load_default(size=size)


def compose(frame: Image.Image, text: str, subtext: str, font_path: str) -> Image.Image:
    W, H = 1280, 720
    s = max(W / frame.width, H / frame.height)
    img = frame.resize((round(frame.width * s), round(frame.height * s)), Image.LANCZOS)
    l, t = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((l, t, l + W, t + H)).convert("RGB")
    img = ImageEnhance.Contrast(img).enhance(1.06)
    img = ImageEnhance.Color(img).enhance(1.10)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    # soft vignette
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    v = np.clip(1 - 0.28 * np.clip(r - 0.55, 0, None) ** 1.5, 0, 1)
    img = Image.fromarray((np.asarray(img, np.float32) * v[..., None]).astype(np.uint8))
    if text:
        d = ImageDraw.Draw(img, "RGBA")
        f1 = _font(font_path, 92)
        f2 = _font(font_path, 40)
        tw = d.textlength(text, font=f1)
        x, y = (W - tw) / 2, H * 0.68
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.text((x + 3, y + 4), text, font=f1, fill=(0, 0, 0, 170))
        if subtext:
            sw = sd.textlength(subtext, font=f2)
            sd.text(((W - sw) / 2 + 2, y + 112), subtext, font=f2, fill=(0, 0, 0, 170))
        img = Image.alpha_composite(img.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(6)))
        d = ImageDraw.Draw(img)
        d.text((x, y), text, font=f1, fill=(255, 255, 255, 255))
        if subtext:
            sw = d.textlength(subtext, font=f2)
            d.text(((W - sw) / 2, y + 110), subtext, font=f2, fill=(235, 240, 245, 255))
        img = img.convert("RGB")
    return img


def save_jpeg(img: Image.Image, path: Path) -> int:
    for q in (92, 88, 84, 80, 75, 70):
        buf = BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= MAX_BYTES:
            path.write_bytes(buf.getvalue())
            return buf.tell()
    raise SystemExit(f"Could not get thumbnail under 2 MB: {path}")


def run(proj: Project) -> list[Path]:
    manifest = proj.load_json("work/manifest.json")
    an = proj.load_json("work/analysis.json")
    tcfg = proj.cfg["thumbnail"]
    cands = []
    for cid, c in manifest["clips"].items():
        if an["clips"].get(cid, {}).get("excluded"):
            continue
        spikes = [s["t"] for s in an["clips"][cid].get("spikes", [])]
        for s, t in score_frames(proj.root / c["mezz"]):
            if any(abs(t - x) < 0.5 for x in spikes):
                continue
            cands.append((s, cid, t))
    cands.sort(reverse=True)
    chosen, used = [], set()
    for s, cid, t in cands:          # best frame per clip first, for variety
        if cid not in used:
            chosen.append((s, cid, t))
            used.add(cid)
    chosen = (chosen + [c for c in cands if c not in chosen])[: int(tcfg["count"])]
    outdir = proj.out / "thumbnails"
    outdir.mkdir(parents=True, exist_ok=True)
    paths = []
    text = tcfg.get("text") or ""
    sub = tcfg.get("subtext") or ""
    for k, (s, cid, t) in enumerate(chosen, 1):
        src = proj.root / manifest["clips"][cid]["mezz"]
        png = subprocess.run([ff.FFMPEG, "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(src),
                              "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
                             capture_output=True, check=True).stdout
        frame = Image.open(BytesIO(png))
        img = compose(frame, text, sub, tcfg.get("font", ""))
        p = outdir / f"thumb_{k}_{cid}_{t:.1f}s.jpg"
        size = save_jpeg(img, p)
        compose(frame, "", "", "").save(outdir / f"clean_{k}_{cid}_{t:.1f}s.png")
        print(f"  thumbnail {p.name} (score {s:.2f}, {size / 1024:.0f} KB)")
        paths.append(p)
    if paths:  # contact sheet for quick choice
        thumbs = [Image.open(p).resize((426, 240)) for p in paths]
        sheet = Image.new("RGB", (426 * len(thumbs), 240), "black")
        for k, im in enumerate(thumbs):
            sheet.paste(im, (426 * k, 0))
        sheet.save(outdir / "contact_sheet.jpg", quality=85)
    return paths
