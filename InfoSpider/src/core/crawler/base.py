"""爬虫基类和统一数据结构"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, List, Optional, Any
from datetime import datetime


@dataclass
class CrawlItem:
    """统一爬取结果数据结构
    
    所有平台的爬取结果都统一为此格式，消除平台差异。
    """
    source: str           # 来源平台: zhihu / bilibili / youtube / github / paper
    item_type: str        # 类型: article / answer / video / repo / paper
    item_id: str          # 平台内唯一ID
    title: str = ""
    url: str = ""
    author: str = ""
    content: str = ""     # 正文/描述
    excerpt: str = ""     # 摘要
    metadata: Dict[str, Any] = field(default_factory=dict)  # 平台特有字段
    voteup: int = 0       # 点赞/好评数
    comment_count: int = 0
    view_count: int = 0   # 浏览/播放数
    published_at: Optional[str] = None
    crawled_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "source": self.source,
            "item_type": self.item_type,
            "item_id": self.item_id,
            "title": self.title,
            "url": self.url,
            "author": self.author,
            "content": self.content,
            "excerpt": self.excerpt,
            "metadata": self.metadata,
            "voteup": self.voteup,
            "comment_count": self.comment_count,
            "view_count": self.view_count,
            "published_at": self.published_at,
            "crawled_at": self.crawled_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CrawlItem':
        """从字典创建"""
        return cls(
            source=data.get("source", ""),
            item_type=data.get("item_type", ""),
            item_id=data.get("item_id", ""),
            title=data.get("title", ""),
            url=data.get("url", ""),
            author=data.get("author", ""),
            content=data.get("content", ""),
            excerpt=data.get("excerpt", ""),
            metadata=data.get("metadata", {}),
            voteup=data.get("voteup", 0),
            comment_count=data.get("comment_count", 0),
            view_count=data.get("view_count", 0),
            published_at=data.get("published_at"),
            crawled_at=data.get("crawled_at", datetime.now().isoformat())
        )


class BaseCrawler(ABC):
    """爬虫基类 - 所有平台爬虫必须实现此接口
    
    使用方式:
        async with crawler:
            async for item in crawler.search("keyword"):
                process(item)
    """
    
    source_name: str = ""     # 平台标识
    source_type: str = ""     # feed / video / code / academic
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化爬虫（启动浏览器/建立连接等）"""
    
    @abstractmethod
    async def close(self) -> None:
        """关闭爬虫（释放资源）"""
    
    @abstractmethod
    async def search(self, keyword: str, limit: int = 20, **filters) -> AsyncIterator[CrawlItem]:
        """按关键词搜索
        
        Args:
            keyword: 搜索关键词
            limit: 最大返回数量
            **filters: 平台特有的过滤参数
            
        Yields:
            CrawlItem: 搜索结果
        """
        yield  # type: ignore
    
    @abstractmethod
    async def get_trending(self, category: str = "", limit: int = 20, **filters) -> AsyncIterator[CrawlItem]:
        """获取热门/趋势内容
        
        Args:
            category: 分类/频道
            limit: 最大返回数量
            **filters: 平台特有参数（如 page_offset 用于逐轮加深）
            
        Yields:
            CrawlItem: 热门内容
        """
        yield  # type: ignore
    
    @abstractmethod
    async def get_content(self, item: CrawlItem) -> str:
        """获取完整内容（正文/视频描述等）
        
        Args:
            item: 已采集的条目
            
        Returns:
            完整内容文本
        """
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
