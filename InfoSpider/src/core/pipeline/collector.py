"""采集阶段 - 编排爬虫 + 匹配 + 存储"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from loguru import logger

from .base import BasePipelineStage
from ..crawler.base import BaseCrawler, CrawlItem
from ..crawler.registry import CrawlerRegistry
from ..matcher.keyword import KeywordMatcher
from ..matcher.base import MatchResult
from ...models.user import UserProfile
from ...models.task import CrawlTask, TaskStatus, TaskType
from ...models.collection import CollectionConfig
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
                  collection: Optional[CollectionConfig] = None,
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
            collection: 采集配置(JSON驱动，提供则覆盖 sources/keywords/limit/task_type)
            sources: 目标平台列表
            keywords: 搜索关键词
            limit: 每个源的最大采集量
            task_type: 任务类型 (search/trending)
            user_id: 用户ID
            auto_open_report: 是否自动打开HTML报告
            
        Returns:
            匹配通过的 CrawlItem 列表
        """
        plan = self._resolve_plan(task, collection, sources, keywords, limit, task_type, user_id)
        if task and not collection:
            task.start()
        
        user_profile = self._load_user_profile(plan["user_id"])
        
        logger.info(f"[Pipeline] 开始采集: sources={plan['sources']}, keywords={plan['keywords']}, "
                    f"limit={plan['limit']}, type={plan['task_type']}, user={plan['user_id']}")
        
        matched_items = await self._crawl_and_match(plan, user_profile)
        
        # 存储
        if matched_items:
            source_tag = "_".join(plan["sources"])
            self.storage.save(matched_items, source=source_tag)
            
            # 生成HTML报告
            title = f"InfoSpider 采集报告 - {', '.join(plan['sources'])}"
            self.report_gen.generate(matched_items, title=title, auto_open=auto_open_report)
        
        # 更新任务状态
        if task:
            task.complete(result_count=len(matched_items))
        
        return matched_items
    
    async def run_continuous(self,
                             deadline: datetime,
                             interval_seconds: int = 300,
                             collection: Optional[CollectionConfig] = None,
                             task: Optional[CrawlTask] = None,
                             sources: Optional[List[str]] = None,
                             keywords: Optional[List[str]] = None,
                             limit: int = 20,
                             task_type: str = "search",
                             user_id: str = "default",
                             auto_open_report: bool = False,
                             **kwargs) -> List[CrawlItem]:
        """持续采集直到到达截止时间
        
        适用于夜间空闲时长时间采集高质量内容，到指定时刻自动停止。
        跨轮去重，仅对新出现的内容做匹配，结果按质量累积并周期性落盘。
        
        Args:
            deadline: 截止时间，到点后停止
            interval_seconds: 每轮采集之间的等待秒数
            其余参数同 run()
            
        Returns:
            累积的、匹配通过的 CrawlItem 列表（按质量降序）
        """
        plan = self._resolve_plan(task, collection, sources, keywords, limit, task_type, user_id)
        user_profile = self._load_user_profile(plan["user_id"])
        
        source_tag = "_".join(plan["sources"])
        seen_keys: set = set()
        accumulated: Dict[str, CrawlItem] = {}
        round_no = 0
        
        logger.info(f"[Pipeline] 持续采集启动: 截止时间={deadline.isoformat()}, "
                    f"轮间隔={interval_seconds}s, sources={plan['sources']}")
        
        while datetime.now() < deadline:
            round_no += 1
            logger.info(f"[Pipeline] === 第 {round_no} 轮采集开始 "
                        f"(剩余 {self._format_remaining(deadline)}) ===")
            
            try:
                matched = await self._crawl_and_match(plan, user_profile, seen_keys=seen_keys,
                                                       page_offset=round_no - 1)
            except Exception as e:
                logger.error(f"[Pipeline] 第 {round_no} 轮采集异常: {e}")
                matched = []
            
            new_count = 0
            for item in matched:
                key = self._dedup_key(item)
                if key not in accumulated:
                    new_count += 1
                accumulated[key] = item
            
            logger.info(f"[Pipeline] 第 {round_no} 轮: 新增 {new_count} 条, "
                        f"累计 {len(accumulated)} 条")
            
            # 周期性落盘，保证夜间中断也能保留已采集结果
            if accumulated:
                ranked = self._rank_items(list(accumulated.values()))
                self.storage.save(ranked, source=source_tag, tag="night")
            
            # 计算下一轮等待时间，不超过截止时间
            remaining = (deadline - datetime.now()).total_seconds()
            if remaining <= 0:
                break
            sleep_time = min(interval_seconds, remaining)
            logger.info(f"[Pipeline] 第 {round_no} 轮结束, 等待 {int(sleep_time)}s 后继续")
            await asyncio.sleep(sleep_time)
        
        ranked = self._rank_items(list(accumulated.values()))
        logger.info(f"[Pipeline] 持续采集结束: 共 {round_no} 轮, 累计 {len(ranked)} 条高质量结果")
        
        # 生成最终报告
        if ranked:
            title = f"InfoSpider 夜间采集报告 - {', '.join(plan['sources'])} ({round_no}轮)"
            self.report_gen.generate(ranked, title=title, auto_open=auto_open_report)
        
        if task:
            task.complete(result_count=len(ranked))
        
        return ranked
    
    def _resolve_plan(self, task: Optional[CrawlTask],
                      collection: Optional[CollectionConfig],
                      sources: Optional[List[str]], keywords: Optional[List[str]],
                      limit: int, task_type: str, user_id: str) -> dict:
        """解析采集计划，统一 collection/task/显式参数三种来源
        
        采集配置优先级最高，其次是任务，最后是显式参数。
        如使用采集配置，会按配置重建匹配器。
        """
        per_keyword_limit = 0
        
        if collection:
            sources = collection.sources
            keywords = collection.keywords
            limit = collection.limit
            task_type = collection.task_type
            per_keyword_limit = collection.per_keyword_limit
            self.matcher = KeywordMatcher(
                keywords=collection.keywords,
                min_score=collection.match.min_score,
                require_keyword_match=collection.match.require_keyword_match,
                extra_blacklist=collection.match.blacklist_keywords,
                extra_spam=collection.match.spam_keywords,
            )
            logger.info(f"[Pipeline] 使用采集配置: {collection.name} "
                        f"(关键词={len(keywords)}, 源={sources}, 上限={limit})")
        elif task:
            sources = task.sources
            keywords = task.keywords
            limit = task.limit
            task_type = task.task_type.value
            user_id = task.user_id
        
        if not sources:
            sources = ["bilibili"]  # 默认只用不需要登录的源
        
        return {
            "sources": sources,
            "keywords": keywords,
            "limit": limit,
            "task_type": task_type,
            "per_keyword_limit": per_keyword_limit,
            "user_id": user_id,
        }
    
    def _load_user_profile(self, user_id: str) -> UserProfile:
        """加载用户画像"""
        profiles_dir = self.config.get('storage.profiles_path', 'data/profiles')
        return UserProfile.load(user_id, profiles_dir)
    
    async def _crawl_and_match(self, plan: dict, user_profile: UserProfile,
                               seen_keys: Optional[set] = None,
                               page_offset: int = 0) -> List[CrawlItem]:
        """单轮采集 + 去重 + 匹配
        
        Args:
            plan: 采集计划（_resolve_plan 结果）
            user_profile: 用户画像
            seen_keys: 跨轮去重集合，提供时会跳过已处理过的条目并就地更新
            page_offset: 逐轮加深偏移，传给爬虫从更深的页开始
            
        Returns:
            本轮匹配通过的 CrawlItem 列表
        """
        sources = plan["sources"]
        keywords = plan["keywords"]
        limit = plan["limit"]
        task_type = plan["task_type"]
        per_keyword_limit = plan["per_keyword_limit"]
        
        # 采集阶段
        all_items: List[CrawlItem] = []
        for source in sources:
            try:
                crawler = await self._get_crawler(source)
                source_items = await self._collect_from_source(
                    crawler, task_type, keywords, limit, per_keyword_limit, page_offset
                )
                all_items.extend(source_items)
                logger.info(f"[Pipeline] {source} 采集完成: {len(source_items)} 条")
            except Exception as e:
                logger.error(f"[Pipeline] {source} 采集失败: {e}")
        
        logger.info(f"[Pipeline] 采集总计: {len(all_items)} 条原始结果")
        
        # 单轮去重
        deduped_items = self._deduplicate_items(all_items)
        if len(deduped_items) != len(all_items):
            logger.info(f"[Pipeline] 去重合并: {len(all_items)} → {len(deduped_items)} 条")
        
        # 跨轮去重：仅处理未见过的条目
        if seen_keys is not None:
            fresh_items = []
            for item in deduped_items:
                key = self._dedup_key(item)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                fresh_items.append(item)
            if len(fresh_items) != len(deduped_items):
                logger.info(f"[Pipeline] 跨轮去重: {len(deduped_items)} → {len(fresh_items)} 条新内容")
            deduped_items = fresh_items
        
        # 匹配过滤
        matched_items: List[CrawlItem] = []
        for item in deduped_items:
            result = await self.matcher.match(item, user_profile)
            if result.passed:
                matched_items.append(item)
        
        logger.info(f"[Pipeline] 匹配过滤: {len(deduped_items)} → {len(matched_items)} 条通过")
        return matched_items
    
    def _rank_items(self, items: List[CrawlItem]) -> List[CrawlItem]:
        """按互动质量降序排序"""
        return sorted(items, key=self._item_quality_value, reverse=True)
    
    @staticmethod
    def _format_remaining(deadline: datetime) -> str:
        """格式化距离截止时间的剩余时长"""
        total = int((deadline - datetime.now()).total_seconds())
        if total < 0:
            total = 0
        hours, rem = divmod(total, 3600)
        minutes, _ = divmod(rem, 60)
        return f"{hours}h{minutes}m"
    
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
                                    keywords: Optional[List[str]], limit: int,
                                    per_keyword_limit: int = 0,
                                    page_offset: int = 0) -> List[CrawlItem]:
        """从单个源采集
        
        page_offset: 逐轮加深偏移，>0 时从更深的页/偏移开始抓取
        """
        items = []
        
        if task_type == "trending":
            async for item in crawler.get_trending(limit=limit, page_offset=page_offset):
                items.append(item)
        elif task_type == "search" and keywords:
            if per_keyword_limit > 0:
                per_keyword = per_keyword_limit
            else:
                per_keyword = max(limit // len(keywords), 10)
            for keyword in keywords:
                async for item in crawler.search(keyword, limit=per_keyword, page_offset=page_offset):
                    items.append(item)
                    if len(items) >= limit:
                        break
                if len(items) >= limit:
                    break
        else:
            # 默认获取热门
            async for item in crawler.get_trending(limit=limit, page_offset=page_offset):
                items.append(item)
        
        return items[:limit]
