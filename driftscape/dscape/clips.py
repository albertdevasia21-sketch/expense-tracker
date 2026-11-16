"""Clip intake: prompt queue, verified + de-duplicated downloads, hand-off to the pipeline.

Everything here is independent of *how* a clip gets generated. The browser
assistant (browser.py) and the fully manual `watch` mode both end in
register(), so verification, duplicate protection and logging are identical.

Folder layout (default ~/Driftscape/Veo-Clips, override with DS_CLIPS_DIR or --dir):
  queue.json        prompts and their state
  001_<name>.mp4    verified clips
  _rejected/        failed verification or duplicates (never deleted automatically)
  logs/clips.log    full history
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from . import ff
from .config import slugify

MIN_BYTES = 50_000
MIN_SECONDS = 2.0
PARTIAL_SUFFIXES = (".crdownload", ".part", ".download", ".tmp")


def clips_dir(arg: str | None = None) -> Path:
    d = Path(arg or os.environ.get("DS_CLIPS_DIR") or Path.home() / "Driftscape" / "Veo-Clips").expanduser()
    for sub in ("", "_rejected", "_incoming", "logs"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def get_logger(d: Path) -> logging.Logger:
    log = logging.getLogger("clips")
    if not log.handlers:
        log.setLevel(logging.INFO)
        fh = logging.FileHandler(d / "logs" / "clips.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S"))
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter("  %(message)s"))
        log.addHandler(fh)
        log.addHandler(sh)
    return log


# --- queue ---------------------------------------------------------------------
class Queue:
    def __init__(self, d: Path):
        self.dir = d
        self.path = d / "queue.json"
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {
            "items": [], "single_test_ok": False}

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2))
        tmp.replace(self.path)

    @property
    def items(self) -> list[dict]:
        return self.data["items"]

    def add(self, prompt: str, name: str = "") -> dict | None:
        prompt = " ".join(prompt.split())
        if not prompt:
            return None
        if any(i["prompt"] == prompt and i["status"] in ("pending", "done") for i in self.items):
            return None                      # same prompt already queued or finished
        n = max([i["id"] for i in self.items] + [0]) + 1
        item = {"id": n, "name": slugify(name)[:40] if name else slugify(prompt)[:40], "prompt": prompt,
                "status": "pending", "added": _now(), "attempts": 0}
        self.items.append(item)
        self.save()
        return item

    def pending(self) -> list[dict]:
        return [i for i in self.items if i["status"] == "pending"]

    def known_hashes(self) -> dict[str, str]:
        return {i["sha256"]: i["file"] for i in self.items if i.get("sha256")}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_prompt_file(path: Path) -> list[tuple[str, str]]:
    """Prompts separated by blank lines. Optional first line 'name: xyz'. Lines starting # ignored."""
    out, block = [], []
    for line in Path(path).read_text().splitlines() + [""]:
        if line.strip().startswith("#"):
            continue
        if line.strip():
            block.append(line.strip())
            continue
        if block:
            name = ""
            if block[0].lower().startswith("name:"):
                name, block = block[0][5:].strip(), block[1:]
            if block:
                out.append((" ".join(block), name))
        block = []
    return out


# --- verification / duplicates ---------------------------------------------------
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_stable(path: Path, settle: float = 1.5) -> bool:
    """True once the browser has finished writing the file."""
    if any(path.with_name(path.name + s).exists() for s in PARTIAL_SUFFIXES):
        return False
    try:
        a = path.stat().st_size
        time.sleep(settle)
        return a > 0 and a == path.stat().st_size
    except FileNotFoundError:
        return False


