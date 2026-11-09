"""站点专用适配器自检：装饰图过滤、登录墙停止、内容图提取。"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402
from sources import (JandanSource, is_decoration, load_sources,  # noqa: E402
                     _collect_image_urls)
from storage import Store  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
PAGE_HTML = '<html><script>const PAGE = { id: 108629 };</script></html>'


class FakeFetcher:
    """不产生任何网络请求，模拟公开接口响应。"""

    def __init__(self, html=PAGE_HTML, payloads=None, images=None):
        self.html = html
        self.payloads = list(payloads or [])
        self.images = images or {}
        self.logs = []
        self.calls = []

    def log(self, msg):
        self.logs.append(msg)

    def get_text(self, url, referer=None):
        self.calls.append(("text", url))
        return self.html

    def get_json(self, url, referer=None):
        self.calls.append(("json", url))
        return self.payloads.pop(0) if self.payloads else None

    def image(self, url):
        self.calls.append(("image", url))
        blob = self.images.get(url, PNG)
        return blob, ".png"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="picvote-jandan-")
        self.cfg = Config(root=self.tmp)
        self.store = Store(self.cfg)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def collect(self, fetcher, source=None):
        source = source or JandanSource("beauty", "https://jandan.net/beauty")
        return list(source.iter_images(fetcher, self.store, set()))


class TestDecorationFilter(Base):
    def test_decoration_patterns(self):
        for url in [
            "https://jandan.net/static/tg/wangmoyu_02.png",
            "https://jandan.net/static/tg/vip-side-2.jpg",
            "https://jandan.net/static/tg/reader-side-1.jpg",
            "https://jandan.net/static/images/logo.png",
            "https://cdn.jandan.net/wp-content/themes/x/a.jpg",
        ]:
            self.assertTrue(is_decoration(url), url)
        self.assertFalse(is_decoration("https://img.example.com/pic/a.jpg"))

    def test_collect_and_filter(self):
        data = {
            "comments": [
                {"content": '<img data-src="https://img.example.com/pic/a.jpg">'},
                {"content": '<img src="https://jandan.net/static/tg/ad.png">'},
            ]
        }
        urls = []
        _collect_image_urls(data, urls)
        normalized = ["https:" + u if u.startswith("//") else u for u in urls]
        self.assertEqual(len(normalized), 2)
        self.assertTrue(any(is_decoration(u) for u in normalized))
        self.assertTrue(any(not is_decoration(u) for u in normalized))

    def test_decoration_never_yielded(self):
        payload = {"code": 0, "msg": "success", "data": {"comments": [
            {"content": '<img data-src="https://jandan.net/static/tg/ad.png">'}
        ]}}
        f = FakeFetcher(payloads=[payload])
        got = self.collect(f)
        self.assertEqual(len(got), 0)
        self.assertFalse(any(c[0] == "image" for c in f.calls))
        self.assertTrue(any("尺寸变体过滤" in m for m in f.logs))


class TestLoginWall(Base):
    def test_login_wall_stops_without_bypass(self):
        payload = {"code": 1000, "msg": "较老的数据仅对登陆用户开放访问", "data": None}
        f = FakeFetcher(payloads=[payload])
        got = self.collect(f)
        self.assertEqual(len(got), 0)
        self.assertFalse(any(c[0] == "image" for c in f.calls))
        self.assertTrue(any("按边界不绕过" in m for m in f.logs))

    def test_empty_data_stops(self):
        f = FakeFetcher(payloads=[{"code": 0, "msg": "success", "data": None}])
        self.assertEqual(len(self.collect(f)), 0)

    def test_missing_page_id_stops(self):
        f = FakeFetcher(html="<html>no page id here</html>")
        self.assertEqual(len(self.collect(f)), 0)
        self.assertTrue(any("PAGE.id" in m for m in f.logs))

    def test_public_api_called_without_cookie(self):
        payload = {"code": 0, "data": {"comments": []}}
        f = FakeFetcher(payloads=[payload])
        self.collect(f)
        json_calls = [u for kind, u in f.calls if kind == "json"]
        self.assertEqual(len(json_calls), 1)
        self.assertIn("/api/comment/post/108629?", json_calls[0])
        self.assertIn("cdn_line=default", json_calls[0])


class TestContentImages(Base):
    def test_content_images_are_yielded(self):
        payload = {"code": 0, "data": {"comments": [
            {"content": '<img data-src="https://img.example.com/pic/a.jpg">'},
            {"content": '<img data-src="https://img.example.com/pic/b.png">'},
            {"content": '<img src="https://jandan.net/static/tg/ad.jpg">'},
        ]}}
        f = FakeFetcher(payloads=[payload])
        got = self.collect(f)
        self.assertEqual(len(got), 2)
        self.assertTrue(all(g[0] == "beauty" for g in got))
        self.assertEqual(len([c for c in f.calls if c[0] == "image"]), 2)

    def test_screenshot_style_webp_url_is_not_filtered(self):
        """用户 DevTools 截图里的 img-max / data-src / img.toto.im 形态。"""
        payload = {"code": 0, "data": {"comments": [
            {"content": '<img class="img-max" '
                        'data-src="https://img.toto.im/w600/00814KFg.webp" '
                        'src="https://img.toto.im/mw600/00814KFg.webp" lazy="loaded">'}
        ]}}
        f = FakeFetcher(payloads=[payload])
        got = self.collect(f)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][0], "beauty")
        self.assertIn("img.toto.im", got[0][3])
        self.assertTrue(any("img.toto.im" in c[1] for c in f.calls if c[0] == "image"))

    def test_multi_page_config(self):
        payloads = [
            {"code": 0, "data": {"comments": [
                {"content": '<img src="https://img.example.com/p%d.jpg">' % i}]}}
            for i in (1, 2)
        ]
        payloads.append({"code": 0, "data": None})
        f = FakeFetcher(payloads=payloads)
        f = FakeFetcher(payloads=payloads)
        source = JandanSource("beauty", "https://jandan.net/beauty", 3)
        got = list(source.iter_images(f, self.store, set()))
        self.assertEqual(len(got), 2)
        self.assertEqual(len([c for c in f.calls if c[0] == "json"]), 3)


class TestSourceParsing(Base):
    def test_jandan_type_registered(self):
        path = os.path.join(self.tmp, "sources.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# comment\nbeauty|jandan|https://jandan.net/beauty\n")
        out = load_sources(self.cfg, log=lambda m: None)
        self.assertEqual(len(out), 1)
        self.assertIsInstance(out[0], JandanSource)
        self.assertEqual(out[0].cat, "beauty")


if __name__ == "__main__":
    unittest.main(verbosity=2)
