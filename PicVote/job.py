"""每日凌晨任务：清理 → 抓取 → 汰换（结论 4）。

- 同一天只跑一次（last_job_date）；frozen 后任何任务直接返回。
- 清理：按 id（抓取时间）从最旧开始，删除 ceil(总数 * 10%) 张，跳过 oo 图片。
- 终态：清理后剩余图片全为 oo 且配额已满 → frozen = true，之后不再抓取/清理/汰换。
- 未冻结时抓取补足配额；来源耗尽则记录并次日再试。
"""
import math
from datetime import date, datetime

from credentials import Credentials
from sources import AuthRequired, Fetcher, load_sources


class JobResult:
    def __init__(self, status, **kw):
        self.status = status
        self.detail = kw

    def as_dict(self):
        d = {"status": self.status}
        d.update(self.detail)
        return d

    def __str__(self):
        return "%s %s" % (self.status, self.detail)


def cleanup(store, cfg, log):
    items = store.items
    target = int(math.ceil(len(items) * cfg.cleanup_ratio))
    victims = [i for i in items if i.get("vote") != "oo"][:target]
    if not victims:
        log("清理：无可删除的非点赞图片")
        store.save()
        return 0
    for item in victims:
        store.remove(item)
    store.save()
    log("清理：目标 %d 张，实际删除 %d 张（点赞图片已跳过）" % (target, len(victims)))
    return len(victims)


def crawl(store, cfg, log, sources, credentials=None):
    """返回 (新增张数, 是否因配额停止, 凭证失效信息)。"""
    if not sources:
        log("抓取：没有可用来源")
        return 0, False, None
    fetcher = Fetcher(cfg, log, credentials=credentials)
    seen = {i.get("src", "") for i in store.items}
    added, quota_hit, auth_error = 0, False, None
    for source in sources:
        if store.used_bytes >= cfg.quota_bytes:
            quota_hit = True
            break
        try:
            for cat, blob, ext, src in source.iter_images(fetcher, store, seen):
                item = store.add(blob, cat, src, ext)
                if item is None:
                    quota_hit = True
                    break
                added += 1
                if added % 20 == 0:
                    store.save()
        except AuthRequired as e:
            auth_error = e.message
            log("告警：凭证已失效 —— %s" % auth_error)
            break
        except Exception as e:
            log("来源 %s 异常，跳过：%s" % (type(source).__name__, e))
        if quota_hit:
            break
    store.save()
    return added, quota_hit, auth_error


def run_job(store, cfg, log=None, force=False):
    log = log or (lambda msg: print(msg))
    today = date.today().isoformat()

    if store.frozen:
        log("任务跳过：已进入终态（全部为点赞图片且配额已满）")
        return JobResult("frozen")
    if not force and store.last_job_date == today:
        log("任务跳过：%s 当日已执行" % today)
        return JobResult("already_ran", date=today)

    store.data["last_job_date"] = today
    store.save()
    log("=== 每日任务开始 %s ===" % datetime.now().isoformat(timespec="seconds"))

    removed = cleanup(store, cfg, log)
    current = store.items
    quota_full = store.used_bytes >= cfg.quota_bytes
    if current and all(i.get("vote") == "oo" for i in current) and quota_full:
        store.data["frozen"] = True
        store.save()
        log("终态达成：剩余图片全部为点赞且配额已满，此后不再抓取/清理/汰换")
        return JobResult("frozen", removed=removed, added=0)

    credentials = Credentials(cfg.credentials_path, log)
    sources = load_sources(cfg, log)
    added, quota_hit, auth_error = crawl(store, cfg, log, sources, credentials)
    if quota_hit:
        log("抓取：已达 10G 上限，当天停止；次日凌晨恢复")
    else:
        log("抓取：来源已遍历，本次新增 %d 张" % added)

    # 凭证状态写入索引，供 /api/status 与网页顶部显式告警；成功取到图即清除旧告警
    store.data["credentials"] = credentials.status()
    if auth_error:
        store.data["credentials"]["state"] = "expired"
        store.data["auth_error"] = auth_error
        store.data["auth_error_at"] = datetime.now().isoformat(timespec="seconds")
        log("告警：凭证失效，需人工重新提供；网页已标记")
    elif added > 0:
        store.data.pop("auth_error", None)
        store.data.pop("auth_error_at", None)
    store.save()

    log("=== 每日任务结束：删除 %d 张，新增 %d 张，已用 %d/%d 字节 ===" % (
        removed, added, store.used_bytes, cfg.quota_bytes
    ))
    return JobResult(
        "ok", removed=removed, added=added,
        used_bytes=store.used_bytes, quota_hit=quota_hit,
        auth_error=auth_error,
    )
