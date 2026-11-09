"""HTTP 接口自检：首页、状态、分页、图片、改票、口令、非法路径。"""
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402
from storage import Store  # noqa: E402
from web import ThreadingHTTPServer, make_handler  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def req(base, path, payload=None):
    url = base + path
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


class WebTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="picvote-web-")
        self.cfg = Config(root=self.tmp, quota_bytes=10 ** 9, page_size=20)
        self.store = Store(self.cfg)
        for i in range(25):
            cat = "beauty" if i < 20 else "handsome"
            self.store.add(PNG, cat, "test-src", ".png")
        self.store.save()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.store, self.cfg))
        self.server.daemon_threads = True
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]
        self.t = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.t.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_home_and_labels(self):
        code, body = req(self.base, "/")
        self.assertEqual(code, 200)
        html = body.decode("utf-8")
        self.assertIn("美女", html)
        self.assertIn("帅哥", html)
        self.assertNotIn("__TOKEN_JS__", html)
        self.assertNotIn("__LABELS__", html)

    def test_status(self):
        code, body = req(self.base, "/api/status")
        s = json.loads(body)
        self.assertEqual(s["total"], 25)
        self.assertEqual(s["counts"]["beauty"], 20)
        self.assertEqual(s["counts"]["handsome"], 5)
        self.assertEqual(s["used_bytes"], 25 * len(PNG))
        self.assertFalse(s["frozen"])

    def test_page_and_time_order(self):
        code, body = req(self.base, "/api/images?cat=beauty&page=1")
        d = json.loads(body)
        self.assertEqual(len(d["items"]), 20)
        self.assertEqual([i["id"] for i in d["items"]], list(range(1, 21)))
        self.assertEqual(d["pages"], 1)
        code, body = req(self.base, "/api/images?cat=handsome&page=1")
        self.assertEqual(len(json.loads(body)["items"]), 5)
        code, _ = req(self.base, "/api/images?cat=bad&page=1")
        self.assertEqual(code, 400)

    def test_image_bytes(self):
        code, body = req(self.base, "/img/00000001.png")
        self.assertEqual(code, 200)
        self.assertEqual(body, PNG)
        code, _ = req(self.base, "/img/../../config.py")
        self.assertEqual(code, 400)

    def test_vote_change_and_cancel(self):
        code, body = req(self.base, "/api/vote", {"id": 1, "vote": "oo"})
        self.assertEqual(json.loads(body)["vote"], "oo")
        code, body = req(self.base, "/api/vote", {"id": 1, "vote": "xx"})
        self.assertEqual(json.loads(body)["vote"], "xx")
        code, body = req(self.base, "/api/vote", {"id": 1, "vote": "xx"})
        self.assertIsNone(json.loads(body)["vote"])
        self.assertEqual(len(self.store.items), 25)
        code, _ = req(self.base, "/api/vote", {"id": 999, "vote": "oo"})
        self.assertEqual(code, 404)

    def test_optional_token(self):
        self.cfg.access_token = "s3cret"
        code, _ = req(self.base, "/api/status")
        self.assertEqual(code, 401)
        code, _ = req(self.base, "/api/status?token=s3cret")
        self.assertEqual(code, 200)
        self.cfg.access_token = ""


if __name__ == "__main__":
    unittest.main(verbosity=2)
