"""图床尺寸降级与归一化自检。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources import Fetcher, image_variants, variant_key  # noqa: E402
from config import Config  # noqa: E402

GIF = b"GIF89a" + b"0" * 100
URL1 = "https://img.wangmoyu.com/mw1024/bd5c15582aa3b934cd0b86d2f8f99164.gif"
URL2 = "https://img.toto.im/large/49a01a21ly1ic618vhipjg20jz0qohe1.gif"


class TestVariantKey(unittest.TestCase):
    def test_sizes_collapse_to_one_key(self):
        base = "https://img.toto.im/SIZE/abc.webp"
        for size in ("w600", "mw600", "mw1024", "large", "thumb180"):
            u = "https://img.toto.im/%s/abc.webp" % size
            self.assertEqual(variant_key(u), base, u)

    def test_original_urls_are_distinct(self):
        a = "https://img.toto.im/w600/a.webp"
        b = "https://img.toto.im/w600/b.webp"
        self.assertNotEqual(variant_key(a), variant_key(b))


class TestImageVariants(unittest.TestCase):
    def test_fallback_order(self):
        self.assertEqual(image_variants(URL1), [
            "https://img.wangmoyu.com/mw600/bd5c15582aa3b934cd0b86d2f8f99164.gif",
            "https://img.wangmoyu.com/thumb180/bd5c15582aa3b934cd0b86d2f8f99164.gif",
        ])

    def test_large_is_downgraded(self):
        self.assertEqual(image_variants(URL2)[0],
                         "https://img.toto.im/mw600/49a01a21ly1ic618vhipjg20jz0qohe1.gif")

    def test_no_size_segment_returns_empty(self):
        self.assertEqual(image_variants("https://example.com/pic/a.jpg"), [])


class TestFetcherFallback(unittest.TestCase):
    def setUp(self):
        self.cfg = Config(request_interval=0, timeout=5)
        self.logs = []

    def make(self, responses):
        f = Fetcher(self.cfg, self.logs.append)
        calls = []

        class Resp:
            headers = {"Content-Type": "image/gif"}

            def __init__(self, blob):
                self.blob = blob

            def read(self, n):
                return self.blob

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_get(url, accept, extra_headers=None):
            calls.append(url)
            blob = responses.get(url, b"")
            # 模拟真实 _get：超过上限即视为失败
            if not blob or len(blob) > self.cfg.max_image_bytes:
                return None, ""
            return blob, "image/gif"
        f._get = fake_get
        return f, calls

    def test_404_then_mw600_succeeds(self):
        good = image_variants(URL1)[0]
        f, calls = self.make({good: GIF})
        blob, ext = f.image(URL1)
        self.assertEqual(ext, ".gif")
        self.assertEqual(blob, GIF)
        self.assertEqual(calls, [URL1, good])
        self.assertTrue(any("尺寸降级成功" in m for m in self.logs))

    def test_oversize_then_mw600_succeeds(self):
        big = b"GIF89a" + b"0" * (self.cfg.max_image_bytes + 10)
        good = image_variants(URL2)[0]
        f, calls = self.make({URL2: big, good: GIF})
        blob, ext = f.image(URL2)
        self.assertEqual(ext, ".gif")
        self.assertEqual(calls, [URL2, good])

    def test_all_fail_returns_none(self):
        f, calls = self.make({})
        self.assertEqual(f.image(URL1), (None, None))
        self.assertEqual(len(calls), 3)  # 原始 + 2 个降级


if __name__ == "__main__":
    unittest.main(verbosity=2)
