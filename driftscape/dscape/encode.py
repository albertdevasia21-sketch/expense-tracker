"""Encoder argument builders for intermediates and delivery."""
from __future__ import annotations

from . import ff

COLOR = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]


def mezz_args(v: dict) -> list[str]:
    """Intermediate (mezzanine / loop) codec: near-lossless, short GOP for cheap seeking."""
    if v.get("mezz_codec") == "prores":
        return ["-c:v", "prores_ks", "-profile:v", "2", "-vendor", "apl0", "-pix_fmt", "yuv422p10le"] + COLOR
    return ["-c:v", "libx264", "-preset", "fast", "-crf", "12", "-g", "12", "-bf", "0",
            "-pix_fmt", "yuv420p"] + COLOR + ff.thread_args()


def delivery_args(v: dict, preview: dict | None = None) -> list[str]:
    """Segment encoder. All segments of one profile MUST share these exact args so
    they can be joined with stream copy."""
    fps = int(round(v["fps"]))
    gop = ["-g", str(fps * 2), "-keyint_min", str(fps), "-sc_threshold", "0"]
    if preview is not None:
        return ["-c:v", "libx264", "-preset", preview["preset"], "-crf", str(preview["crf"]),
                "-profile:v", "high", "-pix_fmt", "yuv420p"] + gop + COLOR + ff.thread_args()
    codec = v.get("codec", "libx264")
    if codec in ("h264_videotoolbox", "hevc_videotoolbox"):
        args = ["-c:v", codec, "-b:v", v["vt_bitrate"], "-maxrate", v["maxrate"], "-bufsize", v["bufsize"],
                "-pix_fmt", "yuv420p", "-g", str(fps * 2), "-realtime", "0"]
        if codec == "hevc_videotoolbox":
            args += ["-tag:v", "hvc1", "-profile:v", "main"]
        else:
            args += ["-profile:v", "high"]
        return args + COLOR
    return ["-c:v", "libx264", "-preset", v["preset"], "-crf", str(v["crf"]), "-maxrate", v["maxrate"],
            "-bufsize", v["bufsize"], "-profile:v", "high", "-pix_fmt", "yuv420p"] + gop + COLOR + ff.thread_args()
