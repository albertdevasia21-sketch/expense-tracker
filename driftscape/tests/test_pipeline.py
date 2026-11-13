"""End-to-end + unit tests. Run:  python3 -m unittest discover -s tests -v   (~1-2 min)"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import numpy as np  # noqa: E402

from dscape import cli, ff  # noqa: E402
from dscape.config import Project, parse_duration  # noqa: E402
from dscape.meta import validate  # noqa: E402


class Units(unittest.TestCase):
    def test_durations(self):
        self.assertEqual(parse_duration("3h"), 10800)
        self.assertEqual(parse_duration("2h30m"), 9000)
        self.assertEqual(parse_duration("1:00:30"), 3630)
        self.assertEqual(parse_duration(45), 45)

    def test_meta_limits(self):
        md = {"title": "x" * 101, "description": "a<b", "tags": ["t" * 300, "u u" * 70],
              "privacy": "private"}
        errs = " ".join(validate(md))
        self.assertIn("title", errs)
        self.assertIn("'<'", errs)
        self.assertIn("tags", errs)


class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.proj = Path(cls.tmp.name) / "p"
        import make_samples
        make_samples.main(cls.proj, "320x180")
        cfg = (cls.proj / "project.toml").read_text()
        cfg = cfg.replace('duration = "3h"', 'duration = "150s"')
        cfg = re.sub(r"cycle_minutes = [\d.]+", "cycle_minutes = 0.75", cfg)
        cfg = cfg.replace("hold_min = 20", "hold_min = 8").replace("hold_max = 45", "hold_max = 14")
        (cls.proj / "project.toml").write_text(cfg)
        assert cli.main(["all", str(cls.proj), "--final"]) == 0

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def j(self, rel):
        return json.loads((self.proj / rel).read_text())

    def test_analysis_flags_defects(self):
        a = self.j("work/analysis.json")["clips"]
        self.assertTrue(a["aurora_glitch"]["excluded"], "flash/jump-cut clip must be auto-excluded")
        self.assertEqual(len(a["aurora_glitch"]["spikes"]), 3)
        self.assertEqual(a["camera_push"]["mode"], "oneshot")
        self.assertIn(a["rain_window"]["grade"], "AB")

    def test_loop_wrap_is_seamless(self):
        loops = self.j("work/loops.json")
        for cid, L in loops.items():
            if L["mode"] != "loop":
                continue
            g = ff.read_frames(self.proj / L["file"], 160, 90).astype(np.float32)
            step = np.median(np.mean(np.abs(np.diff(g, axis=0)), axis=(1, 2)))
            wrap = np.mean(np.abs(g[0] - g[-1]))
            self.assertLess(wrap, 2.0 * step + 0.5, f"{cid}: wrap {wrap:.2f} vs step {step:.2f}")

    def test_final_qc(self):
        q = self.j("out/reports/qc_final.json")
        self.assertTrue(q["pass"], json.dumps(q["checks"], indent=1))
        self.assertFalse([e for e in q["scan"]["events"] if e["flag"]])

    def test_final_file(self):
        p = Project(self.proj)
        f = self.j("work/final.json")["file"]
        self.assertEqual(ff.count_frames(f), int(150 * 24))
        info = ff.probe(f)
        self.assertAlmostEqual(float(info["format"]["duration"]), 150, delta=0.5)
        self.assertIsNotNone(ff.audio_stream(info))
        L = self.j("out/reports/qc_final.json")["loudness"]
        self.assertAlmostEqual(L["integrated_lufs"], p.cfg["audio"]["target_lufs"], delta=1.0)

    def test_deliverables(self):
        thumbs = list((self.proj / "out" / "thumbnails").glob("thumb_*.jpg"))
        self.assertTrue(thumbs)
        for t in thumbs:
            self.assertLess(t.stat().st_size, 2 * 1024 * 1024)
        md = self.j("out/metadata.json")
        self.assertEqual(md["validation_errors"], [])
        self.assertEqual(md["privacy"], "private")
        self.assertIn("Drone pad", md["description"])          # attribution credit
        self.assertTrue((self.proj / "out" / "preview.mp4").exists())
        self.assertTrue((self.proj / "out" / "seams_review.mp4").exists())

    def test_upload_never_runs_without_confirmation(self):
        with self.assertRaises(SystemExit):
            cli.main(["upload", str(self.proj)])            # no --i-confirm -> refuses
        self.assertFalse((self.proj / "out" / "upload.json").exists())

    def test_missing_license_blocks_final(self):
        p = self.proj / "project.toml"
        orig = p.read_text()
        try:
            p.write_text(re.sub(r'license = "Synthetic sample \(CC0\)"', 'license = ""', orig))
            with self.assertRaises(SystemExit):
                cli.main(["render", str(self.proj)])
        finally:
            p.write_text(orig)


if __name__ == "__main__":
    unittest.main()
