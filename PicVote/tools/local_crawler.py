"""本地守规矩图片抓取器：把公开静态页面里的图片保存到本机目录。

不接入服务器、不写 PicVote 索引，产出只落在本机，供后续本地模型判别。

用法：
  python tools/local_crawler.py --url <页面URL> --out <目录> --dry-run
  python tools/local_crawler.py --url <页面URL> --out <目录> --max 20
  python tools/local_crawler.py --url <页面URL> --out <目录> --cookie-file <文件>

边界：遵守 robots.txt（取不到则保守拒绝）、限速、可识别 UA、
只解析服务端返回的静态 HTML、图片头校验 + 大小上限、URL 与内容双重去重、
凭证只按域附加且不打印不落日志。
不实现：模拟登录、接口签名伪造、风控 / 验证码绕过、JS 渲染反检测。
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sources import _ImgParser, is_decoration, sniff_ext  # noqa: E402

UA = "PicVoteLocal/1.0 (personal image downloader)"
MAX_BYTES = 8 * 1024 * 1024


def robots_allowed(url):
    parts = urllib.parse.urlsplit(url)
    rb_url = "%s://%s/robots.txt" % (parts.scheme, parts.netloc)
    try:
        req = urllib.request.Request(rb_url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=8) as r:
            text = r.read().decode("utf-8", "replace")
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(text.splitlines())
        return rp.can_fetch(UA, url)
    except Exception:
        return False  # 拿不到 robots.txt 时保守拒绝


def get(url, headers, timeout=10, limit=MAX_BYTES):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit + 1), r.headers.get("Content-Type", "")


def page_image_urls(url, headers):
    blob, ctype = get(url, headers, limit=4 * MAX_BYTES)
    if "html" not in ctype.lower() and not blob.lstrip().startswith(b"<"):
        return []
    parser = _ImgParser()
    parser.feed(blob.decode("utf-8", "replace"))
    seen, out = set(), []
    for raw in parser.urls:
        absolute = urllib.parse.urljoin(url, raw.strip())
        if absolute in seen or is_decoration(absolute):
            continue
        seen.add(absolute)
        out.append(absolute)
    return out


def same_host(a, b):
    return urllib.parse.urlsplit(a).netloc == urllib.parse.urlsplit(b).netloc


def main():
    ap = argparse.ArgumentParser(description="本地守规矩图片抓取器")
    ap.add_argument("--url", required=True, help="待抓取的公开页面 URL")
    ap.add_argument("--out", required=True, help="本机保存目录")
    ap.add_argument("--max", type=int, default=20, help="最多保存几张，默认 20")
    ap.add_argument("--interval", type=float, default=1.0, help="请求间隔秒，默认 1.0")
    ap.add_argument("--dry-run", action="store_true", help="只解析、不下载")
    ap.add_argument("--cookie-file", help="本人 Cookie 纯文本文件，仅按域附加")
    args = ap.parse_args()

    if not robots_allowed(args.url):
        print("robots.txt 不允许或未取到，按边界停止：%s" % args.url)
        print("该站点在守规矩路径下抓不到内容图；这不是脚本故障。")
        return 2

    headers = {"User-Agent": UA, "Accept": "text/html,image/*,*/*"}
    cookie = ""
    if args.cookie_file:
        with open(args.cookie_file, "r", encoding="utf-8") as f:
            cookie = f.read().strip()
        print("已加载本人凭证（长度 %d，内容不打印），仅发往页面同域" % len(cookie))

    def headers_for(u):
        h = dict(headers)
        if cookie and same_host(u, args.url):
            h["Cookie"] = cookie
        return h

    try:
        urls = page_image_urls(args.url, headers_for(args.url))
    except Exception as e:
        print("页面读取失败：%s" % str(e)[:120])
        return 1
    print("robots=allowed 候选内容图=%d" % len(urls))
    for u in urls[:3]:
        print("   ", u[:110])
    if args.dry_run:
        print("dry-run：未下载任何图片")
        return 0

    os.makedirs(args.out, exist_ok=True)
    saved, hashes = 0, set()
    for u in urls:
        if saved >= args.max:
            break
        time.sleep(args.interval)
        try:
            blob, _ = get(u, headers_for(u))
        except Exception as e:
            print("  跳过 %s：%s" % (u[:70], str(e)[:50]))
            continue
        if len(blob) > MAX_BYTES:
            print("  跳过（超过大小上限）：%s" % u[:70])
            continue
        ext = sniff_ext(blob)
        if ext is None:
            continue
        digest = hashlib.sha1(blob).hexdigest()
        if digest in hashes:
            continue
        hashes.add(digest)
        saved += 1
        path = os.path.join(args.out, "%04d%s" % (saved, ext))
        with open(path, "wb") as f:
            f.write(blob)
        print("  已保存 %s (%d 字节)" % (path, len(blob)))
    print("完成：保存 %d 张到 %s" % (saved, args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
