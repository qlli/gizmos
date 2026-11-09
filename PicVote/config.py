"""PicVote 配置。

只依赖 Python 标准库，兼容 Python 3.6+（CentOS 7 自带 python3 3.6.8）。
环境变量可覆盖，便于 systemd 部署。
"""
import os

GiB = 1024 ** 3
MiB = 1024 ** 2


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    def __init__(self, root="", quota_bytes=10 * GiB, page_size=20,
                 cleanup_ratio=0.10, job_hour=3, host="0.0.0.0", port=18080,
                 access_token="", user_agent="PicVote/1.0 (personal image browser)",
                 request_interval=1.0, timeout=10.0,                  max_image_bytes=8 * MiB,
                 jandan_max_pages=20,
                 categories=None, category_labels=None):
        self.root = root or os.environ.get(
            "PICVOTE_ROOT", os.path.dirname(os.path.abspath(__file__))
        )
        self.root = os.path.abspath(self.root)
        self.quota_bytes = quota_bytes
        self.page_size = page_size
        self.cleanup_ratio = cleanup_ratio
        self.job_hour = job_hour
        self.host = host
        self.port = port
        self.access_token = access_token
        self.user_agent = user_agent
        self.request_interval = request_interval
        self.timeout = timeout
        self.max_image_bytes = max_image_bytes
        self.jandan_max_pages = jandan_max_pages
        self.categories = categories or ("beauty", "handsome")
        self.category_labels = category_labels or {
            "beauty": "美女",
            "handsome": "帅哥",
        }

    @classmethod
    def from_env(cls):
        return cls(
            quota_bytes=_int("PICVOTE_QUOTA_BYTES", 10 * GiB),
            page_size=_int("PICVOTE_PAGE_SIZE", 20),
            cleanup_ratio=_float("PICVOTE_CLEANUP_RATIO", 0.10),
            job_hour=_int("PICVOTE_JOB_HOUR", 3),
            host=os.environ.get("PICVOTE_HOST", "0.0.0.0"),
            port=_int("PICVOTE_PORT", 18080),
            access_token=os.environ.get("PICVOTE_ACCESS_TOKEN", ""),
            user_agent=os.environ.get(
                "PICVOTE_UA", "PicVote/1.0 (personal image browser)"
            ),
            request_interval=_float("PICVOTE_REQUEST_INTERVAL", 1.0),
            timeout=_float("PICVOTE_TIMEOUT", 10.0),
            max_image_bytes=_int("PICVOTE_MAX_IMAGE_BYTES", 8 * MiB),
            jandan_max_pages=_int("PICVOTE_JANDAN_MAX_PAGES", 20),
        )

    @property
    def data_dir(self):
        return os.path.join(self.root, "data")

    @property
    def images_dir(self):
        return os.path.join(self.data_dir, "images")

    @property
    def index_path(self):
        return os.path.join(self.data_dir, "index.json")

    @property
    def sources_path(self):
        return os.path.join(self.root, "sources.txt")

    @property
    def log_path(self):
        return os.path.join(self.data_dir, "picvote.log")

    @property
    def secrets_dir(self):
        return os.path.join(self.root, "secrets")

    @property
    def credentials_path(self):
        return os.path.join(self.secrets_dir, "credentials.json")

    def ensure_dirs(self):
        os.makedirs(self.images_dir, exist_ok=True)


def human_bytes(n):
    n = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024 or unit == "TiB":
            return "%.1f %s" % (n, unit) if unit != "B" else "%d B" % int(n)
        n /= 1024
    return "%d B" % int(n)
