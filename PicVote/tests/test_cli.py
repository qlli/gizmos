"""端到端自检：真实入口 app.py --job-now / --status。"""
import contextlib
import io
import json
import logging
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app  # noqa: E402


class _FakeStop:
    """让 scheduler 恰好跑一轮后退出，不真的等待 60 秒。"""

    def __init__(self):
        self.n = 0

    def is_set(self):
        return self.n > 0

    def wait(self, seconds):
        self.n += 1
        return self.n > 0

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="picvote-cli-")
        self.old_root = os.environ.get("PICVOTE_ROOT")
        os.environ["PICVOTE_ROOT"] = self.tmp
        incoming = os.path.join(self.tmp, "incoming")
        os.makedirs(incoming)
        for name in ("a.png", "b.png", "c.png"):
            with open(os.path.join(incoming, name), "wb") as f:
                f.write(PNG)
        with open(os.path.join(self.tmp, "sources.txt"), "w", encoding="utf-8") as f:
            f.write("beauty|dir|./incoming\n")

    def tearDown(self):
        if self.old_root is None:
            os.environ.pop("PICVOTE_ROOT", None)
        else:
            os.environ["PICVOTE_ROOT"] = self.old_root
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_job_now_then_status(self):
        self.assertEqual(app.main(["--job-now"]), 0)
        with open(os.path.join(self.tmp, "data", "index.json"), "r", encoding="utf-8") as f:
            index = json.load(f)
        self.assertEqual(len(index["items"]), 3)
        self.assertEqual(index["items"][0]["cat"], "beauty")
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "data", "images", "00000001.png")))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(app.main(["--status"]), 0)
        self.assertIn("used_bytes", buf.getvalue())

    def test_should_run_rules(self):
        from config import Config
        from storage import Store
        cfg = Config(root=self.tmp, job_hour=3)
        store = Store(cfg)
        self.assertTrue(app.should_run(datetime(2026, 11, 8, 3, 30), cfg, store))
        self.assertFalse(app.should_run(datetime(2026, 11, 8, 14, 0), cfg, store))
        store.data["last_job_date"] = "2026-11-08"
        self.assertFalse(app.should_run(datetime(2026, 11, 8, 3, 30), cfg, store))
        store.data["last_job_date"] = ""
        store.data["frozen"] = True
        self.assertFalse(app.should_run(datetime(2026, 11, 8, 3, 30), cfg, store))

    def test_scheduler_accepts_logger(self):
        """回归：scheduler 收到 Logger 对象而非可调用对象，不能崩溃。"""
        from config import Config
        from storage import Store
        cfg = Config(root=self.tmp, job_hour=datetime.now().hour)
        store = Store(cfg)
        logger = logging.getLogger("picvote-test-scheduler")
        logger.addHandler(logging.NullHandler())
        app.scheduler(store, cfg, logger, _FakeStop())
        self.assertEqual(store.last_job_date, datetime.now().date().isoformat())


if __name__ == "__main__":
    unittest.main(verbosity=2)
