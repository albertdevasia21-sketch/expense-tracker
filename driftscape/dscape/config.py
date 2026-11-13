"""Project configuration: project.toml merged over built-in defaults."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib  # type: ignore

DEFAULTS: dict = {
    "project": {"title": "Untitled Ambience", "duration": "3h", "channel": "Driftscape"},
    "video": {
        "width": 1920, "height": 1080, "fps": 24,
        "fit": "crop",                 # crop (fill frame) | pad (letterbox)
        "mezz_codec": "x264hq",        # x264hq (small, near-lossless) | prores (big, edit-friendly)
        "codec": "libx264",            # libx264 | h264_videotoolbox | hevc_videotoolbox
        "crf": 18, "preset": "medium", "maxrate": "16M", "bufsize": "32M",
        "vt_bitrate": "16M",           # used by *_videotoolbox encoders
        "loop_crossfade": 1.5,         # s, self-loop seam blend
        "transition": 3.0,             # s, dissolve between different clips
        "hold_min": 20.0, "hold_max": 45.0,   # s, how long a looping clip stays on screen
        "cycle_minutes": 10.0,         # unique visual cycle, then stream-copied
        "fade_in": 4.0, "fade_out": 8.0,
        "seed": 7,
        "mode": "auto",                # auto | loop | oneshot | pingpong (per clip override in [clips.<id>])
    },
    "preview": {"width": 640, "height": 360, "crf": 30, "preset": "veryfast", "extra_seconds": 20},
    "audio": {
        "target_lufs": -18.0, "true_peak": -2.0, "lra": 11.0,
        "sample_rate": 48000, "bitrate": "384k",
        "layers": [],
    },
    "thumbnail": {"text": "", "subtext": "", "font": "", "count": 3},
    "youtube": {
        "title": "{title} | {length} of Relaxing Ambience",
        "description": "",
        "tags": [],
        "category_id": "10",
        "privacy": "private",
        "made_for_kids": False,
        "contains_synthetic_media": True,
        "default_language": "en",
    },
    "system": {"threads": 6, "nice": 10},
    "clips": {},
}

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def parse_duration(v) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower()
    if re.fullmatch(r"[\d.]+", s):
        return float(s)
    if re.fullmatch(r"\d+:\d{2}:\d{2}", s):
        h, m, sec = map(int, s.split(":"))
        return h * 3600 + m * 60 + sec
    total, matched = 0.0, False
    for num, unit in re.findall(r"([\d.]+)\s*([hms])", s):
        matched = True
        total += float(num) * {"h": 3600, "m": 60, "s": 1}[unit]
    if not matched:
        raise ValueError(f"Cannot parse duration: {v!r} (use e.g. '3h', '2h30m', '45m', 10800)")
    return total


class Project:
    def __init__(self, root: Path | str):
        self.root = Path(root).expanduser().resolve()
        cfg_path = self.root / "project.toml"
        if not cfg_path.exists():
            raise SystemExit(f"No project.toml in {self.root}. Create one with: ./ds new {self.root}")
        with open(cfg_path, "rb") as f:
            user = tomllib.load(f)
        self.cfg = deep_merge(DEFAULTS, user)
        self.duration = parse_duration(self.cfg["project"]["duration"])

    # --- paths -------------------------------------------------------------
    def p(self, *parts) -> Path:
        path = self.root.joinpath(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def inbox(self) -> Path:
        return self.root / "inbox"

    @property
    def audio_dir(self) -> Path:
        return self.root / "audio"

    @property
    def work(self) -> Path:
        return self.root / "work"

    @property
    def out(self) -> Path:
        return self.root / "out"

    @property
    def video(self) -> dict:
        return self.cfg["video"]

    def clip_cfg(self, cid: str) -> dict:
        return self.cfg.get("clips", {}).get(cid, {})

    def load_json(self, rel: str, default=None):
        path = self.root / rel
        if not path.exists():
            if default is not None:
                return default
            raise SystemExit(f"Missing {rel}. Run the earlier pipeline step first.")
        return json.loads(path.read_text())

    def save_json(self, rel: str, data) -> Path:
        path = self.p(rel)
        path.write_text(json.dumps(data, indent=2, default=_jsonable))
        return path


def _jsonable(o):
    """numpy scalars/arrays -> plain Python for json.dumps."""
    if hasattr(o, "item") and getattr(o, "ndim", 0) == 0:
        return o.item()
    if hasattr(o, "tolist"):
        return o.tolist()
    raise TypeError(f"not JSON serializable: {type(o).__name__}")


def spec_hash(spec) -> str:
    return hashlib.sha1(json.dumps(spec, sort_keys=True, default=str).encode()).hexdigest()[:12]


def file_sig(path: Path) -> list:
    st = Path(path).stat()
    return [str(path), st.st_size, int(st.st_mtime)]


def is_fresh(out: Path, spec) -> bool:
    """Cache check: output exists and was made from the identical spec."""
    stamp = out.with_name(out.name + ".spec")
    return out.exists() and stamp.exists() and stamp.read_text() == spec_hash(spec)


def mark_fresh(out: Path, spec) -> None:
    out.with_name(out.name + ".spec").write_text(spec_hash(spec))


def slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s or "clip"