def verify(path: Path) -> tuple[bool, str, dict]:
    """Is this a complete, playable video? Returns (ok, reason, info)."""
    if not path.exists():
        return False, "file missing", {}
    size = path.stat().st_size
    if size < MIN_BYTES:
        return False, f"too small ({size} bytes)", {}
    try:
        info = ff.probe(path)
    except ff.FFmpegError as e:
        return False, f"not a readable media file ({str(e).splitlines()[-1][:120]})", {}
    vs = ff.video_stream(info)
    if not vs:
        return False, "no video stream", {}
    dur = float(info.get("format", {}).get("duration") or 0)
    if dur < MIN_SECONDS:
        return False, f"too short ({dur:.1f}s)", {}
    # full decode: catches truncated downloads that still have a valid header
    p = subprocess.run([ff.FFMPEG, "-v", "error", "-nostdin", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"],
                       capture_output=True, text=True)
    if p.returncode != 0 or p.stderr.strip():
        return False, f"decode errors ({p.stderr.strip().splitlines()[0][:120] if p.stderr.strip() else 'failed'})", {}
    meta = {"width": int(vs["width"]), "height": int(vs["height"]), "duration": round(dur, 2),
            "fps": round(ff.parse_rate(vs.get("avg_frame_rate")), 3), "bytes": size}
    return True, "ok", meta


def _reject(d: Path, src: Path, why: str, log) -> None:
    dest = d / "_rejected" / f"{datetime.now():%Y%m%d-%H%M%S}_{src.name}"
    shutil.move(str(src), dest)
    log.warning(f"rejected {src.name}: {why} -> {dest.relative_to(d)}")


def register(q: Queue, item: dict, src: Path, log) -> bool:
    """Verify, de-duplicate and file a downloaded clip against its queue item."""
    d = q.dir
    ok, why, meta = verify(src)
    if not ok:
        _reject(d, src, why, log)
        item.update(status="failed", error=f"download failed verification: {why}")
        q.save()
        return False
    digest = sha256(src)
    dup = q.known_hashes().get(digest)
    if dup:
        _reject(d, src, f"duplicate of {dup}", log)
        item.update(status="failed", error=f"duplicate of {dup} (the site returned an earlier video)")
        q.save()
        return False
    dest = d / f"{item['id']:03d}_{item['name']}.mp4"
    k = 2
    while dest.exists():
        dest = d / f"{item['id']:03d}_{item['name']}_{k}.mp4"
        k += 1
    shutil.move(str(src), dest)
    item.update(status="done", file=dest.name, sha256=digest, done=_now(), error=None, **meta)
    q.save()
    log.info(f"saved {dest.name}  {meta['width']}x{meta['height']} {meta['duration']}s "
             f"{meta['bytes'] / 1e6:.1f} MB  sha256 {digest[:12]}")
    return True


# --- download detection ----------------------------------------------------------
def snapshot(dirs: list[Path]) -> set[Path]:
    return {p for d in dirs if d.exists() for p in d.iterdir()
            if p.is_file() and p.suffix.lower() in (".mp4", ".mov", ".webm")}


def wait_for_new_video(dirs: list[Path], before: set[Path], timeout: float, poll: float = 1.0,
                       tick=None) -> Path | None:
    """Wait for a finished video file that was not in `before` to appear in any of `dirs`."""
    end = time.time() + timeout
    while time.time() < end:
        for p in sorted(snapshot(dirs) - before, key=lambda x: x.stat().st_mtime):
            if is_stable(p):
                return p
        if tick and tick() is False:
            return None
        time.sleep(poll)
    return None


def download_dirs(d: Path) -> list[Path]:
    dirs = [d / "_incoming", Path.home() / "Downloads"]
    extra = os.environ.get("DS_DOWNLOAD_DIR")
    if extra:
        dirs.insert(0, Path(extra).expanduser())
    return dirs


# --- commands --------------------------------------------------------------------
def cmd_add(d: Path, prompts: list[str], file: str | None, name: str) -> None:
    q, log = Queue(d), get_logger(d)
    pairs = [(p, name) for p in prompts] + (parse_prompt_file(Path(file)) if file else [])
    if not pairs:
        raise SystemExit("Nothing to add. Give a prompt in quotes or --file prompts.txt")
    for prompt, nm in pairs:
        item = q.add(prompt, nm)
        if item:
            log.info(f"queued #{item['id']} {item['name']}")
        else:
            log.info(f"skipped (already queued or done): {prompt[:60]}...")


def cmd_list(d: Path) -> None:
    q = Queue(d)
    if not q.items:
        print(f"  queue is empty ({q.path})")
        return
    for i in q.items:
        extra = i.get("file") or i.get("error") or ""
        print(f"  #{i['id']:<3} {i['status']:<8} {i['name']:<32} {extra}")
    c = {s: sum(1 for i in q.items if i["status"] == s) for s in ("pending", "done", "failed", "blocked")}
    print(f"  {c['pending']} pending, {c['done']} done, {c['failed']} failed, {c['blocked']} blocked "
          f"| single-generation test passed: {'yes' if q.data.get('single_test_ok') else 'no'}")
    print(f"  folder: {d}")


def cmd_retry(d: Path) -> None:
    q, log = Queue(d), get_logger(d)
    n = 0
    for i in q.items:
        if i["status"] in ("failed", "blocked"):
            i.update(status="pending", error=None)
            n += 1
    q.save()
    log.info(f"{n} item(s) set back to pending")


def copy_to_clipboard(text: str) -> bool:
    for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=text, text=True, check=True, timeout=5)
                return True
            except Exception:
                pass
    return False


def cmd_watch(d: Path, timeout_min: float, limit: int) -> None:
    """Fully manual, always-available mode: you paste and click on the website; this files the result."""
    q, log = Queue(d), get_logger(d)
    todo = q.pending()[: limit or None]
    if not todo:
        print("  nothing pending. Add prompts with: ./ds clips add \"...\"")
        return
    dirs = download_dirs(d)
    print(f"  Watching for finished downloads in: {', '.join(str(x) for x in dirs)}")
    print("  For each prompt: paste it into Gemini or Flow, generate, then click Download. Ctrl-C to stop.\n")
    for n, item in enumerate(todo, 1):
        copied = copy_to_clipboard(item["prompt"])
        print(f"  [{n}/{len(todo)}] #{item['id']} {item['name']}" + ("  (prompt copied to clipboard)" if copied else ""))
        print(f"      {item['prompt']}\n")
        before = snapshot(dirs)
        item["attempts"] += 1
        q.save()
        got = wait_for_new_video(dirs, before, timeout_min * 60)
        if not got:
            log.warning(f"#{item['id']}: no download seen within {timeout_min:g} min - left pending, stopping")
            return
        register(q, item, got, log)
    log.info("queue finished")


def cmd_send(d: Path, project: str, only: list[str]) -> int:
    """Copy verified clips into a project's inbox (skipping any already there)."""
    from .config import Project
    q, log = Queue(d), get_logger(d)
    proj = Project(project)
    proj.inbox.mkdir(exist_ok=True)
    have = {sha256(p) for p in proj.inbox.iterdir() if p.is_file() and p.suffix.lower() == ".mp4"}
    sent = 0
    for i in q.items:
        if i["status"] != "done" or (only and i["name"] not in only and str(i["id"]) not in only):
            continue
        src = d / i["file"]
        if not src.exists():
            log.warning(f"#{i['id']}: {i['file']} is missing from {d}")
            continue
        if i["sha256"] in have:
            continue
        shutil.copy2(src, proj.inbox / f"{i['name']}.mp4")
        have.add(i["sha256"])
        i.setdefault("sent_to", []).append(str(proj.root))
        sent += 1
        log.info(f"sent {i['file']} -> {proj.inbox / (i['name'] + '.mp4')}")
    q.save()
    log.info(f"{sent} clip(s) added to {proj.inbox}" if sent else "no new clips to send")
    return sent
