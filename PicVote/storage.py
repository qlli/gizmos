"""图片与索引存储：不使用数据库，单个 index.json + 原始图片文件。

索引结构（结论 2.1）：
{
  "next_id": 123,
  "items": [
    {"id": 1, "file": "00000001.jpg", "cat": "beauty",
     "size": 12345, "at": "2026-11-08T03:00:01", "vote": null, "src": "..."}
  ],
  "frozen": false,
  "last_job_date": "2026-11-08"
}
"""
import json
import os
import tempfile
from datetime import datetime

import config as cfgmod

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


def _empty_index():
    return {"next_id": 1, "items": [], "frozen": False, "last_job_date": ""}


class Store:
    def __init__(self, cfg):
        self.cfg = cfg
        cfg.ensure_dirs()
        self.data = self._load()
        self._recalc()

    def _load(self):
        path = self.cfg.index_path
        if not os.path.isfile(path):
            return _empty_index()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (ValueError, OSError):
            return _empty_index()
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            return _empty_index()
        base = _empty_index()
        base.update(data)
        return base

    def _recalc(self):
        self._used = sum(int(i.get("size", 0)) for i in self.data["items"])

    def refresh_if_changed(self):
        """磁盘被 --job-now / 其他进程改写后，重新载入内存快照。

        按 index.json 的 mtime 判断；无变化时是零成本的 stat 调用。
        """
        try:
            stamp = os.stat(self.cfg.index_path).st_mtime_ns
        except OSError:
            return
        if stamp != getattr(self, "_stamp", None):
            self.data = self._load()
            self._recalc()
            self._stamp = stamp

    @property
    def items(self):
        return sorted(self.data["items"], key=lambda i: int(i["id"]))

    @property
    def used_bytes(self):
        return self._used

    @property
    def frozen(self):
        return bool(self.data.get("frozen"))

    @property
    def last_job_date(self):
        return self.data.get("last_job_date", "")

    def save(self):
        """原子写回：同目录临时文件 + os.replace。"""
        cfg = self.cfg
        cfg.ensure_dirs()
        fd, tmp = tempfile.mkstemp(prefix="index-", suffix=".tmp", dir=cfg.data_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, separators=(",", ":"))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, cfg.index_path)
            try:
                self._stamp = os.stat(cfg.index_path).st_mtime_ns
            except OSError:
                pass
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def normalize_ext(self, ext, content_type=""):
        ext = (ext or "").lower()
        if ext in ALLOWED_EXT:
            return ".jpg" if ext == ".jpeg" else ext
        ct = (content_type or "").split(";")[0].strip().lower()
        mapping = {
            "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
            "image/webp": ".webp", "image/bmp": ".bmp",
        }
        return mapping.get(ct, ".jpg")

    def add(self, blob, cat, src, ext=".jpg"):
        """落盘前预判配额；超限时返回 None 且不写文件。"""
        size = len(blob)
        if self.frozen or self._used + size > self.cfg.quota_bytes:
            return None
        item_id = int(self.data["next_id"])
        filename = "%08d%s" % (item_id, ext)
        path = os.path.join(self.cfg.images_dir, filename)
        with open(path, "wb") as f:
            f.write(blob)
        item = {
            "id": item_id,
            "file": filename,
            "cat": cat,
            "size": size,
            "at": datetime.now().isoformat(timespec="seconds"),
            "vote": None,
            "src": src,
        }
        self.data["items"].append(item)
        self.data["next_id"] = item_id + 1
        self._used += size
        return item

    def remove(self, item):
        path = os.path.join(self.cfg.images_dir, item["file"])
        try:
            os.remove(path)
        except OSError:
            pass
        self.data["items"] = [i for i in self.data["items"] if i["id"] != item["id"]]
        self._used -= int(item.get("size", 0))
        if self._used < 0:
            self._used = 0

    def vote(self, item_id, value):
        """改票语义：点击已选按钮取消为无票，点击另一按钮改票。"""
        if value not in ("oo", "xx"):
            return None
        for i in self.data["items"]:
            if int(i["id"]) == int(item_id):
                i["vote"] = None if i.get("vote") == value else value
                self.save()
                return i["vote"]
        return None

    def by_cat(self, cat):
        if cat not in self.cfg.categories:
            return []
        return [i for i in self.items if i.get("cat") == cat]

    def page(self, cat, page_no):
        arr = self.by_cat(cat)
        total = len(arr)
        size = max(1, int(self.cfg.page_size))
        pages = max(1, (total + size - 1) // size)
        page_no = max(1, min(int(page_no), pages))
        chunk = arr[(page_no - 1) * size: page_no * size]
        return {
            "page": page_no,
            "pages": pages,
            "total": total,
            "items": [self.public(i) for i in chunk],
        }

    def public(self, i):
        token = self.cfg.access_token
        suffix = "?token=" + _quote(token) if token else ""
        return {
            "id": i["id"],
            "url": "/img/" + i["file"] + suffix,
            "cat": i["cat"],
            "size": i["size"],
            "at": i.get("at", ""),
            "vote": i.get("vote"),
        }

    def status(self):
        counts = {c: len(self.by_cat(c)) for c in self.cfg.categories}
        return {
            "used_bytes": self._used,
            "used": cfgmod.human_bytes(self._used),
            "quota_bytes": self.cfg.quota_bytes,
            "quota": cfgmod.human_bytes(self.cfg.quota_bytes),
            "percent": round(self._used * 100.0 / max(1, self.cfg.quota_bytes), 2),
            "total": len(self.data["items"]),
            "counts": counts,
            "frozen": self.frozen,
            "last_job_date": self.last_job_date,
            "job_hour": self.cfg.job_hour,
            "page_size": self.cfg.page_size,
            "credentials": dict(self.data.get("credentials") or
                                {"state": "unknown", "configured_hosts": []}),
            "auth_error": self.data.get("auth_error", ""),
            "auth_error_at": self.data.get("auth_error_at", ""),
        }


def _quote(s):
    from urllib.parse import quote
    return quote(s, safe="")
