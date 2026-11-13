"""Thin, dependency-free wrappers around ffmpeg/ffprobe.

Everything heavy is delegated to ffmpeg so Python never holds full-resolution
video in memory. Analysis reads tiny downscaled frames through a pipe.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

FFMPEG = os.environ.get("DS_FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("DS_FFPROBE", "ffprobe")

IS_MAC = platform.system() == "Darwin"

# Set from config at startup (see cli.py)
SETTINGS = {"threads": 0, "nice": 10, "verbose": False}


class FFmpegError(RuntimeError):
    pass


def _wrap(cmd: list[str], long_running: bool) -> list[str]:
    prefix: list[str] = []
    # Keep the Mac awake during long renders, but let the display sleep.
    if long_running and IS_MAC and shutil.which("caffeinate"):
        prefix += ["caffeinate", "-i"]
    nice = SETTINGS.get("nice", 0)
    if nice and shutil.which("nice"):
        prefix += ["nice", "-n", str(int(nice))]
    return prefix + cmd


def thread_args() -> list[str]:
    t = int(SETTINGS.get("threads") or 0)
    return ["-threads", str(t)] if t > 0 else []


def run(args: list[str], desc: str = "", long_running: bool = False,
        capture: bool = False) -> str:
    """Run ffmpeg. Returns stderr text when capture=True."""
    loglevel = "info" if capture else ("warning" if SETTINGS.get("verbose") else "error")
    cmd = [FFMPEG, "-hide_banner", "-nostdin", "-y", "-loglevel", loglevel]
    if long_running and not capture:
        cmd += ["-stats"]
    cmd += args
    cmd = _wrap(cmd, long_running)
    if SETTINGS.get("verbose"):
        print("  $", " ".join(cmd), file=sys.stderr)
    t0 = time.time()
    if capture:
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        err = p.stderr
    else:
        # Long renders show ffmpeg's own progress line on the terminal.
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL,
                           stderr=None if long_running else subprocess.PIPE, text=True)
        err = p.stderr or ""
    if p.returncode != 0:
        tail = "\n".join((err or "").strip().splitlines()[-25:])
        raise FFmpegError(f"ffmpeg failed ({desc or 'command'}):\n{tail}\nCMD: {' '.join(cmd)}")
    if desc and SETTINGS.get("verbose"):
        print(f"  ({desc}: {time.time() - t0:.1f}s)", file=sys.stderr)
    return err


def probe(path: Path | str) -> dict:
    cmd = [FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise FFmpegError(f"ffprobe failed for {path}: {p.stderr.strip()}")
    return json.loads(p.stdout)


def video_stream(info: dict) -> dict | None:
    return next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)


def audio_stream(info: dict) -> dict | None:
    return next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)


def parse_rate(r: str | None) -> float:
    if not r or r in ("0/0", "N/A"):
        return 0.0
    if "/" in r:
        a, b = r.split("/")
        return float(a) / float(b) if float(b) else 0.0
    return float(r)


def duration_of(path: Path | str) -> float:
    info = probe(path)
    d = info.get("format", {}).get("duration")
    return float(d) if d not in (None, "N/A") else 0.0


def count_frames(path: Path | str) -> int:
    """Exact decoded frame count (reads packets, cheap)."""
    cmd = [FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_packets",
           "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(path)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return int(p.stdout.strip().split(",")[0])
    except ValueError:
        return 0


def has_encoder(name: str) -> bool:
    p = subprocess.run([FFMPEG, "-hide_banner", "-encoders"], capture_output=True, text=True)
    return any(line.split()[1:2] == [name] for line in p.stdout.splitlines() if line.strip())


def has_filter(name: str) -> bool:
    p = subprocess.run([FFMPEG, "-hide_banner", "-filters"], capture_output=True, text=True)
    return any(line.split()[1:2] == [name] for line in p.stdout.splitlines() if line.strip())


def iter_frames(path: Path | str, w: int, h: int, pix: str = "gray",
                vf_extra: str = "", chunk: int = 64, input_args: list[str] | None = None):
    """Yield (n,h,w[,c]) uint8 chunks of tiny frames streamed from ffmpeg.

    Memory stays at chunk*w*h bytes regardless of video length.
    """
    ch = {"gray": 1, "rgb24": 3}[pix]
    vf = f"scale={w}:{h}:flags=area,format={pix}"
    if vf_extra:
        vf = vf_extra + "," + vf
    cmd = [FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error"] + (input_args or []) + \
          ["-i", str(path), "-map", "0:v:0", "-vf", vf, "-f", "rawvideo", "-pix_fmt", pix, "pipe:1"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    fsize = w * h * ch
    try:
        while True:
            buf = proc.stdout.read(fsize * chunk)
            if not buf:
                break
            n = len(buf) // fsize
            arr = np.frombuffer(buf[: n * fsize], dtype=np.uint8)
            shape = (n, h, w) if ch == 1 else (n, h, w, ch)
            yield arr.reshape(shape)
    finally:
        proc.stdout.close()
        err = proc.stderr.read().decode(errors="replace")
        proc.stderr.close()
        rc = proc.wait()
        if rc != 0:
            raise FFmpegError(f"frame decode failed for {path}: {err[-800:]}")


def read_frames(path, w, h, pix="gray", **kw) -> np.ndarray:
    chunks = list(iter_frames(path, w, h, pix, **kw))
    if not chunks:
        return np.zeros((0, h, w) if pix == "gray" else (0, h, w, 3), np.uint8)
    return np.concatenate(chunks)


def read_audio(path, start: float, dur: float, sr: int = 48000) -> np.ndarray:
    """Read a short stereo float32 window (shape (n,2))."""
    cmd = [FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error", "-ss", f"{start:.6f}", "-t", f"{dur:.6f}",
           "-i", str(path), "-ac", "2", "-ar", str(sr), "-f", "f32le", "pipe:1"]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        raise FFmpegError(p.stderr.decode(errors="replace")[-500:])
    return np.frombuffer(p.stdout, dtype=np.float32).reshape(-1, 2)
