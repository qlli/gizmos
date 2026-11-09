"""凭证与失效告警自检（结论第五次修订）。"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402
from credentials import Credentials, LOADED, MISSING, INVALID  # noqa: E402
from job import run_job  # noqa: E402
from sources import (AuthRequired, Fetcher, JandanSource,  # noqa: E402
                     load_sources)
from storage import Store  # noqa: E402

SECRET = "SUPER_SECRET_COOKIE_VALUE_12345"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
PAGE_HTML = '<html><script>const PAGE = { id: 108629 };</script></html>'


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="picvote-cred-")
        self.cfg = Config(root=self.tmp)
        self.store = Store(self.cfg)
        self.logs = []
        os.makedirs(self.cfg.secrets_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def log(self, msg):
        self.logs.append(msg)

    def write_credentials(self, mode=0o600, payload=None):
        path = self.cfg.credentials_path
        data = payload if payload is not None else {
            "jandan.net": {"Cookie": SECRET}
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.chmod(path, mode)
        return path


class TestCredentials(Base):
    def test_missing(self):
        c = Credentials(self.cfg.credentials_path, self.log)
        self.assertEqual(c.state, MISSING)
        self.assertEqual(c.headers_for("https://jandan.net/beauty"), {})

    def test_loaded_and_scoped_by_host(self):
        self.write_credentials()
        c = Credentials(self.cfg.credentials_path, self.log)
        self.assertEqual(c.state, LOADED)
        own = c.headers_for("https://jandan.net/beauty")
        self.assertEqual(own.get("Cookie"), SECRET)
        self.assertEqual(c.headers_for("https://www.jandan.net/beauty").get("Cookie"), SECRET)
        self.assertEqual(c.headers_for("https://img.example.com/a.jpg"), {})
        self.assertEqual(c.headers_for("https://evil-jandan.net/x"), {})
        self.assertEqual(c.status(), {"state": LOADED,
                                      "configured_hosts": ["jandan.net"],
                                      "is_template": False})

    def test_wide_permissions_ignored(self):
        import credentials as credmod
        self.write_credentials()
        original = credmod._permissions_ok
        credmod._permissions_ok = lambda path: False
        try:
            c = Credentials(self.cfg.credentials_path, self.log)
        finally:
            credmod._permissions_ok = original
        self.assertEqual(c.state, INVALID)
        self.assertEqual(c.headers_for("https://jandan.net/beauty"), {})

    def test_template_placeholder_is_not_loaded(self):
        self.write_credentials(payload={
            "_说明": "这是模板说明",
            "jandan.net": {"Cookie": "<把浏览器里该站的 Cookie 串粘贴到此处>"},
        })
        c = Credentials(self.cfg.credentials_path, self.log)
        self.assertEqual(c.state, MISSING)
        self.assertTrue(c.is_template)
        self.assertEqual(c.headers_for("https://jandan.net/beauty"), {})
        self.assertEqual(c.status()["configured_hosts"], [])
        self.assertTrue(any("仍是模板" in m for m in self.logs))

    def test_real_looking_value_is_loaded(self):
        self.write_credentials(payload={"jandan.net": {"Cookie": "sid=abc123; uid=42"}})
        c = Credentials(self.cfg.credentials_path, self.log)
        self.assertEqual(c.state, LOADED)
        self.assertFalse(c.is_template)

    def test_bad_json_ignored(self):
        with open(self.cfg.credentials_path, "w", encoding="utf-8") as f:
            f.write("{not json")
        os.chmod(self.cfg.credentials_path, 0o600)
        c = Credentials(self.cfg.credentials_path, self.log)
        self.assertEqual(c.state, INVALID)

    def test_secret_never_in_logs_or_status(self):
        self.write_credentials()
        c = Credentials(self.cfg.credentials_path, self.log)
        text = " ".join(self.logs) + json.dumps(c.status())
        self.assertNotIn(SECRET, text)

    def test_fetcher_injects_only_for_own_host(self):
        self.write_credentials()
        c = Credentials(self.cfg.credentials_path, self.log)
        f = Fetcher(self.cfg, self.log, credentials=c)
        captured = []

        class FakeResp:
            headers = {}

            def read(self, n):
                return b"{}"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        f.opener = type("Opener", (), {
            "open": lambda self, req, timeout=None: (
                captured.append(dict(req.header_items())) or FakeResp())
        })()
        f.robots = type("Robots", (), {"allowed": lambda self, u: True})()
        f.get_json("https://jandan.net/api/x", referer="https://jandan.net/beauty")
        f.image("https://img.example.com/a.jpg")
        self.assertTrue(captured)
        own_lower = {k.lower(): v for k, v in captured[0].items()}
        self.assertEqual(own_lower.get("cookie"), SECRET)
        cdn_lower = {k.lower(): v for k, v in captured[1].items()}
        self.assertNotIn("cookie", cdn_lower)


class FakeFetcher:
    """模拟公开接口，避免任何网络请求。"""

    def __init__(self, cfg, payloads, credentials=None):
        self.cfg = cfg
        self.log = lambda m: None
        self.credentials = credentials
        self.payloads = list(payloads)

    def log(self, msg):
        pass

    def get_text(self, url, referer=None):
        return PAGE_HTML

    def get_json(self, url, referer=None):
        return self.payloads.pop(0) if self.payloads else None

    def image(self, url):
        return PNG, ".png"


class TestAuthAlert(Base):
    def _job_with(self, payloads, credentials):
        import job as jobmod
        with open(self.cfg.sources_path, "w", encoding="utf-8") as f:
            f.write("beauty|jandan|https://jandan.net/beauty\n")
        original_fetcher = jobmod.Fetcher
        original_creds = jobmod.Credentials
        jobmod.Fetcher = lambda cfg, log, credentials=None: FakeFetcher(
            cfg, payloads, credentials)
        jobmod.Credentials = lambda path, log: credentials
        try:
            return run_job(self.store, self.cfg, self.log, force=True)
        finally:
            jobmod.Fetcher = original_fetcher
            jobmod.Credentials = original_creds

    def test_loaded_but_rejected_marks_expired(self):
        cred = type("C", (), {
            "state": LOADED,
            "status": lambda self: {"state": LOADED,
                                    "configured_hosts": ["jandan.net"]},
        })()
        payload = {"code": 1000, "msg": "较老的数据仅对登陆用户开放访问", "data": None}
        result = self._job_with([payload], cred)
        self.assertIsNotNone(result.detail.get("auth_error"))
        self.assertEqual(self.store.status()["credentials"]["state"], "expired")
        self.assertTrue(self.store.status()["auth_error"])
        self.assertTrue(any("告警" in m for m in self.logs))

    def test_not_configured_stops_cleanly(self):
        cred = type("C", (), {
            "state": MISSING,
            "status": lambda self: {"state": MISSING, "configured_hosts": []},
        })()
        payload = {"code": 1000, "msg": "较老的数据仅对登陆用户开放访问", "data": None}
        result = self._job_with([payload], cred)
        self.assertIsNone(result.detail.get("auth_error"))
        self.assertEqual(self.store.status()["credentials"]["state"], MISSING)

    def test_success_clears_previous_alert(self):
        self.store.data["auth_error"] = "old"
        self.store.data["auth_error_at"] = "yesterday"
        self.store.save()
        cred = type("C", (), {
            "state": LOADED,
            "status": lambda self: {"state": LOADED,
                                    "configured_hosts": ["jandan.net"]},
        })()
        payload = {"code": 0, "data": {"comments": [
            {"content": '<img src="https://img.example.com/pic/a.jpg">'}
        ]}}
        self._job_with([payload], cred)
        s = self.store.status()
        self.assertEqual(s["auth_error"], "")
        self.assertEqual(s["total"], 1)

    def test_secret_never_in_job_logs_or_index(self):
        cred = type("C", (), {
            "state": LOADED,
            "status": lambda self: {"state": LOADED,
                                    "configured_hosts": ["jandan.net"]},
        })()
        payload = {"code": 1000, "msg": "较老的数据仅对登陆用户开放访问", "data": None}
        self._job_with([payload], cred)
        blob = " ".join(self.logs) + json.dumps(self.store.data, ensure_ascii=False)
        self.assertNotIn(SECRET, blob)
        self.assertNotIn("cookie", blob.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
