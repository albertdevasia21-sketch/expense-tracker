"""Supervised browser assistant for Gemini / Google Flow.

How it works
  1. `./ds clips chrome` opens an ordinary Chrome window with its own profile.
     YOU sign in to Google by hand. This tool never sees or types credentials.
  2. The assistant attaches to that window (Chrome DevTools protocol, via
     Playwright), types a queued prompt, submits it, waits for the video and
     clicks Download - the same clicks you would make, one prompt at a time.

Hard rules (by design, do not weaken)
  * No stealth: no fingerprint spoofing, no automation-flag hiding, no headless.
  * Sign-in pages, CAPTCHAs, "verify it's you" and usage-limit messages are
    never worked around. The run stops and tells you what it saw.
  * One generation at a time, a pause between prompts, a cap per run.
  * Whenever the page does not look as expected, it asks you to do that one
    step by hand and carries on, instead of guessing.

The page structure of Google's sites changes without notice. All selectors are
in DEFAULTS and can be overridden in <Veo-Clips>/browser.toml (see README).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import clips

PORT = int(os.environ.get("DS_CHROME_PORT", "9222"))
PROFILE = Path.home() / ".driftscape" / "chrome-profile"

DEFAULTS = {
    "gemini": {
        "url": "https://gemini.google.com/app",
        "host": "gemini.google.com",
        "prompt_prefix": "Generate a video: ",
        "new_chat_each_prompt": True,
    },
    "flow": {
        "url": "https://labs.google/fx/tools/flow",
        "host": "labs.google",
        "prompt_prefix": "",
        "new_chat_each_prompt": False,
    },
    "common": {
        # Tried in order; the last visible match is used.
        "prompt_box": ["div[contenteditable='true'][role='textbox']", "rich-textarea div[contenteditable='true']",
                       "textarea", "div[contenteditable='true']", "[role='textbox']"],
        # Buttons whose accessible name matches are tried before pressing Enter.
        "submit_name": r"^(send( message)?|submit|generate|create)$",
        "download_name": r"download",
        "video": "video",
        # Page text that means: stop, a human must look at this.
        "blockers": {
            "usage limit": r"(reached|hit|exceeded) (your|the)[\w\s]{0,30}limit|limit (resets|reached)|"
                           r"out of credits|no credits|quota|try again (tomorrow|later)|come back (tomorrow|later)",
            "security check": r"verify it.?s you|unusual (traffic|activity)|not a robot|captcha|"
                              r"this browser or app may not be secure|couldn.?t sign you in",
            "generation refused": r"can.?t (generate|create|help with) (that|this|videos?)|"
                                  r"(violat|against)\w* (our|the) polic|unable to generate",
        },
        "generate_timeout_s": 600,
        "pause_between_s": 20,
    },
}


class Blocked(Exception):
    """The site showed something that must not be automated past."""


class NeedsHuman(Exception):
    pass


def load_cfg(d: Path, site: str) -> dict:
    cfg = {**DEFAULTS["common"], **DEFAULTS[site]}
    f = d / "browser.toml"
    if f.exists():
        import tomllib
        user = tomllib.loads(f.read_text())
        cfg.update({k: v for k, v in user.items() if not isinstance(v, dict) or k == "blockers"})
        cfg.update(user.get(site, {}))
    return cfg


# --- Chrome ------------------------------------------------------------------------
def find_chrome() -> str | None:
    cands = [os.environ.get("DS_CHROME"),
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             shutil.which("google-chrome"), shutil.which("google-chrome-stable"), shutil.which("chromium")]
    return next((c for c in cands if c and Path(c).exists()), None)


def port_open() -> bool:
    import socket
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def cmd_chrome(d: Path, site: str) -> None:
    cfg = load_cfg(d, site)
    if port_open():
        print(f"  A Chrome window for Driftscape is already running (port {PORT}).")
        return
    exe = find_chrome()
    if not exe:
        raise SystemExit("Google Chrome not found. Install it, or set DS_CHROME to its path.")
    PROFILE.mkdir(parents=True, exist_ok=True)
    (d / "_incoming").mkdir(exist_ok=True)
    # Plain Chrome: only the debugging port and a separate profile. Nothing that hides automation.
    subprocess.Popen([exe, f"--remote-debugging-port={PORT}", "--remote-debugging-address=127.0.0.1",
                      f"--user-data-dir={PROFILE}", "--no-first-run", "--no-default-browser-check", cfg["url"]],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    print(f"""  Chrome opened with a separate Driftscape profile.
  1. Sign in to your Google account in that window, by hand.
  2. Open the video tool and make sure you can see the prompt box.
  3. Leave the window open, then run:  ./ds clips check

  If Google refuses the sign-in in this window ("This browser or app may not be
  secure"), do not try to get around it. Close the window and use the manual
  mode instead:  ./ds clips watch""")


class Session:
    def __init__(self, d: Path, site: str, log):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise SystemExit("Browser assistant needs Playwright:  pip install -r requirements-browser.txt\n"
                             "(the manual mode `./ds clips watch` needs nothing extra)")
        if not port_open():
            raise SystemExit("No Driftscape Chrome window found. Start one with:  ./ds clips chrome")
        self.d, self.site, self.log, self.cfg = d, site, log, load_cfg(d, site)
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
        ctx = self.browser.contexts[0]
        pages = [p for p in ctx.pages if self.cfg["host"] in p.url]
        self.page = pages[-1] if pages else None
        self.downloads: list[Path] = []
        if self.page:
            self.page.on("download", self._on_download)

    def _on_download(self, download) -> None:
        try:
            dest = self.d / "_incoming" / (f"{int(time.time())}_" + (download.suggested_filename or "clip.mp4"))
            download.save_as(str(dest))
            self.downloads.append(dest)
        except Exception as e:               # falls back to watching the Downloads folder
            self.log.warning(f"could not capture the download directly ({e}); watching folders instead")

    def close(self) -> None:
        try:
            self._pw.stop()                  # detaches; the Chrome window stays open
        except Exception:
            pass

    # --- page state ---
    def text(self) -> str:
        try:
            return self.page.inner_text("body", timeout=5000)
        except Exception:
            return ""

    def check_blockers(self, baseline: str = "") -> None:
        url = self.page.url
        if "accounts.google.com" in url or "/signin" in url:
            raise Blocked("sign-in page: you are signed out. Sign in by hand in the Chrome window.")
        body = self.text()
        new = body.replace(baseline, "") if baseline else body
        for kind, pat in self.cfg["blockers"].items():
            m = re.search(pat, new, re.I)
            if m:
                raise Blocked(f"{kind}: the page says \"{_around(new, m)}\"")

    def prompt_box(self):
        for sel in self.cfg["prompt_box"]:
            loc = self.page.locator(sel)
            for k in range(loc.count() - 1, -1, -1):
                if loc.nth(k).is_visible():
                    return loc.nth(k)
        return None

    def named_button(self, pattern: str, last: bool = True):
        loc = self.page.get_by_role("button", name=re.compile(pattern, re.I))
        idx = range(loc.count() - 1, -1, -1) if last else range(loc.count())
        for k in idx:
            b = loc.nth(k)
            if b.is_visible() and b.is_enabled():
                return b
        return None

    def video_count(self) -> int:
        return self.page.locator(self.cfg["video"]).count()


def _around(text: str, m: re.Match, n: int = 70) -> str:
    return " ".join(text[max(0, m.start() - n): m.end() + n].split())


def _ask(msg: str) -> None:
    if not sys.stdin.isatty():
        raise NeedsHuman(msg)
    input(f"\n  >> {msg}\n     Press Enter when done (Ctrl-C to stop) ")


# --- commands ------------------------------------------------------------------------
def cmd_check(d: Path, site: str) -> bool:
    """Read-only: attach and report what the assistant can see. Generates nothing."""
    log = clips.get_logger(d)
    s = Session(d, site, log)
    try:
        if not s.page:
            print(f"  [--] no tab open on {s.cfg['host']}. Open {s.cfg['url']} in the Driftscape Chrome window.")
            return False
        print(f"  [ok] attached to tab: {s.page.url[:80]}")
        ok = True
        try:
            s.check_blockers()
            print("  [ok] no sign-in, security or limit message on the page")
        except Blocked as e:
            print(f"  [--] {e}")
            ok = False
        box = s.prompt_box()
        print(f"  [{'ok' if box else '--'}] prompt box " + ("found" if box else
              "NOT found - is the video tool open? Otherwise set prompt_box in browser.toml"))
        btn = s.named_button(s.cfg["submit_name"])
        print(f"  [{'ok' if btn else '..'}] send button " + ("found" if btn else
              "not visible yet (normal while the box is empty; Enter is used as fallback)"))
        print(f"  [..] videos currently on the page: {s.video_count()}")
        names = [n for n in s.page.get_by_role("button").evaluate_all(
            "els => els.map(e => (e.getAttribute('aria-label') || e.innerText || '').trim()).filter(Boolean)")][:40]
        print("  [..] visible button names (for browser.toml if something is not found):")
        print("       " + " | ".join(dict.fromkeys(n[:28] for n in names)))
        ok = ok and bool(box)
        print("\n  Ready for the single test:  ./ds clips one" if ok else
              "\n  Not ready. Fix the items marked [--], or use manual mode:  ./ds clips watch")
        return ok
    finally:
        s.close()


def generate(s: Session, q: clips.Queue, item: dict, approve: bool) -> bool:
    """One prompt -> one verified clip. Raises Blocked when the site must be handled by a person."""
    log, cfg, page = s.log, s.cfg, s.page
    page.bring_to_front()
    s.check_blockers()
    baseline = s.text()
    videos_before = s.video_count()
    dirs = clips.download_dirs(s.d)
    files_before = clips.snapshot(dirs)
    n_dl = len(s.downloads)
    text = cfg["prompt_prefix"] + item["prompt"]

    box = s.prompt_box()
    if box:
        box.click()
        page.keyboard.press("ControlOrMeta+A")
        page.keyboard.press("Backspace")
        page.keyboard.insert_text(text)
        log.info(f"#{item['id']}: prompt typed ({len(text)} chars)")
    else:
        clips.copy_to_clipboard(text)
        _ask("I can't find the prompt box. The prompt is on your clipboard: paste it into the video tool "
             "(do not send it yet).")
    if approve:
        _ask("Check the prompt in the Chrome window. This will use one generation from your allowance.\n"
             "     To go ahead, leave the window as it is.")
    item["attempts"] += 1
    item["status"] = "generating"
    q.save()

    btn = s.named_button(cfg["submit_name"])
    if btn:
        btn.click()
    elif box:
        page.keyboard.press("Enter")
    else:
        _ask("Click the send / generate button in the Chrome window.")
    log.info(f"#{item['id']}: submitted, waiting for the video (up to {cfg['generate_timeout_s'] // 60} min)")

    end = time.time() + cfg["generate_timeout_s"]
    while s.video_count() <= videos_before:
        if time.time() > end:
            raise NeedsHuman("no video appeared in time")
        s.check_blockers(baseline)
        page.wait_for_timeout(3000)
    page.wait_for_timeout(2000)
    log.info(f"#{item['id']}: video is ready, downloading")

    vid = page.locator(cfg["video"]).last
    try:
        vid.scroll_into_view_if_needed(timeout=5000)
        vid.hover(timeout=5000)
    except Exception:
        pass
    dl = s.named_button(cfg["download_name"])
    if dl:
        dl.click()
    else:
        _ask("I can't find the Download button. Click Download on the new video in the Chrome window.")

    got = None
    end = time.time() + 180
    asked = False
    while not got and time.time() < end:
        page.wait_for_timeout(1000)
        if len(s.downloads) > n_dl:
            got = s.downloads[-1]
            break
        got = clips.wait_for_new_video(dirs, files_before, timeout=1.5, poll=0.5)
        if not got and not asked and time.time() > end - 150 and sys.stdin.isatty():
            asked = True
            _ask("No download seen yet. If a menu opened (e.g. a quality choice), pick an option in Chrome.")
    if not got:
        raise NeedsHuman("the download did not arrive")
    return clips.register(q, item, got, log)


def _run(d: Path, site: str, items: list[dict], approve: bool, q: clips.Queue, log) -> int:
    s = Session(d, site, log)
    done = fails = 0
    try:
        if not s.page:
            raise SystemExit(f"No tab open on {s.cfg['host']}. Run ./ds clips check first.")
        for n, item in enumerate(items):
            if n:
                log.info(f"pausing {s.cfg['pause_between_s']}s before the next prompt")
                time.sleep(s.cfg["pause_between_s"])
            if s.cfg.get("new_chat_each_prompt"):
                # a fresh conversation per prompt: no old videos or old messages to confuse the checks
                nb = s.named_button(r"^new chat$", last=False)
                if nb:
                    nb.click()
                    s.page.wait_for_timeout(2500)
            try:
                if generate(s, q, item, approve):
                    done, fails = done + 1, 0
                else:
                    fails += 1
            except Blocked as e:
                item.update(status="blocked", error=str(e))
                q.save()
                log.error(f"STOPPED - {e}")
                log.error("Nothing was bypassed. Deal with it in the Chrome window (or wait for your allowance "
                          "to reset), then:  ./ds clips retry")
                log.error("If that text is only an old message in the conversation, start a new chat first.")
                break
            except NeedsHuman as e:
                item.update(status="failed", error=str(e))
                q.save()
                log.error(f"#{item['id']} failed: {e}")
                fails += 1
            except KeyboardInterrupt:
                item.update(status="pending")
                q.save()
                log.info("stopped by you; the queue is saved")
                break
            except Exception as e:           # page changed, tab closed, etc.
                item.update(status="failed", error=f"{type(e).__name__}: {str(e).splitlines()[0][:160]}")
                q.save()
                log.error(f"#{item['id']} failed: {item['error']}")
                fails += 1
            if fails >= 2:
                log.error("two failures in a row - stopping so nothing is wasted. Run ./ds clips check, "
                          "or switch to ./ds clips watch")
                break
    finally:
        s.close()
    return done


def cmd_one(d: Path, site: str) -> None:
    """The approval-gated single test. Batch mode stays locked until this succeeds."""
    q, log = clips.Queue(d), clips.get_logger(d)
    todo = q.pending()
    if not todo:
        raise SystemExit("Queue is empty. Add a prompt first:  ./ds clips add \"...\"")
    if not sys.stdin.isatty():
        raise SystemExit("The single test needs you at the terminal to approve each step.")
    print(f"  Single test with #{todo[0]['id']} {todo[0]['name']}. You approve before anything is sent.")
    if _run(d, site, todo[:1], True, q, log):
        q.data["single_test_ok"] = True
        q.save()
        log.info("single test passed. Batch mode unlocked:  ./ds clips run")
    else:
        log.error("single test did not complete; batch mode stays locked")


def cmd_run(d: Path, site: str, limit: int) -> None:
    q, log = clips.Queue(d), clips.get_logger(d)
    if not q.data.get("single_test_ok"):
        raise SystemExit("Batch mode is locked until one supervised test succeeds:  ./ds clips one")
    todo = q.pending()[:limit]
    if not todo:
        print("  nothing pending")
        return
    log.info(f"batch: {len(todo)} prompt(s), one at a time (cap {limit} per run)")
    n = _run(d, site, todo, False, q, log)
    log.info(f"batch finished: {n}/{len(todo)} clip(s) saved to {d}")
