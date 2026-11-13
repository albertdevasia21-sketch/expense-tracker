"""Generate a synthetic sample project that mimics Veo ambience clips + licensed audio.

Clips are procedural (no copyrighted material) and deliberately include the
problems the pipeline must catch:
  fog_valley     9 s  24 fps  drifting fog, start != end        -> loopable with crossfade
  lake_shimmer   8 s  24 fps  water ripples + embedded audio     -> loopable, audio stripped
  camera_push   10 s  30 fps  1280x720 slow zoom (camera move)   -> fps/upscale notes, oneshot
  aurora_glitch  8 s  24 fps  aurora with a flash + a jump cut   -> artifacts flagged
  rain_window   10 s  24 fps  falling rain streaks               -> stationary texture, loops well
Audio: rain_bed.wav (48 kHz, 40 s, not seamless) and drone.mp3 (44.1 kHz, 25 s).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import numpy as np

GW, GH = 480, 270  # generation resolution; ffmpeg upscales + adds grain


def value_noise(rng, w, h, cells):
    g = rng.random((cells + 3, int(cells * h / w) + 3))
    xs = np.linspace(0, cells, w, endpoint=False)
    ys = np.linspace(0, cells * h / w, h, endpoint=False)
    x0, y0 = xs.astype(int), ys.astype(int)
    fx, fy = xs - x0, ys - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = g[x0][:, y0]; b = g[x0 + 1][:, y0]; c = g[x0][:, y0 + 1]; d = g[x0 + 1][:, y0 + 1]
    top = a + (b - a) * fx[:, None]; bot = c + (d - c) * fx[:, None]
    return (top + (bot - top) * fy[None, :]).T


def fbm(rng, w, h, base=4, octaves=4):
    out, amp, tot = np.zeros((h, w)), 1.0, 0.0
    for o in range(octaves):
        out += amp * value_noise(rng, w, h, base * 2 ** o); tot += amp; amp *= 0.5
    return out / tot


def encode(frames_fn, n, fps, out: Path, size: str, src_size=(GW, GH), audio: bool = False, grain=3):
    W, H = map(int, size.split("x"))
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{src_size[0]}x{src_size[1]}", "-r", str(fps), "-i", "pipe:0"]
    if audio:
        cmd += ["-f", "lavfi", "-t", str(n / fps), "-i", "anoisesrc=color=pink:amplitude=0.05:sample_rate=48000"]
    cmd += ["-vf", f"scale={W}:{H}:flags=lanczos,noise=alls={grain}:allf=t,format=yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-crf", "16"]
    if audio:
        cmd += ["-c:a", "aac", "-shortest"]
    cmd += [str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(n):
        f = np.clip(frames_fn(k), 0, 255).astype(np.uint8)
        p.stdin.write(f.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise SystemExit(f"sample encode failed: {out}")


def grade(v, lo, hi):
    lo, hi = np.array(lo, float), np.array(hi, float)
    return lo + (hi - lo) * v[..., None]


def fog_frames(seed, n, fps, palette, glitch=False, drift=18.0, morph=3.2):
    rng = np.random.default_rng(seed)
    keys = [fbm(rng, GW * 2, GH * 2) for _ in range(5)]
    yy = np.linspace(0, 1, GH)[:, None]
    def frame(k):
        t = k / fps
        # evolving field: blend between random keyframes + slow drift
        ph = t / morph
        i = int(ph) % 4; f = ph - int(ph); f = f * f * (3 - 2 * f)
        dx = int(drift * t); dy = int(4 * np.sin(t * 0.7) + 4)
        A = keys[i][dy:dy + GH, dx:dx + GW]; B = keys[i + 1][dy:dy + GH, dx:dx + GW]
        fog = A + (B - A) * f
        v = np.clip(0.25 + 0.75 * fog * (0.55 + 0.6 * yy), 0, 1)
        if glitch and int(3.5 * fps) <= k < int(3.5 * fps) + 2:
            v = np.clip(v * 1.9 + 0.25, 0, 1)               # 2-frame flash
        if glitch and k >= int(5.5 * fps):
            v = np.roll(v, 60, axis=1)                       # jump cut / morph glitch
        return grade(v, *palette)
    return frame


def rain_frames(seed, n, fps):
    """Rain streaks over a soft dark backdrop: stationary texture -> should loop well."""
    rng = np.random.default_rng(seed)
    back = grade(fbm(rng, GW, GH, base=2, octaves=3) * 0.5 + 0.2, (8, 12, 20), (90, 110, 140))
    drops = [(rng.uniform(0, GW), rng.uniform(0, GH), rng.uniform(180, 320), rng.uniform(6, 16)) for _ in range(160)]
    def frame(k):
        t = k / fps
        f = back.copy()
        for x, y0, v, L in drops:
            y = int((y0 + v * t) % GH); xi = int(x + 0.15 * (y0 + v * t)) % GW
            f[y:y + int(L), xi] = np.minimum(255, f[y:y + int(L), xi] + 70)
        return f
    return frame


def lake_frames(seed, n, fps):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:GH, 0:GW] / GH
    waves = [(rng.uniform(0, 2 * np.pi), rng.uniform(6, 22), rng.uniform(0.6, 2.2), rng.uniform(0, 6.28))
             for _ in range(9)]
    sky = np.clip(1 - yy, 0, 1)
    def frame(k):
        t = k / fps
        h = sum(np.sin(np.cos(a) * xx * f + np.sin(a) * yy * f * 3 - s * t + p) for a, f, s, p in waves) / 9
        v = np.clip(0.35 + 0.3 * h + 0.35 * sky * (yy < 0.4), 0, 1)
        return grade(v, (10, 25, 45), (150, 200, 230))
    return frame


def push_frames(seed, n, fps, w=640, h=360):
    rng = np.random.default_rng(seed)
    big = fbm(rng, w * 2, h * 2, base=3, octaves=5)
    yy = np.linspace(0, 1, h * 2)[:, None]
    ridge = (yy > 0.45 + 0.15 * big).astype(float)
    land = np.clip(0.6 * (1 - yy) + 0.4 * big * ridge, 0, 1)
    img = grade(land, (25, 20, 40), (240, 170, 120))
    def frame(k):
        z = 1 + 0.35 * k / n                                  # steady zoom
        cw, ch = int(w * 2 / z), int(h * 2 / z)
        x0, y0 = (w * 2 - cw) // 2, (h * 2 - ch) // 2
        crop = img[y0:y0 + ch, x0:x0 + cw]
        iy = (np.arange(h) * ch / h).astype(int); ix = (np.arange(w) * cw / w).astype(int)
        return crop[iy][:, ix]
    return frame


def make_audio(dirp: Path):
    # rain: pink+brown noise, high-passed, slow swell; deliberately not loop-seamless
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.4:sample_rate=48000:seed=3",
                    "-f", "lavfi", "-i", "anoisesrc=color=brown:amplitude=0.5:sample_rate=48000:seed=5",
                    "-filter_complex", "[0][1]amix=inputs=2:normalize=0,highpass=f=120,lowpass=f=9000,"
                    "volume='0.6+0.25*sin(2*PI*t/17)':eval=frame,aformat=channel_layouts=stereo",
                    "-t", "40", str(dirp / "rain_bed.wav")], check=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "sine=f=110:sample_rate=44100", "-f", "lavfi", "-i", "sine=f=164.8:sample_rate=44100",
                    "-f", "lavfi", "-i", "sine=f=220.5:sample_rate=44100",
                    "-filter_complex", "[0][1][2]amix=inputs=3,tremolo=f=0.2:d=0.4,aformat=channel_layouts=stereo",
                    "-t", "25", "-c:a", "libmp3lame", "-q:a", "3", str(dirp / "drone.mp3")], check=True)


def main(root: Path, size: str = "1920x1080"):
    root = Path(root).expanduser()
    for d in ("inbox", "audio", "work", "out"):
        (root / d).mkdir(parents=True, exist_ok=True)
    inbox = root / "inbox"
    print(f"generating sample clips at {size} in {inbox} ...")
    encode(fog_frames(1, 216, 24, ((18, 28, 30), (200, 215, 210))), 216, 24, inbox / "fog_valley.mp4", size)
    encode(rain_frames(5, 240, 24), 240, 24, inbox / "rain_window.mp4", size)
    encode(lake_frames(2, 192, 24), 192, 24, inbox / "lake_shimmer.mp4", size, audio=True)
    w, h = map(int, size.split("x"))
    encode(push_frames(3, 300, 30), 300, 30, inbox / "camera_push.mp4", f"{min(w, 1280)}x{min(h, 720)}",
           src_size=(640, 360))
    encode(fog_frames(4, 192, 24, ((5, 20, 25), (90, 230, 160)), glitch=True), 192, 24,
           inbox / "aurora_glitch.mp4", size)
    print("generating sample audio ...")
    make_audio(root / "audio")
    tpl = (Path(__file__).resolve().parent.parent / "templates" / "project.toml").read_text()
    tpl = tpl.replace('title = "Misty Pine Forest Rain"', 'title = "Sample Fog Valley"')
    tpl = re.sub(r'license = "REPLACE[^"]*"', 'license = "Synthetic sample generated by make_samples.py (CC0)"', tpl)
    tpl = tpl.replace("# [[audio.layers]]\n# file = \"distant_thunder.wav\"\n# gain_db = -9.0\n# loop = true\n"
                      "# license = \"...\"",
                      "[[audio.layers]]\nfile = \"drone.mp3\"\ngain_db = -14.0\nloop = true\nloop_crossfade = 3.0\n"
                      "crossfade_curve = \"tri\"\nlicense = \"Synthetic sample (CC0)\"\n"
                      "credit = \"Drone pad - Driftscape sample\"\nattribution_required = true")
    tpl = tpl.replace("cycle_minutes = 10 ", "cycle_minutes = 3  ")
    w_, h_ = size.split("x")
    tpl = tpl.replace("width = 1920 ", f"width = {w_} ", 1).replace("height = 1080", f"height = {h_}", 1)
    (root / "project.toml").write_text(tpl)
    print(f"sample project ready: {root}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "1920x1080")
