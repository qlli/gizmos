"""扩展阶段"""
from typing import Dict, List, Set
from loguru import logger
import time

from ..crawler.zhihu_client import ZhihuClient
from ..storage.json_storage import JSONStorage


class ExpanderStage:
    """扩展阶段 - 流水线第三阶段（优先级低）"""
    
    def __init__(self):
        self.client = ZhihuClient()
        self.storage = JSONStorage()
        self.logger = logger.bind(name="expander")
    
    def expand_by_author(self, articles: List[Dict], 
                        max_per_author: int = 5) -> List[Dict]:
        """扩展同一作者的其他内容"""
        # 收集作者ID
        author_ids: Set[str] = set()
        for article in articles:
            author_id = article.get('author_id')
            if author_id:
                author_ids.add(author_id)
        
        self.logger.info(f"开始扩展 {len(author_ids)} 位作者的内容")
        
        expanded = []
        for author_id in author_ids:
            try:
                # 获取该作者的文章和回答
                articles_batch = self.client.get_user_articles(author_id, limit=max_per_author)
                answers_batch = self.client.get_user_answers(author_id, limit=max_per_author)
                
                for item in articles_batch + answers_batch:
                    if 'title' in item:
                        item['source'] = 'author_expansion'
                        item['source_author_id'] = author_id
                        expanded.append(item)
                
                time.sleep(1)  # 避免请求过快
                
            except Exception as e:
                self.logger.warning(f"扩展作者 {author_id} 失败: {e}")
        
        self.logger.info(f"扩展完成，获得 {len(expanded)} 篇额外内容")
        return expanded
    
    def expand_by_question(self, articles: List[Dict],
                           max_per_question: int = 3) -> List[Dict]:
        """扩展同一问题的其他答案"""
        # 收集问题ID
        question_ids: Set[str] = set()
        for article in articles:
            question_id = article.get('question_id')
            if question_id:
                question_ids.add(question_id)
        
        self.logger.info(f"开始扩展 {len(question_ids)} 个问题的内容")
        
        expanded = []
        for question_id in question_ids:
            try:
                # 获取问题的其他高赞回答
                answers = self.client.get_question_answers(
                    question_id,
                    limit=max_per_question,
                    sort_by='voteup_count'
                )
                
                for item in answers:
                    item['source'] = 'question_expansion'
                    item['source_question_id'] = question_id
                    expanded.append(item)
                
                time.sleep(1)
                
            except Exception as e:
                self.logger.warning(f"扩展问题 {question_id} 失败: {e}")
        
        self.logger.info(f"扩展完成，获得 {len(expanded)} 篇额外内容")
        return expanded
    
    def expand_by_questioner(self, articles: List[Dict],
                            max_per_questioner: int = 3) -> List[Dict]:
        """扩展同一提问者的其他提问"""
        # 注意：这需要额外的信息来源
        # 简化实现：暂无
        self.logger.info("提问者扩展暂未实现")
        return []
    
    def run(self, articles: List[Dict] = None, 
            enable_author: bool = True,
            enable_question: bool = True) -> List[Dict]:
        """运行扩展阶段"""
        if articles is None:
            articles = self.storage.load_processed_articles('analyzed')
        
        if not articles:
            return []
        
        all_expanded = []
        
        # 扩展作者
        if enable_author:
            author_expanded = self.expand_by_author(articles)
            all_expanded.extend(author_expanded)
        
        # 扩展问题
        if enable_question:
            question_expanded = self.expand_by_question(articles)
            all_expanded.extend(question_expanded)
        
        # 保存扩展内容
        if all_expanded:
            self.storage.save_raw_articles(all_expanded, is_stock=False,
                                          filename='expanded.json')
        
        return all_expanded
