"""登录态凭证（结论第五次修订）。

安全约束：
- 凭证由用户本人写入服务器本机 secrets/credentials.json，目录 700、文件 600。
- 不进仓库、不落日志、不出现在异常信息 / 索引 / API 响应 / 对话。
- 只按显式声明的域名注入请求头，绝不发往第三方图床或其他站点。
- 只记录「未配置 / 已加载 / 已失效」三种状态，不记录值。

文件格式（headers 内为原样附加的请求头）：
{
  "jandan.net": {
    "Cookie": "<你的 Cookie 串>",
    "User-Agent": "<可选，与浏览器保持一致>"
  }
}
"""
import json
import os
import re
import stat

MISSING = "not_configured"
LOADED = "loaded"
INVALID = "invalid"

PLACEHOLDER_RE = re.compile(r"<\s*[^>]*>|粘贴|在此处|你的\s*Cookie|YOUR_|CHANGEME", re.I)


def is_placeholder(value):
    """模板里未替换的示例值。"""
    return bool(PLACEHOLDER_RE.search(value or ""))


def _permissions_ok(path):
    """POSIX 下要求 600；Windows 无同等权限模型，由 NTFS ACL 负责。"""
    if os.name != "posix":
        return True
    mode = stat.S_IMODE(os.stat(path).st_mode)
    return not (mode & 0o077)


class Credentials:
    def __init__(self, path, log=None):
        self.path = path
        self.log = log or (lambda msg: None)
        self.state = MISSING
        self.is_template = False
        self._by_host = {}
        self._load()

    def _load(self):
        if not os.path.isfile(self.path):
            self.log("凭证未配置（%s 不存在）；来源将在登录墙处停止" % self.path)
            return
        try:
            if not _permissions_ok(self.path):
                self.log("凭证文件权限过宽，已忽略；请设为 600")
                self.state = INVALID
                return
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                raise ValueError("根对象必须是字典")
            for host, headers in raw.items():
                if host.startswith("_"):
                    continue  # 模板里的说明字段
                if not isinstance(host, str) or not host.strip():
                    raise ValueError("域名无效")
                if not isinstance(headers, dict) or not headers:
                    raise ValueError("请求头无效")
                clean = {}
                for key, value in headers.items():
                    if not isinstance(key, str) or not isinstance(value, str) or not value:
                        raise ValueError("请求头键值无效")
                    clean[key.strip()] = value.strip()
                self._by_host[host.strip().lower()] = clean
            placeholders = [v for h in self._by_host.values()
                            for v in h.values() if is_placeholder(v)]
            if placeholders:
                self.is_template = True
                self._by_host = {}
                self.state = MISSING
                self.log("凭证文件仍是模板（示例值未替换），请填入真实 Cookie；"
                         "本轮不注入任何请求头")
                return
            self.state = LOADED if self._by_host else MISSING
            self.log("凭证已加载：%d 个域名（内容不记录）" % len(self._by_host))
        except (ValueError, OSError, TypeError):
            self.state = INVALID
            self._by_host = {}
            self.log("凭证文件解析失败，已忽略；不记录内容")

    def headers_for(self, url):
        """按 URL 的 host 返回要附加的请求头；未命中返回空字典。"""
        from urllib.parse import urlsplit
        try:
            host = (urlsplit(url).hostname or "").lower()
        except ValueError:
            return {}
        for declared, headers in self._by_host.items():
            if host == declared or host.endswith("." + declared):
                return dict(headers)
        return {}

    def status(self):
        return {
            "state": self.state,
            "configured_hosts": sorted(self._by_host.keys()),
            "is_template": self.is_template,
        }
