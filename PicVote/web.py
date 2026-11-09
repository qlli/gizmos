"""HTTP 服务与单页前端（结论 5）。

默认公网匿名访问；配置 access_token 后所有页面与接口需带 ?token= 或
Authorization: Bearer，供用户一行收紧访问范围。
"""
import json
import mimetypes
import os
import re
import socketserver
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

SAFE_FILE = re.compile(r"^\d{8}\.(jpg|png|gif|webp|bmp)$")


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """兼容 Python 3.6（3.6 的 http.server 尚无 ThreadingHTTPServer）。"""
    daemon_threads = True
    allow_reuse_address = True

PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PicVote · 图片浏览</title>
<style>
  :root {
    --bg: #f5f6f8; --card: #ffffff; --ink: #1c2028; --muted: #7b8494;
    --line: #e7e9ee; --accent: #4f6bed; --good: #16a34a; --bad: #e05252;
    --shadow: 0 2px 10px rgba(28,32,40,.05), 0 12px 32px rgba(28,32,40,.05);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Microsoft YaHei", sans-serif; font-size: 15px; line-height: 1.5;
  }
  .wrap { max-width: 820px; margin: 0 auto; padding: 20px 16px 64px; }
  header { position: sticky; top: 0; z-index: 10; background: rgba(245,246,248,.92);
           backdrop-filter: blur(10px); padding: 14px 0 10px; margin-bottom: 18px;
           border-bottom: 1px solid var(--line); }
  .inner { max-width: 820px; margin: 0 auto; padding: 0 16px; }
  h1 { font-size: 19px; margin: 0; letter-spacing: .3px; }
  h1 small { font-weight: 400; color: var(--muted); font-size: 12px; margin-left: 8px; }
  .stats { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
  .chip { background: var(--card); border: 1px solid var(--line); border-radius: 999px;
          padding: 4px 12px; font-size: 12px; color: var(--muted); }
  .chip b { color: var(--ink); font-weight: 600; }
  .bar { height: 5px; border-radius: 99px; background: var(--line); margin-top: 10px; overflow: hidden; }
  .bar i { display: block; height: 100%; background: linear-gradient(90deg,#4f6bed,#8a76f5); }
  .tabs { display: flex; gap: 8px; margin-bottom: 16px; }
  .tab { flex: 1; padding: 10px; text-align: center; border: 1px solid var(--line);
         background: var(--card); border-radius: 10px; cursor: pointer; font-size: 14px;
         font-weight: 600; color: var(--muted); transition: .15s; }
  .tab:hover { border-color: #c9d0f0; }
  .tab.on { color: #fff; background: var(--accent); border-color: var(--accent);
            box-shadow: 0 4px 14px rgba(79,107,237,.25); }
  .list { display: flex; flex-direction: column; gap: 18px; }
  .photo { background: var(--card); border: 1px solid var(--line); border-radius: 14px;
           overflow: hidden; box-shadow: var(--shadow); }
  .photo img { display: block; width: 100%; height: auto; background: #eceef2; }
  .meta { display: flex; align-items: center; gap: 10px; padding: 12px 14px; flex-wrap: wrap; }
  .idx { font-variant-numeric: tabular-nums; color: var(--muted); font-size: 12px;
         min-width: 92px; }
  .when { color: var(--muted); font-size: 12px; flex: 1; }
  .btn { border: 1px solid var(--line); background: #fff; color: var(--muted);
         border-radius: 9px; padding: 7px 16px; font-size: 13px; font-weight: 700;
         cursor: pointer; letter-spacing: .5px; transition: .15s; min-width: 62px; }
  .btn:hover { transform: translateY(-1px); }
  .btn.oo.on { background: var(--good); border-color: var(--good); color: #fff; }
  .btn.xx.on { background: var(--bad); border-color: var(--bad); color: #fff; }
  .pager { display: flex; align-items: center; justify-content: center; gap: 8px;
           margin-top: 24px; flex-wrap: wrap; }
  .pager button { border: 1px solid var(--line); background: var(--card); color: var(--ink);
                  border-radius: 8px; padding: 7px 13px; cursor: pointer; font-size: 13px; }
  .pager button:disabled { opacity: .4; cursor: default; }
  .pager .cur { padding: 7px 12px; font-size: 13px; color: var(--muted); }
  .empty { text-align: center; padding: 72px 20px; color: var(--muted);
           background: var(--card); border: 1px dashed var(--line); border-radius: 14px; }
  .frozen { background: #fff8e6; border: 1px solid #f2dca0; color: #8a6414;
            border-radius: 10px; padding: 10px 14px; margin-bottom: 16px; font-size: 13px; }
  .alert { background: #fdecec; border: 1px solid #f0b4b4; color: #a12626;
           border-radius: 10px; padding: 10px 14px; margin-bottom: 16px; font-size: 13px; }
  @media (max-width: 520px) { .idx { min-width: 100%; } .when { flex: 1; } }
</style>
</head>
<body>
<header><div class="inner">
  <h1>PicVote <small>按抓取时间顺序浏览</small></h1>
  <div class="stats" id="stats"></div>
  <div class="bar"><i id="bar" style="width:0%"></i></div>
</div></header>
<div class="wrap">
  <div id="frozen" class="frozen" hidden></div>
  <div id="alert" class="alert" hidden></div>
  <div class="tabs">
    <div class="tab on" data-cat="beauty">美女</div>
    <div class="tab" data-cat="handsome">帅哥</div>
  </div>
  <div class="list" id="list"></div>
  <div class="pager" id="pager"></div>
</div>
<script>
const TOKEN = __TOKEN_JS__;
const LABELS = __LABELS__;
let cat = "beauty", page = 1;

function qs(extra) {
  const p = new URLSearchParams(extra || {});
  if (TOKEN) p.set("token", TOKEN);
  return p.toString() ? "?" + p.toString() : "";
}
async function api(path, opts) {
  const r = await fetch(path + qs(), opts || {});
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
}
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, c =>
    ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
async function loadStatus() {
  try {
    const s = await api("/api/status");
    document.getElementById("stats").innerHTML = [
      ["已用", s.used + " / " + s.quota], ["图片", s.total + " 张"],
      [LABELS.beauty, s.counts.beauty + " 张"], [LABELS.handsome, s.counts.handsome + " 张"],
      ["状态", s.frozen ? "已冻结" : "运行中"]
    ].map(p => '<span class="chip">' + esc(p[0]) + ' <b>' + esc(p[1]) + '</b></span>').join("");
    document.getElementById("bar").style.width = Math.min(100, s.percent) + "%";
    const f = document.getElementById("frozen");
    if (s.frozen) {
      f.hidden = false;
      f.textContent = "已进入终态：当前图片全部为点赞且配额已满，不再抓取、清理、汰换。";
    } else { f.hidden = true; }

    const a = document.getElementById("alert");
    const cred = s.credentials || {};
    if (s.auth_error || cred.state === "expired") {
      a.hidden = false;
      a.textContent = "抓取凭证已失效，需重新提供（" + esc(s.auth_error_at || "") +
        "）。原因：" + esc(s.auth_error || "接口要求登录") +
        "。凌晨任务已停止，不会静默空跑。";
    } else if (cred.is_template) {
      a.hidden = false;
      a.textContent = "凭证文件仍是模板（示例值未替换）：请在服务器填入真实 Cookie 后再抓取。";
    } else if (cred.state === "not_configured") {
      a.hidden = false;
      a.textContent = "未配置抓取凭证：需要登录的栏目会在登录墙处停止，暂时抓不到内容图。";
    } else if (cred.state === "invalid") {
      a.hidden = false;
      a.textContent = "抓取凭证文件无效或权限过宽（需 600），已忽略，请检查服务器配置。";
    } else { a.hidden = true; }
  } catch (e) { console.warn(e); }
}
async function load() {
  const box = document.getElementById("list");
  box.innerHTML = '<div class="empty">加载中…</div>';
  try {
    const q = new URLSearchParams({cat: cat, page: page});
    if (TOKEN) q.set("token", TOKEN);
    const r = await fetch("/api/images?" + q.toString());
    if (!r.ok) throw new Error("HTTP " + r.status);
    const data = await r.json();
    if (!data.items.length) {
      box.innerHTML = '<div class="empty">该分类还没有图片。<br>把来源写入 sources.txt 后，' +
                      '执行 <code>python app.py --job-now</code> 即可抓取。</div>';
    } else {
      box.innerHTML = data.items.map(it =>
        '<div class="photo">' +
          '<img src="' + esc(it.url) + '" alt="图片 ' + it.id + '" loading="lazy">' +
          '<div class="meta">' +
            '<span class="idx">#' + it.id + ' · ' + esc(humanSize(it.size)) + '</span>' +
            '<span class="when">' + esc(it.at) + '</span>' +
            '<button class="btn oo ' + (it.vote === "oo" ? "on" : "") +
              '" onclick="vote(' + it.id + ',\'oo\',this)">oo</button>' +
            '<button class="btn xx ' + (it.vote === "xx" ? "on" : "") +
              '" onclick="vote(' + it.id + ',\'xx\',this)">xx</button>' +
          '</div>' +
        '</div>').join("");
    }
    const pg = document.getElementById("pager");
    pg.innerHTML =
      '<button ' + (data.page <= 1 ? "disabled" : "") + ' onclick="go(' + (data.page-1) + ')">上一页</button>' +
      '<span class="cur">第 ' + data.page + ' / ' + data.pages + ' 页 · 共 ' + data.total + ' 张</span>' +
      '<button ' + (data.page >= data.pages ? "disabled" : "") + ' onclick="go(' + (data.page+1) + ')">下一页</button>';
  } catch (e) {
    box.innerHTML = '<div class="empty">加载失败：' + esc(e.message) + '</div>';
  }
}
function humanSize(n) {
  if (n < 1024) return n + " B";
  if (n < 1048576) return (n/1024).toFixed(1) + " KiB";
  return (n/1048576).toFixed(1) + " MiB";
}
async function vote(id, v, btn) {
  const card = btn.closest(".meta");
  try {
    const r = await fetch("/api/vote" + qs(), {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({id: id, vote: v})
    });
    const d = await r.json();
    card.querySelectorAll(".btn").forEach(b => b.classList.remove("on"));
    if (d.vote === "oo") card.querySelector(".btn.oo").classList.add("on");
    if (d.vote === "xx") card.querySelector(".btn.xx").classList.add("on");
  } catch (e) { console.warn(e); }
}
function go(p) { page = p; load(); window.scrollTo({top: 0, behavior: "smooth"}); }
document.querySelectorAll(".tab").forEach(t => t.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.remove("on"));
  t.classList.add("on"); cat = t.dataset.cat; page = 1; load();
}));
loadStatus(); load();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    store = None
    cfg = None
    log = staticmethod(lambda msg: print(msg))

    def log_message(self, fmt, *args):
        pass

    def _token_ok(self):
        token = self.cfg.access_token
        if not token:
            return True
        parsed = urllib.parse.urlsplit(self.path)
        q = urllib.parse.parse_qs(parsed.query)
        if token in q.get("token", []):
            return True
        if self.headers.get("Authorization") == "Bearer " + token:
            return True
        return False

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def do_GET(self):
        self.store.refresh_if_changed()
        if not self._token_ok():
            return self._json({"error": "unauthorized"}, 401)
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        q = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            labels = json.dumps(self.cfg.category_labels, ensure_ascii=False)
            token_js = json.dumps(self.cfg.access_token, ensure_ascii=False)
            html = PAGE.replace("__TOKEN_JS__", token_js).replace("__LABELS__", labels)
            return self._send(200, html, "text/html; charset=utf-8")

        if path == "/api/status":
            return self._json(self.store.status())

        if path == "/api/images":
            cat = q.get("cat", ["beauty"])[0]
            if cat not in self.cfg.categories:
                return self._json({"error": "invalid category"}, 400)
            try:
                page_no = int(q.get("page", ["1"])[0])
            except ValueError:
                page_no = 1
            return self._json(self.store.page(cat, page_no))

        if path.startswith("/img/"):
            name = os.path.basename(path[len("/img/"):])
            if not SAFE_FILE.match(name):
                return self._json({"error": "invalid filename"}, 400)
            full = os.path.join(self.cfg.images_dir, name)
            if not os.path.isfile(full):
                return self._json({"error": "not found"}, 404)
            ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
            with open(full, "rb") as f:
                blob = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(blob)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            try:
                self.wfile.write(blob)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        self.store.refresh_if_changed()
        if not self._token_ok():
            return self._json({"error": "unauthorized"}, 401)
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path != "/api/vote":
            return self._json({"error": "not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            item_id = int(payload["id"])
            value = payload.get("vote")
        except (ValueError, KeyError, TypeError, UnicodeDecodeError):
            return self._json({"error": "invalid payload"}, 400)
        if value not in ("oo", "xx"):
            return self._json({"error": "invalid vote"}, 400)
        vote = self.store.vote(item_id, value)
        if vote is None and not any(int(i["id"]) == item_id for i in self.store.items):
            return self._json({"error": "image not found"}, 404)
        return self._json({"id": item_id, "vote": vote})


def make_handler(store, cfg, log=None):
    return type("BoundHandler", (Handler,), {
        "store": store,
        "cfg": cfg,
        "log": staticmethod(log or (lambda msg: print(msg))),
    })


def serve_forever(store, cfg, log=None):
    handler = make_handler(store, cfg, log)
    server = ThreadingHTTPServer((cfg.host, cfg.port), handler)
    server.daemon_threads = True
    log = log or (lambda msg: print(msg))
    log("HTTP 服务已启动： http://%s:%d/" % (cfg.host, cfg.port))
    if cfg.host == "0.0.0.0":
        log("当前为公网匿名访问；如需收紧，设置 PICVOTE_HOST=127.0.0.1 "
            "或 PICVOTE_ACCESS_TOKEN=<自定口令>")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
