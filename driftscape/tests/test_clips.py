"""Tests for the clip queue and the browser assistant (against a local mock site).

Run:  python3 -m unittest tests.test_clips -v
The browser tests need Playwright and a Chrome/Chromium binary; they are skipped otherwise.
The real Gemini / Flow pages are NOT exercised here - that needs your signed-in browser.
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from dscape import clips  # noqa: E402
import mock_site  # noqa: E402


def chrome_binary():
    cands = [os.environ.get("DS_CHROME"), *glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"),
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             shutil.which("google-chrome"), shutil.which("chromium")]
    return next((c for c in cands if c and Path(c).exists()), None)


class QueueAndVerify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = clips.clips_dir(str(Path(self.tmp.name) / "Veo-Clips"))
        self.src = mock_site.make_clips(Path(self.tmp.name), 2)
        self.log = clips.get_logger(self.d)

    def tearDown(self):
        self.tmp.cleanup()

    def test_queue_skips_repeated_prompts(self):
        q = clips.Queue(self.d)
        self.assertIsNotNone(q.add("rain in a pine forest", "Forest Rain"))
        self.assertIsNone(q.add("rain  in a pine   forest"))        # same prompt, different spacing
        self.assertEqual(len(clips.Queue(self.d).items), 1)

    def test_prompt_file(self):
        f = Path(self.tmp.name) / "p.txt"
        f.write_text("# comment\nname: stream\na forest stream\nin the rain\n\nfog over treetops\n")
        self.assertEqual(clips.parse_prompt_file(f),
                         [("a forest stream in the rain", "stream"), ("fog over treetops", "")])

    def test_register_verifies_and_blocks_duplicates(self):
        q = clips.Queue(self.d)
        a, b, c = q.add("one"), q.add("two"), q.add("three")
        inc = self.d / "_incoming"
        shutil.copy(self.src[0], inc / "x.mp4")
        self.assertTrue(clips.register(q, a, inc / "x.mp4", self.log))
        self.assertTrue((self.d / a["file"]).exists())
        shutil.copy(self.src[0], inc / "again.mp4")                 # identical bytes
        self.assertFalse(clips.register(q, b, inc / "again.mp4", self.log))
        self.assertIn("duplicate", b["error"])
        bad = inc / "cut.mp4"
        bad.write_bytes(self.src[1].read_bytes()[: self.src[1].stat().st_size // 3])
        self.assertFalse(clips.register(q, c, bad, self.log))        # truncated download
        self.assertEqual(len(list(self.d.glob("*.mp4"))), 1)
        self.assertEqual(len(list((self.d / "_rejected").iterdir())), 2)

    def test_send_to_project_without_duplicates(self):
        from dscape import cli
        q = clips.Queue(self.d)
        a = q.add("one", "forest")
        shutil.copy(self.src[0], self.d / "_incoming" / "x.mp4")
        clips.register(q, a, self.d / "_incoming" / "x.mp4", self.log)
        proj = Path(self.tmp.name) / "proj"
        cli.main(["new", str(proj)])
        self.assertEqual(clips.cmd_send(self.d, str(proj), []), 1)
        self.assertTrue((proj / "inbox" / "forest.mp4").exists())
        self.assertEqual(clips.cmd_send(self.d, str(proj), []), 0)   # second send adds nothing

    def test_watch_picks_up_a_manual_download(self):
        q = clips.Queue(self.d)
        q.add("manual clip", "manual")
        os.environ["DS_DOWNLOAD_DIR"] = str(Path(self.tmp.name) / "dl")
        (Path(self.tmp.name) / "dl").mkdir()
        try:
            import threading
            threading.Timer(1.0, lambda: shutil.copy(self.src[1], Path(self.tmp.name) / "dl" / "video.mp4")).start()
            clips.cmd_watch(self.d, timeout_min=0.5, limit=0)
        finally:
            del os.environ["DS_DOWNLOAD_DIR"]
        self.assertEqual(clips.Queue(self.d).items[0]["status"], "done")


@unittest.skipUnless(chrome_binary(), "no Chrome/Chromium binary")
class BrowserAssistant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import playwright  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("playwright not installed")
        cls.tmp = tempfile.TemporaryDirectory()
        t = Path(cls.tmp.name)
        cls.srv, cls.state = mock_site.serve(t)
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}/"
        os.environ["DS_CHROME_PORT"] = "9377"
        os.environ["DS_DOWNLOAD_DIR"] = str(t / "dl")
        (t / "dl").mkdir()
        cls.chrome = subprocess.Popen(
            [chrome_binary(), "--headless=new", "--no-sandbox", "--remote-debugging-port=9377",
             f"--user-data-dir={t / 'profile'}", "--no-first-run", cls.url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import importlib
        from dscape import browser
        cls.browser = importlib.reload(browser)                     # pick up DS_CHROME_PORT
        for _ in range(50):
            if cls.browser.port_open():
                break
            time.sleep(0.2)
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.chrome.terminate()
        cls.chrome.wait(timeout=10)
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.tmp.cleanup()
        os.environ.pop("DS_CHROME_PORT", None)
        os.environ.pop("DS_DOWNLOAD_DIR", None)

    def fresh(self, name):
        d = clips.clips_dir(str(Path(self.tmp.name) / name))
        (d / "browser.toml").write_text(
            f'pause_between_s = 1\ngenerate_timeout_s = 20\nnew_chat_each_prompt = true\n[gemini]\nurl = "{self.url}"\nhost = "127.0.0.1"\n'
            'prompt_prefix = "Generate a video: "\n')
        return d, clips.Queue(d), clips.get_logger(d)

    def test_1_check_is_read_only(self):
        d, q, log = self.fresh("c1")
        before = len(self.state["prompts"])
        self.assertTrue(self.browser.cmd_check(d, "gemini"))
        self.assertEqual(len(self.state["prompts"]), before)         # nothing was generated

    def test_2_batch_locked_until_single_test(self):
        d, q, log = self.fresh("c2")
        q.add("a quiet lake")
        with self.assertRaises(SystemExit):
            self.browser.cmd_run(d, "gemini", 5)
        self.assertEqual(clips.Queue(d).items[0]["status"], "pending")

    def test_3_generate_download_verify(self):
        d, q, log = self.fresh("c3")
        q.add("misty pine forest in rain", "forest")
        q.add("stream over mossy rocks", "stream")
        n = self.browser._run(d, "gemini", q.pending(), False, q, log)
        self.assertEqual(n, 2)
        q = clips.Queue(d)
        self.assertEqual([i["status"] for i in q.items], ["done", "done"])
        self.assertEqual(sorted(p.name for p in d.glob("*.mp4")), ["001_forest.mp4", "002_stream.mp4"])
        self.assertNotEqual(q.items[0]["sha256"], q.items[1]["sha256"])
        self.assertIn("Generate a video: misty pine forest in rain", self.state["prompts"])

    def test_4_usage_limit_stops_the_run(self):
        d, q, log = self.fresh("c4")
        q.add("LIMIT please", "first")
        q.add("never reached", "second")
        before = len(self.state["prompts"])
        n = self.browser._run(d, "gemini", q.pending(), False, q, log)
        self.assertEqual(n, 0)
        q = clips.Queue(d)
        self.assertEqual(q.items[0]["status"], "blocked")
        self.assertIn("limit", q.items[0]["error"].lower())
        self.assertEqual(q.items[1]["status"], "pending")            # not attempted
        self.assertEqual(len(self.state["prompts"]), before + 1)     # exactly one request, no retry

    def test_5_duplicate_and_broken_downloads_rejected(self):
        d, q, log = self.fresh("c5")
        q.add("fresh clip", "a")
        q.add("DUPLICATE of the last one", "b")
        self.browser._run(d, "gemini", q.pending(), False, q, log)
        q = clips.Queue(d)
        self.assertEqual(q.items[0]["status"], "done")
        self.assertEqual(q.items[1]["status"], "failed")
        self.assertIn("duplicate", q.items[1]["error"])
        d2, q2, log2 = self.fresh("c6")
        q2.add("BROKEN download", "x")
        self.browser._run(d2, "gemini", q2.pending(), False, q2, log2)
        self.assertEqual(clips.Queue(d2).items[0]["status"], "failed")
        self.assertEqual(list(d2.glob("*.mp4")), [])


if __name__ == "__main__":
    unittest.main()
