"""PicVote 入口：个人自用的图片抓取 / 浏览服务。

用法：
  python app.py                 启动网页服务 + 凌晨定时任务
  python app.py --job-now       立即执行一次「清理 → 抓取 → 汰换」，然后退出
  python app.py --status        打印配额与索引状态，然后退出
  python app.py --no-scheduler  只启动网页，不跑定时任务
"""
import argparse
import logging
import sys
import threading
from datetime import date, datetime

from config import Config, human_bytes
from job import run_job
from storage import Store
from web import serve_forever


def setup_logging(cfg):
    cfg.ensure_dirs()
    logger = logging.getLogger("picvote")
    logger.setLevel(logging.INFO)
    for h in list(logger.handlers):
        logger.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = logging.FileHandler(cfg.log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def should_run(now, cfg, store):
    """是否应当执行每日任务：仅在设定小时、当日未跑过、且未冻结。"""
    return (now.hour == cfg.job_hour
            and store.last_job_date != date.today().isoformat()
            and not store.frozen)


def scheduler(store, cfg, log, stop):
    """启动即检查一次，之后每 60 秒检查一次；仅在设定小时触发。"""
    log.info("定时任务已启动：每天 %02d 点执行（当日仅一次）" % cfg.job_hour)
    while not stop.is_set():
        if should_run(datetime.now(), cfg, store):
            try:
                result = run_job(store, cfg, log.info)
                log.info("每日任务结果：%s" % result)
            except Exception as e:
                log.exception("每日任务异常：%s" % e)
        stop.wait(60)


def main(argv=None):
    p = argparse.ArgumentParser(description="PicVote 个人图片服务")
    p.add_argument("--job-now", action="store_true", help="立即执行每日任务后退出")
    p.add_argument("--status", action="store_true", help="打印状态后退出")
    p.add_argument("--no-scheduler", action="store_true", help="不启动定时任务")
    p.add_argument("--host", default=None, help="覆盖监听地址")
    p.add_argument("--port", type=int, default=None, help="覆盖监听端口")
    args = p.parse_args(argv)

    cfg = Config.from_env()
    if args.host:
        cfg.host = args.host
    if args.port:
        cfg.port = args.port
    log = setup_logging(cfg)
    store = Store(cfg)

    if args.status:
        s = store.status()
        for k, v in s.items():
            print("%-16s %s" % (k, v))
        return 0

    log.info("工程目录：%s" % cfg.root)
    log.info("配额：%s（%d 字节）" % (human_bytes(cfg.quota_bytes), cfg.quota_bytes))

    if args.job_now:
        result = run_job(store, cfg, log.info, force=True)
        log.info("任务结果：%s" % result)
        return 0

    stop = threading.Event()
    if not args.no_scheduler:
        t = threading.Thread(target=scheduler, args=(store, cfg, log, stop), daemon=True)
        t.start()
    try:
        serve_forever(store, cfg, log.info)
    finally:
        stop.set()
    return 0


if __name__ == "__main__":
    sys.exit(main())
