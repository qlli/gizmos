"""文章搜集器"""
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from loguru import logger

from .zhihu_client import ZhihuClient
from ..utils.config import get_config
from ..utils.logger import get_logger


class ArticleCollector:
    """文章搜集器 - 流水线第一阶段"""
    
    def __init__(self, client: ZhihuClient = None):
        # 如果未提供 client，创建一个（用于独立测试）
        self.client = client if client else ZhihuClient(headless=True)
        self.config = get_config()
        self.logger = get_logger("collector")
        
        # 加载配置
        filters = self.config.crawler.get('filters', {})
        self.min_upvote = filters.get('min_upvote', 5)
        self.min_answer_count = filters.get('min_answer_count', 1)
        self.min_char_count = filters.get('min_char_count', 100)
        self.blacklist_authors = filters.get('blacklist_authors', [])
        self.blacklist_keywords = filters.get('blacklist_keywords', [])
        self.spam_keywords = filters.get('spam_keywords', [])
        
        self.batch_size = self.config.get('crawler.collection.batch_size', 50)
        
        # 存储路径
        self.stock_path = Path(self.config.get('storage.json.stock_path', 'data/raw/stock'))
        self.incremental_path = Path(self.config.get('storage.json.incremental_path', 'data/raw/incremental'))
        self.stock_path.mkdir(parents=True, exist_ok=True)
        self.incremental_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(
            f"搜集器初始化: batch_size={self.batch_size}, min_upvote={self.min_upvote}, "
            f"min_answer_count={self.min_answer_count}, min_char_count={self.min_char_count}"
        )
        self.logger.info(
            f"搜集输出目录: stock={self.stock_path.resolve()}, incremental={self.incremental_path.resolve()}"
        )
    
    def _is_blacklisted_author(self, author_name: str) -> bool:
        """检查作者是否在黑名单"""
        return author_name in self.blacklist_authors
    
    def _contains_blacklist_keyword(self, title: str, content: str = "") -> bool:
        """检查是否包含黑名单关键词"""
        text = (title + " " + content).lower()
        return any(kw in text for kw in self.blacklist_keywords)
    
    def _contains_spam_keyword(self, title: str, content: str = "") -> bool:
        """检查是否包含垃圾关键词"""
        text = (title + " " + content).lower()
        return any(kw in text for kw in self.spam_keywords)
    
    def _basic_filter(self, article: Dict) -> bool:
        """基础过滤"""
        # 提取元信息
        title = article.get('title', '') or article.get('question', {}).get('title', '')
        
        # 点赞数过滤
        upvote_count = article.get('voteup_count', 0)
        if upvote_count < self.min_upvote:
            self.logger.debug(f"过滤低赞文章: {title} (赞: {upvote_count})")
            return False
        
        # 作者黑名单过滤
        author_name = ""
        if 'author' in article:
            author_name = article['author'].get('name', '') or article['author'].get('url_token', '')
        elif 'user' in article:
            author_name = article['user'].get('name', '') or article['user'].get('url_token', '')
        
        if self._is_blacklisted_author(author_name):
            self.logger.debug(f"过滤黑名单作者: {author_name}")
            return False
        
        # 关键词过滤
        content_preview = article.get('excerpt', '') or article.get('content', '')[:500]
        if self._contains_blacklist_keyword(title, content_preview):
            self.logger.debug(f"过滤含黑名单关键词: {title}")
            return False
        
        # 垃圾内容过滤
        if self._contains_spam_keyword(title, content_preview):
            self.logger.debug(f"过滤垃圾内容: {title}")
            return False
        
        return True
    
    def _extract_article_meta(self, item: Dict) -> Dict:
        """提取文章元信息"""
        meta = {
            'id': item.get('id', ''),
            'type': item.get('type', 'unknown'),
            'title': '',
            'url': '',
            'author': '',
            'author_id': '',
            'created_time': '',
            'updated_time': '',
            'voteup_count': 0,
            'comment_count': 0,
            'excerpt': '',
            'question_id': '',
            'question_title': '',
            'collected': False,
            'scraped_at': datetime.now().isoformat(),
        }
        
        # 文章类型
        if 'title' in item:  # 文章
            meta['type'] = 'article'
            meta['title'] = item.get('title', '')
            meta['url'] = f"https://zhuanlan.zhihu.com/p/{item.get('id', '')}"
            if 'author' in item:
                meta['author'] = item['author'].get('name', '')
                meta['author_id'] = item['author'].get('url_token', '')
        elif 'question' in item:  # 回答
            meta['type'] = 'answer'
            meta['question_id'] = item['question'].get('id', '')
            meta['question_title'] = item['question'].get('title', '')
            meta['url'] = f"https://www.zhihu.com/question/{meta['question_id']}/answer/{item.get('id', '')}"
            if 'author' in item:
                meta['author'] = item['author'].get('name', '')
                meta['author_id'] = item['author'].get('url_token', '')
        
        # 时间
        if 'created' in item:
            meta['created_time'] = datetime.fromtimestamp(item['created']).isoformat()
        elif 'created_time' in item:
            meta['created_time'] = item['created_time']
        
        if 'updated' in item:
            meta['updated_time'] = datetime.fromtimestamp(item['updated']).isoformat()
        
        # 互动数据
        meta['voteup_count'] = item.get('voteup_count', 0)
        meta['comment_count'] = item.get('comment_count', 0)
        
        # 摘要
        meta['excerpt'] = item.get('excerpt', '') or item.get('content', '')[:500]
        
        # 字符数
        content = item.get('content', '')
        if content:
            meta['char_count'] = len(content)
        else:
            meta['char_count'] = len(meta.get('excerpt', ''))
        
        return meta
    
    def collect_hot_feed(self, limit: int = 100) -> List[Dict]:
        """搜集热门内容"""
        self.logger.info(f"[STEP 4/8] 解析并过滤热门内容元数据，目标: {limit}")
        
        # 使用新的 ZhihuClient 方法
        articles_data = self.client.get_hot_content(limit=limit)
        self.logger.info(f"[STEP 4/8] 知乎热门接口返回原始条目: {len(articles_data)}")
        
        articles = []
        filtered_count = 0
        for item in articles_data:
            content_item = item.get('object', item) if isinstance(item, dict) else item
            if not isinstance(content_item, dict):
                filtered_count += 1
                continue
            
            if not self._basic_filter(content_item):
                filtered_count += 1
                continue
                
            meta = self._extract_article_meta(content_item)
            articles.append(meta)
        
        if articles:
            sample = articles[0]
            self.logger.info(
                f"[STEP 4/8] 解析样例: id={sample.get('id')}, type={sample.get('type')}, "
                f"title={sample.get('title') or sample.get('question_title')}, url={sample.get('url')}"
            )
        else:
            sample_keys = list(articles_data[0].keys()) if articles_data and isinstance(articles_data[0], dict) else None
            self.logger.warning(
                f"[STEP 4/8] 没有获得可保存文章，请检查接口返回、登录状态或过滤条件，raw_sample_keys={sample_keys}"
            )
        
        self.logger.info(f"[STEP 4/8] 解析完成: 原始 {len(articles_data)}, 过滤 {filtered_count}, 保留 {len(articles)}")
        return articles[:limit]
    
    def collect_by_keywords(self, keywords: List[str], per_keyword: int = 50) -> List[Dict]:
        """通过关键词搜集"""
        articles = []
        
        for keyword in keywords:
            self.logger.info(f"搜索关键词: {keyword}")
            
            # 使用新的 ZhihuClient.search() 方法
            results = self.client.search(keyword, limit=per_keyword)
            self.logger.info(f"关键词 {keyword} 原始返回: {len(results)}")
            
            before_count = len(articles)
            filtered_count = 0
            for item in results:
                content_item = item.get('object', item) if isinstance(item, dict) else item
                if not isinstance(content_item, dict):
                    filtered_count += 1
                    continue
                
                if not self._basic_filter(content_item):
                    filtered_count += 1
                    continue
                
                meta = self._extract_article_meta(content_item)
                articles.append(meta)
            
            self.logger.info(
                f"关键词 {keyword} 搜集完成: 保留 {len(articles) - before_count}, 过滤 {filtered_count}"
            )
            time.sleep(2)  # 关键词之间稍作延迟
        
        self.logger.info(f"关键词搜集总计: {len(articles)} 篇")
        return articles
    
    def collect_user_content(self, user_id: str, limit: int = 100) -> List[Dict]:
        """搜集指定用户的内容（暂未实现，需要用户主页 URL）"""
        self.logger.warning(f"collect_user_content 暂未实现")
        return []
    
    def collect_by_topics(self, topic_ids: List[str], per_topic: int = 50) -> List[Dict]:
        """通过话题搜集（暂未实现，需要话题 URL）"""
        self.logger.warning(f"collect_by_topics 暂未实现")
        return []
    
    def save_to_file(self, articles: List[Dict], is_stock: bool = True):
        """保存到文件"""
        path = self.stock_path if is_stock else self.incremental_path
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"collected_{timestamp}.json"
        
        filepath = path / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"保存 {len(articles)} 篇文章到 {filepath}")
        return filepath
    
    def deduplicate(self, articles: List[Dict]) -> List[Dict]:
        """去重"""
        seen_ids = set()
        unique = []
        
        for article in articles:
            article_id = f"{article['type']}_{article['id']}"
            if article_id not in seen_ids:
                seen_ids.add(article_id)
                unique.append(article)
        
        removed_count = len(articles) - len(unique)
        self.logger.info(f"去重完成: 输入 {len(articles)}, 移除重复 {removed_count}, 输出 {len(unique)}")
        return unique
