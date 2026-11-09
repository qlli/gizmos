"""可插拔的抓取适配层（结论 6、第四次修订的「站点专用适配器」）。

工程侧边界：遵守 robots.txt、可识别 UA、单线程限速、图片大小与类型校验。
不实现：模拟登录 / Cookie 会话维持 / 接口签名伪造 / 风控或验证码绕过 /
JS 渲染反检测 / UA 或代理轮换。站点专用适配器只解析公开 HTML 与公开接口
返回的图片地址；遇到登录墙如实报告并停止，不绕过。

sources.txt 每行一条来源，格式：  <分类>|<类型>|<值>
  分类：beauty / handsome
  类型：page   = 普通 HTML 页面，抽取页面中的 <img>
        image  = 单张图片直链
        dir    = 本地目录（用户自有图片，完全离线可用）
        jandan = 煎蛋栏目专用适配器（只走公开接口，过滤装饰图）
  例：
    beauty|page|https://example.com/some/gallery
    handsome|image|https://example.com/a.jpg
    beauty|dir|./my-images
    beauty|jandan|https://jandan.net/beauty
以 # 开头的行为注释。
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser

MAGIC = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"BM", ".bmp"),
)
WEBP_MAGIC = b"RIFF"


def sniff_ext(blob):
    """用文件头判断真实图片类型，避免把 HTML / JSON 错误页存成图片。"""
    for magic, ext in MAGIC:
        if blob.startswith(magic):
            return ext
    if blob.startswith(WEBP_MAGIC) and blob[8:12] == b"WEBP":
        return ".webp"
    return None


class RateLimiter:
    def __init__(self, interval):
        self.interval = max(0.0, float(interval))
        self._last = 0.0

    def wait(self):
        if self.interval <= 0:
            return
        gap = time.monotonic() - self._last
        if gap < self.interval:
            time.sleep(self.interval - gap)
        self._last = time.monotonic()


class RobotsCache:
    """按 origin 缓存 robots.txt；取不到时保守跳过。"""

    def __init__(self, cfg, limiter, opener):
        self.cfg = cfg
        self.limiter = limiter
        self.opener = opener
        self._cache = {}

    def allowed(self, url):
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ("http", "https"):
            return True
        origin = "%s://%s" % (parts.scheme, parts.netloc)
        if origin not in self._cache:
            self._cache[origin] = self._fetch(origin)
        parser = self._cache[origin]
        if parser is None:
            return False
        return parser.can_fetch(self.cfg.user_agent, url)

    def _fetch(self, origin):
        url = origin + "/robots.txt"
        self.limiter.wait()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.cfg.user_agent})
            with self.opener.open(req, timeout=self.cfg.timeout) as resp:
                raw = resp.read(256 * 1024).decode("utf-8", "replace")
            parser = urllib.robotparser.RobotFileParser()
            parser.parse(raw.splitlines())
            return parser
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                empty = urllib.robotparser.RobotFileParser()
                empty.parse([])
                return empty
            return None
        except Exception:
            return None


class _ImgParser(HTMLParser):
    ATTRS = ("src", "data-src", "data-original", "data-lazy-src", "data-url")

    def __init__(self):
        HTMLParser.__init__(self)
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag != "img":
            return
        d = dict(attrs)
        for key in self.ATTRS:
            val = d.get(key)
            if val:
                self.urls.append(val.strip())
        srcset = d.get("srcset") or d.get("data-srcset")
        if srcset:
            for part in srcset.split(","):
                candidate = part.strip().split(" ")[0]
                if candidate:
                    self.urls.append(candidate)


class Fetcher:
    """通用 HTTP 抓取器。所有请求共用限速器与 robots 缓存。"""

    def __init__(self, cfg, logger=None, credentials=None):
        self.cfg = cfg
        self.log = logger or (lambda msg: None)
        self.limiter = RateLimiter(cfg.request_interval)
        self.opener = urllib.request.build_opener()
        self.robots = RobotsCache(cfg, self.limiter, self.opener)
        self.credentials = credentials

    def _get(self, url, accept, extra_headers=None):
        if not self.robots.allowed(url):
            self.log("robots.txt 不允许，跳过：%s" % url)
            return None, None
        self.limiter.wait()
        headers = {
            "User-Agent": self.cfg.user_agent,
            "Accept": accept,
        }
        if extra_headers:
            headers.update(extra_headers)
        if self.credentials:
            headers.update(self.credentials.headers_for(url))
        try:
            req = urllib.request.Request(url, headers=headers)
            with self.opener.open(req, timeout=self.cfg.timeout) as resp:
                ctype = resp.headers.get("Content-Type", "")
                declared = resp.headers.get("Content-Length")
                limit = self.cfg.max_image_bytes
                if declared and declared.isdigit() and int(declared) > limit:
                    self.log("超过大小上限，跳过：%s" % url)
                    return None, None
                blob = resp.read(limit + 1)
                if len(blob) > limit:
                    return None, None
                return blob, ctype
        except Exception as e:
            self.log("请求失败 %s：%s" % (url, e))
            return None, None

    def get_text(self, url, referer=None):
        headers = {"Referer": referer} if referer else None
        blob, _ = self._get(url, "text/html,application/xhtml+xml", headers)
        return blob.decode("utf-8", "replace") if blob else None

    def get_json(self, url, referer=None):
        """公开 GET JSON；不携带 Cookie、不构造签名、不换 UA。"""
        headers = {}
        if referer:
            headers["Referer"] = referer
            headers["X-Requested-With"] = "XMLHttpRequest"
        blob, ctype = self._get(url, "application/json, text/plain, */*", headers)
        if blob is None:
            return None
        try:
            return json.loads(blob.decode("utf-8", "replace"))
        except ValueError:
            self.log("接口返回非 JSON：%s (ctype=%s)" % (url, ctype))
            return None

    def page_images(self, page_url):
        blob, ctype = self._get(page_url, "text/html,application/xhtml+xml")
        if blob is None:
            return []
        if "html" not in (ctype or "").lower() and not blob.lstrip().startswith(b"<"):
            return []
        parser = _ImgParser()
        try:
            parser.feed(blob.decode("utf-8", "replace"))
        except Exception:
            return []
        out, seen = [], set()
        for raw in parser.urls:
            if raw.startswith("data:"):
                continue
            absolute = urllib.parse.urljoin(page_url, raw)
            if absolute not in seen:
                seen.add(absolute)
                out.append(absolute)
        return out

    def image(self, image_url):
        accept = "image/avif,image/webp,image/*,*/*;q=0.5"
        blob, ctype = self._get(image_url, accept)
        if blob is not None:
            ext = sniff_ext(blob)
            if ext is not None:
                return blob, ext
        # 公开图床的尺寸段重试：mw1024 常失效，large 常超大小上限
        for variant in image_variants(image_url):
            blob, ctype = self._get(variant, accept)
            if blob is None:
                continue
            ext = sniff_ext(blob)
            if ext is not None:
                self.log("尺寸降级成功：%s" % variant[:110])
                return blob, ext
        if "image/" not in (ctype or "").lower() and blob is None:
            self.log("非图片响应，跳过：%s" % image_url[:110])
        return None, None


class Source:
    """子类实现 iter_images()，产出 (cat, blob, ext, src)。"""

    def __init__(self, cat):
        self.cat = cat

    def iter_images(self, fetcher, store, seen_src):
        raise NotImplementedError


class PageSource(Source):
    def __init__(self, cat, url):
        Source.__init__(self, cat)
        self.url = url

    def iter_images(self, fetcher, store, seen_src):
        for image_url in fetcher.page_images(self.url):
            if image_url in seen_src:
                continue
            seen_src.add(image_url)
            blob, ext = fetcher.image(image_url)
            if blob is None:
                continue
            yield self.cat, blob, ext, image_url


class ImageSource(Source):
    def __init__(self, cat, url):
        Source.__init__(self, cat)
        self.url = url

    def iter_images(self, fetcher, store, seen_src):
        if self.url in seen_src:
            return
        seen_src.add(self.url)
        blob, ext = fetcher.image(self.url)
        if blob is not None:
            yield self.cat, blob, ext, self.url


class DirSource(Source):
    """本地目录导入：读取用户自有图片，不产生任何网络请求。"""

    def __init__(self, cat, path):
        Source.__init__(self, cat)
        self.path = path

    def iter_images(self, fetcher, store, seen_src):
        if not os.path.isdir(self.path):
            return
        for name in sorted(os.listdir(self.path)):
            full = os.path.join(self.path, name)
            if not os.path.isfile(full) or full in seen_src:
                continue
            seen_src.add(full)
            try:
                with open(full, "rb") as f:
                    blob = f.read(store.cfg.max_image_bytes + 1)
            except OSError:
                continue
            if len(blob) > store.cfg.max_image_bytes:
                continue
            ext = sniff_ext(blob)
            if ext is None:
                continue
            yield self.cat, blob, ext, full


DECORATION_RE = re.compile(
    r"/static/tg/|/static/(?:img|images|avatar|logo|ad|ads|banner)/"
    r"|/wp-content/themes/|/wp-includes/|gravatar|/logo\.|/banner\."
    r"|/ads?\.|google|doubleclick|placeholder|loading\.gif|blank\.gif",
    re.I,
)
IMAGE_URL_RE = re.compile(
    r"(?:https?:)?//[^\s\"'<>\\]+?\.(?:jpe?g|png|gif|webp|bmp)(?:\?[^\s\"'<>\\]*)?",
    re.I,
)


SIZE_SEGMENT_RE = re.compile(r"/(?:m?w\d+|large|small|bmiddle|thumb\d+)(?=/)", re.I)
FALLBACK_SIZES = ("mw600", "thumb180")


def variant_key(url):
    """同一张图的不同尺寸段归一到同一个 key，避免重复下载。"""
    return SIZE_SEGMENT_RE.sub("/SIZE", url or "")


def image_variants(url):
    """下载失败或超限时，尝试同一公开图的其他尺寸。"""
    out = []
    for size in FALLBACK_SIZES:
        candidate = SIZE_SEGMENT_RE.sub("/" + size, url, count=1)
        if candidate != url and candidate not in out:
            out.append(candidate)
    return out


def is_decoration(url):
    """站点装饰 / 广告图，不是栏目正文内容图。"""
    return bool(DECORATION_RE.search(url or ""))


def _collect_image_urls(node, out):
    """递归从公开接口返回的数据里收集图片地址（含 HTML 片段中的 data-src）。"""
    if isinstance(node, dict):
        for value in node.values():
            _collect_image_urls(value, out)
    elif isinstance(node, list):
        for value in node:
            _collect_image_urls(value, out)
    elif isinstance(node, str):
        for match in IMAGE_URL_RE.finditer(node.replace("\\/", "/")):
            out.append(match.group(0))


class AuthRequired(Exception):
    """公开接口要求登录 / 凭证失效。用于触发显式告警，绝不静默跳过。"""

    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message


class JandanSource(Source):
    """煎蛋栏目专用适配器（守规矩版本）。

    只做三件事：从公开 HTML 读取栏目 PAGE.id、GET 该站的公开列表接口、
    从返回的图片地址里过滤装饰图后下载。
    不提交用户名密码、不自动登录、不换取 token、不伪造签名、
    不绕过风控或验证码、不做 JS 渲染反检测。
    凭证由用户自行放入本机文件，只按域附加请求头；接口若仍要求登录，
    按「凭证未配置」或「凭证已失效」分别告警并停止，不尝试绕过。
    """

    PAGE_ID_RE = re.compile(r"const\s+PAGE\s*=\s*\{\s*id\s*:\s*(\d+)")

    def __init__(self, cat, url, max_pages=1):
        Source.__init__(self, cat)
        self.url = url
        self.max_pages = max(1, int(max_pages))

    def iter_images(self, fetcher, store, seen_src):
        html = fetcher.get_text(self.url, referer=self.url)
        if not html:
            fetcher.log("页面读取失败，跳过：%s" % self.url)
            return
        match = self.PAGE_ID_RE.search(html)
        if not match:
            fetcher.log("未找到栏目 PAGE.id，跳过：%s" % self.url)
            return
        page_id = match.group(1)
        parts = urllib.parse.urlsplit(self.url)
        origin = "%s://%s" % (parts.scheme, parts.netloc)
        fetcher.log("栏目 %s：PAGE.id=%s" % (self.url, page_id))

        for page_no in range(1, self.max_pages + 1):
            api = ("%s/api/comment/post/%s?order=desc&page=%d&cdn_line=default"
                   % (origin, page_id, page_no))
            payload = fetcher.get_json(api, referer=self.url)
            if not isinstance(payload, dict):
                fetcher.log("接口无有效响应，停止：%s" % api)
                return
            if payload.get("code") != 0:
                msg = payload.get("msg", "")
                creds = getattr(fetcher, "credentials", None)
                state = creds.state if creds else "not_configured"
                fetcher.log("站点拒绝提供内容：%s（code=%s，凭证状态=%s）。"
                            "按边界不绕过，本来源停止。"
                            % (msg, payload.get("code"), state))
                if state == "loaded":
                    raise AuthRequired("凭证已加载但接口仍要求登录：%s（code=%s）"
                                       % (msg, payload.get("code")))
                return
            data = payload.get("data")
            if not data:
                fetcher.log("接口返回空数据，停止翻页")
                return
            candidates = []
            _collect_image_urls(data, candidates)
            content_urls = []
            page_variants = set()
            for raw in candidates:
                absolute = urllib.parse.urljoin(self.url, raw)
                if is_decoration(absolute) or absolute in seen_src:
                    continue
                seen_src.add(absolute)
                key = variant_key(absolute)
                if key in page_variants:
                    continue
                page_variants.add(key)
                content_urls.append(absolute)
            skipped = len(candidates) - len(content_urls)
            fetcher.log("第 %d 页：候选 %d 条，内容图 %d 条，装饰/重复/尺寸变体过滤 %d 条"
                        % (page_no, len(candidates), len(content_urls), skipped))
            for image_url in content_urls:
                blob, ext = fetcher.image(image_url)
                if blob is None:
                    continue
                yield self.cat, blob, ext, image_url


def load_sources(cfg, log=None):
    """解析 sources.txt；文件不存在时返回空列表（服务仍可正常浏览已有图片）。"""
    log = log or (lambda msg: None)
    if not os.path.isfile(cfg.sources_path):
        log("未找到 sources.txt，本轮不抓取新图")
        return []
    out = []
    with open(cfg.sources_path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|", 2)
            if len(parts) != 3:
                log("sources.txt 第 %d 行格式错误，已忽略" % lineno)
                continue
            cat, kind, value = (p.strip() for p in parts)
            if cat not in cfg.categories:
                log("sources.txt 第 %d 行分类无效：%s" % (lineno, cat))
                continue
            kind = kind.lower()
            if kind == "page":
                out.append(PageSource(cat, value))
            elif kind == "image":
                out.append(ImageSource(cat, value))
            elif kind == "dir":
                path = value if os.path.isabs(value) else os.path.join(cfg.root, value)
                out.append(DirSource(cat, os.path.abspath(path)))
            elif kind == "jandan":
                out.append(JandanSource(cat, value, cfg.jandan_max_pages))
            else:
                log("sources.txt 第 %d 行类型无效：%s" % (lineno, kind))
    return out
