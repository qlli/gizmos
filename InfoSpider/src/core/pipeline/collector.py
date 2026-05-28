"""采集阶段 - 编排爬虫 + 匹配 + 存储"""
import asyncio
from typing import Dict, List, Optional

from loguru import logger

from .base import BasePipelineStage
from ..crawler.base import BaseCrawler, CrawlItem
from ..crawler.registry import CrawlerRegistry
from ..matcher.keyword import KeywordMatcher
from ..matcher.base import MatchResult
from ...models.user import UserProfile
from ...models.task import CrawlTask, TaskStatus, TaskType
from ...storage.json_storage import JSONStorage
from ...storage.html_report import HTMLReportGenerator
from ...utils.config import get_config


class CollectorStage(BasePipelineStage):
    """采集阶段
    
    编排多个爬虫进行内容采集，通过匹配器过滤，保存结果。
    
    流程:
    1. 根据任务配置获取爬虫实例
    2. 对每个目标源执行搜索/热门采集
    3. 通过 KeywordMatcher 过滤评分
    4. 保存到 JSON + 生成 HTML 报告
    """
    
    def __init__(self):
        self.config = get_config()
        self.matcher = KeywordMatcher()
        self.storage = JSONStorage()
        self.report_gen = HTMLReportGenerator()
        self._crawlers: Dict[str, BaseCrawler] = {}
    
    async def setup(self) -> None:
        """初始化所有需要的爬虫"""
        logger.info("[Pipeline] 采集阶段初始化")
    
    async def teardown(self) -> None:
        """关闭所有爬虫"""
        for name, crawler in self._crawlers.items():
            try:
                await crawler.close()
                logger.debug(f"[Pipeline] 已关闭爬虫: {name}")
            except Exception as e:
                logger.warning(f"[Pipeline] 关闭爬虫 {name} 出错: {e}")
        self._crawlers.clear()
        logger.info("[Pipeline] 采集阶段资源已释放")
    
    async def _get_crawler(self, source: str) -> BaseCrawler:
        """获取或创建爬虫实例"""
        if source not in self._crawlers:
            crawler = CrawlerRegistry.create(source)
            await crawler.initialize()
            self._crawlers[source] = crawler
        return self._crawlers[source]
    
    async def run(self, task: Optional[CrawlTask] = None,
                  sources: Optional[List[str]] = None,
                  keywords: Optional[List[str]] = None,
                  limit: int = 20,
                  task_type: str = "search",
                  user_id: str = "default",
                  auto_open_report: bool = True,
                  **kwargs) -> List[CrawlItem]:
        """执行采集
        
        Args:
            task: 采集任务（如提供则覆盖其他参数）
            sources: 目标平台列表
            keywords: 搜索关键词
            limit: 每个源的最大采集量
            task_type: 任务类型 (search/trending)
            user_id: 用户ID
            auto_open_report: 是否自动打开HTML报告
            
        Returns:
            匹配通过的 CrawlItem 列表
        """
        # 解析参数
        if task:
            sources = task.sources
            keywords = task.keywords
            limit = task.limit
            task_type = task.task_type.value
            user_id = task.user_id
            task.start()
        
        if not sources:
            sources = ["bilibili"]  # 默认只用不需要登录的源
        
        # 加载用户画像
        profiles_dir = self.config.get('storage.profiles_path', 'data/profiles')
        user_profile = UserProfile.load(user_id, profiles_dir)
        
        logger.info(f"[Pipeline] 开始采集: sources={sources}, keywords={keywords}, "
                    f"limit={limit}, type={task_type}, user={user_id}")
        
        # 采集阶段
        all_items: List[CrawlItem] = []
        
        for source in sources:
            try:
                crawler = await self._get_crawler(source)
                source_items = await self._collect_from_source(
                    crawler, task_type, keywords, limit
                )
                all_items.extend(source_items)
                logger.info(f"[Pipeline] {source} 采集完成: {len(source_items)} 条")
            except Exception as e:
                logger.error(f"[Pipeline] {source} 采集失败: {e}")
        
        logger.info(f"[Pipeline] 采集总计: {len(all_items)} 条原始结果")
        
        deduped_items = self._deduplicate_items(all_items)
        if len(deduped_items) != len(all_items):
            logger.info(f"[Pipeline] 去重合并: {len(all_items)} → {len(deduped_items)} 条")
        
        # 匹配过滤阶段
        matched_items: List[CrawlItem] = []
        for item in deduped_items:
            result = await self.matcher.match(item, user_profile)
            if result.passed:
                matched_items.append(item)

        
        logger.info(f"[Pipeline] 匹配过滤: {len(all_items)} → {len(matched_items)} 条通过")
        
        # 存储
        if matched_items:
            source_tag = "_".join(sources)
            self.storage.save(matched_items, source=source_tag)
            
            # 生成HTML报告
            title = f"InfoSpider 采集报告 - {', '.join(sources)}"
            self.report_gen.generate(matched_items, title=title, auto_open=auto_open_report)
        
        # 更新任务状态
        if task:
            task.complete(result_count=len(matched_items))
        
        return matched_items
    
    def _deduplicate_items(self, items: List[CrawlItem]) -> List[CrawlItem]:
        """按稳定键去重，并保留互动质量更高的条目"""
        unique: Dict[str, CrawlItem] = {}
        for item in items:
            key = self._dedup_key(item)
            existing = unique.get(key)
            if not existing or self._item_quality_value(item) > self._item_quality_value(existing):
                unique[key] = item
        return list(unique.values())
    
    @staticmethod
    def _dedup_key(item: CrawlItem) -> str:
        """生成跨关键词稳定去重键"""
        if item.source and item.item_id:
            return f"{item.source}:{item.item_type}:{item.item_id}"
        if item.url:
            return f"url:{item.url.strip().lower()}"
        return f"fallback:{item.source}:{item.title.strip().lower()}"
    
    @staticmethod
    def _item_quality_value(item: CrawlItem) -> int:
        """用于重复项取舍的粗略质量值"""
        return item.voteup * 3 + item.view_count + item.comment_count * 5
    
    async def _collect_from_source(self, crawler: BaseCrawler, task_type: str,
                                    keywords: Optional[List[str]], limit: int) -> List[CrawlItem]:
        """从单个源采集"""
        items = []

        
        if task_type == "trending":
            async for item in crawler.get_trending(limit=limit):
                items.append(item)
        elif task_type == "search" and keywords:
            per_keyword = max(limit // len(keywords), 10)
            for keyword in keywords:
                async for item in crawler.search(keyword, limit=per_keyword):
                    items.append(item)
                    if len(items) >= limit:
                        break
                if len(items) >= limit:
                    break
        else:
            # 默认获取热门
            async for item in crawler.get_trending(limit=limit):
                items.append(item)
        
        return items[:limit]
