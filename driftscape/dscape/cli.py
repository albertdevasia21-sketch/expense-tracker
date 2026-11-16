"""Command line entry point:  ./ds <command> <project> [options]"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import ff

HERE = Path(__file__).resolve().parent.parent
TEMPLATE = HERE / "templates" / "project.toml"


DURATION_OVERRIDE = None


def _proj(path):
    from .config import Project, parse_duration
    p = Project(path)
    if DURATION_OVERRIDE:
        p.duration = parse_duration(DURATION_OVERRIDE)
        p.cfg["project"]["duration"] = DURATION_OVERRIDE
        print(f"  (duration overridden: {DURATION_OVERRIDE})")
    ff.SETTINGS.update(threads=p.cfg["system"]["threads"], nice=p.cfg["system"]["nice"])
    return p


def step(title):
    print(f"\n== {title} ==")


def cmd_new(a):
    root = Path(a.project).expanduser()
    for d in ("inbox", "audio", "work", "out"):
        (root / d).mkdir(parents=True, exist_ok=True)
    cfg = root / "project.toml"
    if not cfg.exists():
        shutil.copy(TEMPLATE, cfg)
    print(f"Project ready: {root}\n  1. put Veo clips in {root / 'inbox'}\n  2. put licensed audio in "
          f"{root / 'audio'}\n  3. edit {cfg} (title, audio layers + licences)\n  4. ./ds all {root}")


def cmd_doctor(a):
    ok = True
    def line(name, good, detail=""):
        nonlocal ok
        ok &= bool(good) or name.startswith("(optional)")
        print(f"  [{'ok' if good else '--'}] {name} {detail}")
    line("python >= 3.11", sys.version_info >= (3, 11), sys.version.split()[0])
    for exe in ("ffmpeg", "ffprobe"):
        line(exe, shutil.which(exe), shutil.which(exe) or "missing - brew install ffmpeg")
    if shutil.which("ffmpeg"):
        v = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.split("\n")[0]
        print(f"       {v}")
        for enc in ("libx264", "aac", "prores_ks"):
            line(f"encoder {enc}", ff.has_encoder(enc))
        for flt in ("xfade", "loudnorm", "ebur128"):
            line(f"filter {flt}", ff.has_filter(flt))
        line("(optional) h264_videotoolbox (Apple hardware encoder)", ff.has_encoder("h264_videotoolbox"))
        line("(optional) aac_at (Apple AAC encoder, much faster audio)", ff.has_encoder("aac_at"))
        line("(optional) drawtext (labels in seam reel)", ff.has_filter("drawtext"))
    for mod in ("numpy", "PIL"):
        try:
            __import__(mod)
            line(f"python module {mod}", True)
        except ImportError:
            line(f"python module {mod}", False, "pip install -r requirements.txt")
    try:
        __import__("googleapiclient")
        line("(optional) google-api-python-client (upload)", True)
    except ImportError:
        line("(optional) google-api-python-client (upload)", False, "pip install -r requirements-upload.txt")
    try:
        __import__("playwright")
        line("(optional) playwright (browser assistant for Gemini/Flow)", True)
    except ImportError:
        line("(optional) playwright (browser assistant for Gemini/Flow)", False,
             "pip install -r requirements-browser.txt")
    line("(optional) blender", shutil.which("blender"), "(not required by this pipeline)")
    print("\nAll required dependencies present." if ok else "\nMissing required dependencies (see above).")
    return 0 if ok else 1


def cmd_import(a):
    from . import ingest
    step("import"); ingest.run(_proj(a.project), a.source)


def cmd_analyze(a):
    from . import analyze
    step("analyse"); analyze.run(_proj(a.project))


def cmd_loops(a):
    from . import loops
    step("loops"); loops.run(_proj(a.project))


def cmd_plan(a):
    from . import sequence
    step("plan"); sequence.plan(_proj(a.project))


def cmd_audio(a):
    from . import audio
    p = _proj(a.project)
    step("audio (full length)")
    audio.render_mix(p, p.duration, p.p("work", "audio", "mix_final.m4a"))


def cmd_preview(a):
    from . import qc, render
    p = _proj(a.project)
    step("preview"); render.preview(p)
    step("qc (preview)"); qc.run(p, final=False)


def cmd_render(a):
    from . import qc, render
    p = _proj(a.project)
    step("final render"); render.final(p)
    step("qc (final)"); qc.run(p, final=True)


def cmd_thumbs(a):
    from . import thumbs
    step("thumbnails"); thumbs.run(_proj(a.project))


def cmd_meta(a):
    from . import meta
    step("metadata"); meta.run(_proj(a.project))


def cmd_qc(a):
    from . import qc
    step("qc"); qc.run(_proj(a.project), final=a.final)


def cmd_all(a):
    t0 = time.time()
    a.source = None
    for f in (cmd_import, cmd_analyze, cmd_loops, cmd_preview, cmd_thumbs, cmd_meta):
        f(a)
    if a.final:
        cmd_render(a)
    print(f"\nDone in {time.time() - t0:.0f}s. Review out/preview.mp4, out/seams_review.mp4 and out/reports/."
          + ("" if a.final else f"\nWhen happy: ./ds render {a.project}"))


def cmd_upload(a):
    from . import upload
    step("upload"); upload.run(_proj(a.project), a.i_confirm, a.dry_run, a.thumbnail)


def cmd_clips(a):
    from . import clips
    d = clips.clips_dir(a.dir)
    act = a.action
    if act == "add":
        clips.cmd_add(d, a.prompts, a.file, a.name)
    elif act == "list":
        clips.cmd_list(d)
    elif act == "retry":
        clips.cmd_retry(d)
    elif act == "watch":
        step("clips: manual mode"); clips.cmd_watch(d, a.timeout, a.max)
    elif act == "send":
        if not a.prompts:
            raise SystemExit("Usage: ./ds clips send <project> [--only name ...] [--run]")
        step("clips -> project")
        clips.cmd_send(d, a.prompts[0], a.only or [])
        if a.run:
            a.project, a.final = a.prompts[0], False
            cmd_all(a)
    else:
        from . import browser
        if act == "chrome":
            browser.cmd_chrome(d, a.site)
        elif act == "check":
            step("clips: browser check"); return 0 if browser.cmd_check(d, a.site) else 1
        elif act == "one":
            step("clips: single supervised test"); browser.cmd_one(d, a.site)
        elif act == "run":
            step("clips: batch"); browser.cmd_run(d, a.site, a.max or 5)


def cmd_samples(a):
    sys.path.insert(0, str(HERE / "tools"))
    import make_samples
    make_samples.main(Path(a.project), a.size)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ds", description="Driftscape ambience video pipeline")
    ap.add_argument("-v", "--verbose", action="store_true", help="print ffmpeg commands")
    ap.add_argument("-d", "--duration", help="override project.duration for this run, e.g. 3m for a "
                    "short full-quality sample (put it before the command: ./ds -d 3m render <project>)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    def add(name, fn, help_, project=True):
        s = sub.add_parser(name, help=help_)
        if project:
            s.add_argument("project")
        s.set_defaults(fn=fn)
        return s
    add("new", cmd_new, "create a project folder from the template")
    add("doctor", cmd_doctor, "check dependencies", project=False)
    add("import", cmd_import, "normalise clips from inbox/").add_argument("--source", help="other folder")
    add("analyze", cmd_analyze, "loop compatibility + artifact report")
    add("loops", cmd_loops, "build seamless loop sources")
    add("plan", cmd_plan, "show the timeline plan")
    add("audio", cmd_audio, "full-length mix + loudness normalisation")
    add("preview", cmd_preview, "low-res preview + seam reel + QC")
    add("render", cmd_render, "final video + QC")
    add("thumbs", cmd_thumbs, "thumbnail candidates")
    add("meta", cmd_meta, "YouTube title/description/tags")
    add("qc", cmd_qc, "re-run QC").add_argument("--final", action="store_true")
    add("all", cmd_all, "import -> preview -> thumbs -> meta").add_argument(
        "--final", action="store_true", help="also render the final video")
    up = add("upload", cmd_upload, "upload to YouTube (asks for confirmation)")
    up.add_argument("--i-confirm", action="store_true", help="required to actually upload")
    up.add_argument("--dry-run", action="store_true")
    up.add_argument("--thumbnail")
    cl = add("clips", cmd_clips, "clip queue + Gemini/Flow browser assistant (see README)", project=False)
    cl.add_argument("action", choices=["add", "list", "retry", "watch", "send", "chrome", "check", "one", "run"])
    cl.add_argument("prompts", nargs="*", help="prompt text(s) for add; project folder for send")
    cl.add_argument("--file", help="add: text file with prompts separated by blank lines")
    cl.add_argument("--name", default="", help="add: short name for the clip file")
    cl.add_argument("--dir", help="clips folder (default ~/Driftscape/Veo-Clips or $DS_CLIPS_DIR)")
    cl.add_argument("--site", choices=["gemini", "flow"], default="gemini")
    cl.add_argument("--max", type=int, default=0, help="run/watch: most prompts this run (run default 5)")
    cl.add_argument("--timeout", type=float, default=20, help="watch: minutes to wait per clip")
    cl.add_argument("--only", nargs="*", help="send: only these clip names or ids")
    cl.add_argument("--run", action="store_true", help="send: then run the pipeline preview on the project")
    add("samples", cmd_samples, "generate a synthetic sample project").add_argument(
        "--size", default="1920x1080", help="clip size, e.g. 1280x720")
    a = ap.parse_args(argv)
    ff.SETTINGS["verbose"] = a.verbose
    global DURATION_OVERRIDE
    DURATION_OVERRIDE = a.duration
    try:
        return a.fn(a) or 0
    except ff.FFmpegError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nInterrupted. Re-run the same command to resume (finished pieces are cached).")
        return 130
