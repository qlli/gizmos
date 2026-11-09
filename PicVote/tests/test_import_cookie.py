"""Cookie 导入工具的格式识别自检（不接触真实凭证）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from import_cookie import extract  # noqa: E402


class TestExtract(unittest.TestCase):
    def test_plain_cookie_string(self):
        self.assertEqual(extract("sid=abc; uid=42"), "sid=abc; uid=42")

    def test_request_headers_line(self):
        self.assertEqual(extract("accept: */*\ncookie: sid=abc; uid=42\norigin: x"),
                         "sid=abc; uid=42")

    def test_curl_header_form(self):
        cmd = ("curl 'https://jandan.net/api/x' -H 'Accept: */*' "
               "-H 'Cookie: sid=abc; uid=42' -H 'Referer: https://jandan.net/'")
        self.assertEqual(extract(cmd), "sid=abc; uid=42")

    def test_curl_b_form(self):
        self.assertEqual(extract("curl 'https://jandan.net/x' -b 'sid=abc; uid=42'"),
                         "sid=abc; uid=42")

    def test_cookie_editor_json(self):
        raw = '[{"name":"sid","value":"abc"},{"name":"uid","value":"42"}]'
        self.assertEqual(extract(raw), "sid=abc; uid=42")

    def test_cookie_editor_wrapped_json(self):
        raw = '{"cookies":[{"name":"sid","value":"abc"}]}'
        self.assertEqual(extract(raw), "sid=abc")

    def test_rejects_unrecognised(self):
        self.assertIsNone(extract(""))
        self.assertIsNone(extract("curl 'https://jandan.net/x' -H 'Accept: */*'"))
        self.assertIsNone(extract("hello world"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
