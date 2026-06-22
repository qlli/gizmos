"""采集配置(Collection) - JSON 驱动的通用抓取配置

一个 Collection 描述一次可复用的采集需求，包含：
- 关键词列表（用于搜索和关键词过滤）
- 抓取参数（目标源、任务类型、抓取数量上限等）
- 匹配参数（通过阈值、是否强制命中关键词、额外黑名单等）

JSON 文件默认存放在 config/collections/*.json。
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from ..utils.config import get_config


@dataclass
class MatchOptions:
    """匹配与过滤参数"""
    min_score: float = 0.3                # 综合评分通过阈值
    require_keyword_match: bool = False   # 是否要求标题/摘要必须命中关键词
    blacklist_keywords: List[str] = field(default_factory=list)
    spam_keywords: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "MatchOptions":
        data = data or {}
        return cls(
            min_score=float(data.get("min_score", 0.3)),
            require_keyword_match=bool(data.get("require_keyword_match", False)),
            blacklist_keywords=list(data.get("blacklist_keywords", []) or []),
            spam_keywords=list(data.get("spam_keywords", []) or []),
        )

    def to_dict(self) -> dict:
        return {
            "min_score": self.min_score,
            "require_keyword_match": self.require_keyword_match,
            "blacklist_keywords": self.blacklist_keywords,
            "spam_keywords": self.spam_keywords,
        }


@dataclass
class CollectionConfig:
    """采集配置

    通用爬虫抓取配置，可由 JSON 文件加载，支持不同人/不同主题的独立配置。
    """
    name: str = "default"
    description: str = ""
    keywords: List[str] = field(default_factory=list)       # 关键词列表（搜索 + 过滤）
    sources: List[str] = field(default_factory=lambda: ["bilibili"])  # 目标信息源
    task_type: str = "search"                               # search / trending
    limit: int = 20                                         # 每个源抓取数量上限
    per_keyword_limit: int = 0                              # 每个关键词抓取上限(0=自动)
    match: MatchOptions = field(default_factory=MatchOptions)

    @classmethod
    def from_dict(cls, data: dict) -> "CollectionConfig":
        data = data or {}
        return cls(
            name=str(data.get("name", "default")),
            description=str(data.get("description", "")),
            keywords=list(data.get("keywords", []) or []),
            sources=list(data.get("sources", ["bilibili"]) or ["bilibili"]),
            task_type=str(data.get("task_type", "search")),
            limit=int(data.get("limit", 20)),
            per_keyword_limit=int(data.get("per_keyword_limit", 0) or 0),
            match=MatchOptions.from_dict(data.get("match")),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
            "sources": self.sources,
            "task_type": self.task_type,
            "limit": self.limit,
            "per_keyword_limit": self.per_keyword_limit,
            "match": self.match.to_dict(),
        }

    @classmethod
    def from_file(cls, path: str) -> "CollectionConfig":
        """从 JSON 文件加载采集配置"""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"采集配置不存在: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = cls.from_dict(data)
        if not config.name or config.name == "default":
            config.name = file_path.stem
        logger.info(f"[Collection] 已加载采集配置: {file_path}")
        return config

    @classmethod
    def load(cls, name: str, collections_dir: Optional[str] = None) -> "CollectionConfig":
        """按名称从 collections 目录加载

        Args:
            name: 配置名（不含扩展名）或 JSON 文件路径
            collections_dir: 配置目录，默认 config/collections
        """
        candidate = Path(name)
        if candidate.suffix == ".json" and candidate.exists():
            return cls.from_file(str(candidate))

        base_dir = Path(collections_dir) if collections_dir else cls.default_dir()
        file_path = base_dir / f"{name}.json"
        return cls.from_file(str(file_path))

    @staticmethod
    def default_dir() -> Path:
        """默认采集配置目录 config/collections"""
        return Path(get_config().config_dir) / "collections"

    @classmethod
    def list_available(cls, collections_dir: Optional[str] = None) -> List[str]:
        """列出可用的采集配置名称"""
        base_dir = Path(collections_dir) if collections_dir else cls.default_dir()
        if not base_dir.exists():
            return []
        return sorted(p.stem for p in base_dir.glob("*.json"))
