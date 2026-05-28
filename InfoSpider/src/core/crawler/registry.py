"""爬虫注册中心 - 插件化加载机制"""
from typing import Dict, List, Type, Optional

from loguru import logger

from .base import BaseCrawler


class CrawlerRegistry:
    """爬虫注册中心
    
    通过装饰器自动注册爬虫，支持按名称获取和枚举。
    
    使用方式:
        @CrawlerRegistry.register("zhihu")
        class ZhihuCrawler(BaseCrawler):
            ...
        
        crawler = CrawlerRegistry.create("zhihu", config)
    """
    
    _crawlers: Dict[str, Type[BaseCrawler]] = {}
    
    @classmethod
    def register(cls, source_name: str):
        """装饰器：注册爬虫类
        
        Args:
            source_name: 平台标识（如 "zhihu", "bilibili"）
        """
        def wrapper(crawler_cls: Type[BaseCrawler]):
            cls._crawlers[source_name] = crawler_cls
            logger.debug(f"[Registry] 已注册爬虫: {source_name} → {crawler_cls.__name__}")
            return crawler_cls
        return wrapper
    
    @classmethod
    def create(cls, source_name: str, **kwargs) -> BaseCrawler:
        """创建爬虫实例
        
        Args:
            source_name: 平台标识
            **kwargs: 传递给爬虫构造函数的参数
            
        Returns:
            爬虫实例
            
        Raises:
            ValueError: 未注册的爬虫
        """
        crawler_cls = cls._crawlers.get(source_name)
        if not crawler_cls:
            available = list(cls._crawlers.keys())
            raise ValueError(f"未注册的爬虫: {source_name}，可用: {available}")
        return crawler_cls(**kwargs)
    
    @classmethod
    def get_class(cls, source_name: str) -> Optional[Type[BaseCrawler]]:
        """获取爬虫类（不实例化）"""
        return cls._crawlers.get(source_name)
    
    @classmethod
    def list_sources(cls) -> List[str]:
        """列出所有已注册的爬虫名称"""
        return list(cls._crawlers.keys())
    
    @classmethod
    def list_all(cls) -> Dict[str, Type[BaseCrawler]]:
        """列出所有已注册的爬虫"""
        return dict(cls._crawlers)
