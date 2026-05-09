"""搜集阶段"""
from typing import Dict, List, Optional
from loguru import logger

from ..crawler.zhihu_client import ZhihuClient
from ..crawler.article_collector import ArticleCollector
from ..crawler.filters import PowerLawFilter, ContentQualityFilter, UserInterestFilter
from ..storage.json_storage import JSONStorage


class CollectorStage:
    """搜集阶段 - 流水线第一阶段"""
    
    def __init__(self, headless: bool = True):
        """
        初始化搜集阶段
        
        Args:
            headless: 是否无头模式（True=后台运行）
        """
        self.client = ZhihuClient(headless=headless)
        self.collector = ArticleCollector(self.client)
        self.power_filter = PowerLawFilter()
        self.quality_filter = ContentQualityFilter()
        self.interest_filter = UserInterestFilter()
        self.storage = JSONStorage()
        
        self.logger = logger.bind(name="collector")
    
    def __enter__(self):
        """上下文管理器入口：启动浏览器客户端并确认登录状态"""
        self.client.__enter__()
        self.logger.info("浏览器客户端已启动，准备检查知乎登录状态")
        self.client.ensure_logged_in()
        self.logger.info("知乎登录状态检查完成")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口：关闭浏览器客户端"""
        self.client.__exit__(exc_type, exc_val, exc_tb)
    
    def collect_hot_content(self, limit: int = 100) -> List[Dict]:
        """搜集热门内容"""
        self.logger.info(f"开始搜集热门内容，限制: {limit}")
        
        articles = self.collector.collect_hot_feed(limit)
        articles = self.collector.deduplicate(articles)
        
        # 标记极端内容
        for article in articles:
            article['is_extreme'] = self.power_filter.is_extreme(article)
            article['interest_score'] = self.interest_filter.get_interest_score(
                article.get('title', ''),
                article.get('excerpt', ''),
                article.get('question_title', '')
            )
        
        self.logger.info(f"搜集完成，获得 {len(articles)} 篇文章")
        return articles
    
    def collect_by_interest_keywords(self, keywords: List[str] = None) -> List[Dict]:
        """按兴趣关键词搜集"""
        if keywords is None:
            from ..utils.config import get_config
            config = get_config()
            keywords = config.user_profile.get('interests', [])
        
        self.logger.info(f"按关键词搜集: {keywords}")
        
        articles = self.collector.collect_by_keywords(keywords, per_keyword=30)
        articles = self.collector.deduplicate(articles)
        
        for article in articles:
            article['is_extreme'] = self.power_filter.is_extreme(article)
            article['interest_score'] = self.interest_filter.get_interest_score(
                article.get('title', ''),
                article.get('excerpt', ''),
                article.get('question_title', '')
            )
        
        return articles
    
    def collect_by_topics(self, topic_ids: List[str]) -> List[Dict]:
        """按话题搜集"""
        self.logger.info(f"按话题搜集: {topic_ids}")
        
        articles = self.collector.collect_by_topics(topic_ids, per_topic=50)
        articles = self.collector.deduplicate(articles)
        
        for article in articles:
            article['is_extreme'] = self.power_filter.is_extreme(article)
        
        return articles
    
    def save_for_processing(self, articles: List[Dict], is_stock: bool = True):
        """保存待处理文章"""
        self.logger.info(
            f"[STEP 5/8] 保存搜集结果到 JSON: count={len(articles)}, type={'stock' if is_stock else 'incremental'}"
        )
        filepath = self.storage.save_raw_articles(articles, is_stock)
        self.logger.info(f"[STEP 5/8] 搜集结果已保存: {filepath.resolve()}")
        
        # 保存已处理的ID列表
        processed_ids = set()
        missing_id_count = 0
        for a in articles:
            if 'type' not in a or 'id' not in a:
                missing_id_count += 1
                continue
            processed_ids.add(f"{a['type']}_{a['id']}")
        
        if missing_id_count:
            self.logger.warning(f"[STEP 5/8] 有 {missing_id_count} 篇文章缺少 type/id，未加入已处理ID列表")
        
        self.logger.info(f"[STEP 5/8] 待处理ID数量: {len(processed_ids)}")
        return list(processed_ids)
    
    def run(self, mode: str = 'hot', **kwargs) -> List[Dict]:
        """运行搜集阶段"""
        if mode == 'hot':
            limit = kwargs.get('limit', 100)
            return self.collect_hot_content(limit)
        elif mode == 'keywords':
            keywords = kwargs.get('keywords')
            return self.collect_by_interest_keywords(keywords)
        elif mode == 'topics':
            topic_ids = kwargs.get('topic_ids', [])
            return self.collect_by_topics(topic_ids)
        else:
            self.logger.warning(f"未知搜集模式: {mode}")
            return []
