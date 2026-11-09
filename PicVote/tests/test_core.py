"""验收自测：配额、清理、冻结、分页、改票、来源解析。"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402
from job import run_job  # noqa: E402
from sources import load_sources, sniff_ext  # noqa: E402
from storage import Store  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
JPG = b"\xff\xd8\xff" + b"0" * 64


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="picvote-test-")
        self.cfg = Config(root=self.tmp, quota_bytes=10 * 1024, page_size=20)
        self.store = Store(self.cfg)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fill(self, n, cat="beauty", blob=None):
        for _ in range(n):
            self.store.add(blob or PNG, cat, "test-src", ".png")


class TestStorage(Base):
    def test_add_and_reload_atomic_index(self):
        self.fill(3)
        self.store.save()
        again = Store(self.cfg)
        self.assertEqual(len(again.items), 3)
        self.assertEqual(again.used_bytes, 3 * len(PNG))
        self.assertEqual(
            [i["id"] for i in again.items], [1, 2, 3]
        )

    def test_quota_never_exceeded(self):
        self.cfg.quota_bytes = 2 * len(PNG) + 1
        self.store = Store(self.cfg)
        self.assertIsNotNone(self.store.add(PNG, "beauty", "a", ".png"))
        self.assertIsNotNone(self.store.add(PNG, "beauty", "b", ".png"))
        self.assertIsNone(self.store.add(PNG, "beauty", "c", ".png"))
        self.assertEqual(self.store.used_bytes, 2 * len(PNG))
        self.assertEqual(len(os.listdir(self.cfg.images_dir)), 2)

    def test_refresh_picks_up_external_job_now(self):
        """回归：--job-now 是独立进程写盘，长驻服务必须能看到新图。"""
        other = Store(self.cfg)
        self.assertEqual(len(other.items), 0)
        self.store.add(PNG, "beauty", "external", ".png")
        self.store.save()
        self.store.add(PNG, "beauty", "external2", ".png")
        self.store.save()
        other.refresh_if_changed()
        self.assertEqual(len(other.items), 2)
        self.assertEqual(other.used_bytes, 2 * len(PNG))

    def test_vote_toggle_and_change_xx_not_delete(self):
        self.fill(1)
        self.assertEqual(self.store.vote(1, "oo"), "oo")
        self.assertEqual(self.store.vote(1, "oo"), None)
        self.assertEqual(self.store.vote(1, "xx"), "xx")
        self.assertEqual(self.store.vote(1, "oo"), "oo")
        self.assertEqual(self.store.vote(1, "oo"), None)
        self.assertEqual(len(self.store.items), 1)

    def test_page_size_order_and_category_isolation(self):
        self.cfg.quota_bytes = 10 ** 9
        self.store = Store(self.cfg)
        self.fill(45, "beauty")
        self.fill(5, "handsome")
        p1 = self.store.page("beauty", 1)
        self.assertEqual(len(p1["items"]), 20)
        self.assertEqual([i["id"] for i in p1["items"]], list(range(1, 21)))
        self.assertEqual(p1["pages"], 3)
        self.assertEqual(len(self.store.page("beauty", 3)["items"]), 5)
        self.assertEqual(self.store.page("handsome", 1)["total"], 5)
        self.assertEqual(self.store.page("beauty", 999)["page"], 3)
        self.assertEqual(self.store.page("unknown", 1)["total"], 0)


class TestJob(Base):
    def test_cleanup_removes_oldest_10_percent_and_keeps_liked(self):
        self.cfg.quota_bytes = 10 ** 9
        self.store = Store(self.cfg)
        self.fill(20)
        self.store.save()
        for item_id in (1, 2, 3):
            self.store.vote(item_id, "oo")
        result = run_job(self.store, self.cfg, log=lambda m: None, force=True)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detail["removed"], 2)
        ids = [i["id"] for i in self.store.items]
        self.assertIn(1, ids)
        self.assertIn(2, ids)
        self.assertIn(3, ids)
        self.assertNotIn(4, ids)
        self.assertNotIn(5, ids)
        self.assertEqual(len(ids), 18)

    def test_same_day_only_once(self):
        first = run_job(self.store, self.cfg, log=lambda m: None)
        self.assertEqual(first.status, "ok")
        second = run_job(self.store, self.cfg, log=lambda m: None)
        self.assertEqual(second.status, "already_ran")

    def test_frozen_state_stops_everything(self):
        self.cfg.quota_bytes = 10 * len(PNG)
        self.store = Store(self.cfg)
        self.fill(10)
        for item_id in range(1, 11):
            self.store.vote(item_id, "oo")
        self.store.save()
        result = run_job(self.store, self.cfg, log=lambda m: None, force=True)
        self.assertEqual(result.status, "frozen")
        self.assertTrue(self.store.frozen)
        before = [i["id"] for i in self.store.items]
        files = sorted(os.listdir(self.cfg.images_dir))
        again = run_job(self.store, self.cfg, log=lambda m: None, force=True)
        self.assertEqual(again.status, "frozen")
        self.assertEqual([i["id"] for i in self.store.items], before)
        self.assertEqual(sorted(os.listdir(self.cfg.images_dir)), files)
        self.assertIsNone(self.store.add(PNG, "beauty", "x", ".png"))

    def test_crawl_refills_after_cleanup(self):
        img_dir = os.path.join(self.tmp, "incoming")
        os.makedirs(img_dir)
        with open(os.path.join(img_dir, "a.png"), "wb") as f:
            f.write(JPG)
        with open(self.cfg.sources_path, "w", encoding="utf-8") as f:
            f.write("beauty|dir|./incoming\n")
        self.cfg.quota_bytes = 10 ** 9
        self.store = Store(self.cfg)
        self.fill(20)
        self.store.save()
        result = run_job(self.store, self.cfg, log=lambda m: None, force=True)
        self.assertEqual(result.detail["added"], 1)
        self.assertEqual(len(self.store.items), 19)


class TestSources(Base):
    def test_sniff_ext(self):
        self.assertEqual(sniff_ext(PNG), ".png")
        self.assertEqual(sniff_ext(JPG), ".jpg")
        self.assertIsNone(sniff_ext(b"<html>not an image</html>"))

    def test_load_sources_parsing(self):
        with open(self.cfg.sources_path, "w", encoding="utf-8") as f:
            f.write("# comment\nbeauty|page|https://example.com/a\n")
            f.write("handsome|image|https://example.com/b.jpg\n")
            f.write("beauty|dir|./incoming\n")
            f.write("bad-line\ninvalid|page|https://example.com/c\n")
        sources = load_sources(self.cfg, log=lambda m: None)
        self.assertEqual(len(sources), 3)
        self.assertEqual(sources[0].cat, "beauty")


if __name__ == "__main__":
    unittest.main(verbosity=2)
