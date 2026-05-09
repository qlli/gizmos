"""分析阶段"""
from typing import Dict, List, Optional
from loguru import logger

from ..ai.openai_client import OpenAIClient
from ..ai.local_llm import LocalLLMClient
from ..ai.budget_controller import BudgetController
from ..crawler.zhihu_client import ZhihuClient
from ..crawler.filters import ContentQualityFilter, UserInterestFilter
from ..storage.json_storage import JSONStorage
from ..utils.config import get_config


class AnalyzerStage:
    """分析阶段 - 流水线第二阶段"""
    
    def __init__(self, zhihu_client: ZhihuClient = None):
        self.logger = logger.bind(name="analyzer")
        config = get_config()
        
        # 根据配置选择AI客户端
        ai_config = config.ai_analysis
        if ai_config.get('local_llm', {}).get('enabled'):
            self.ai_client = LocalLLMClient()
            if not self.ai_client.is_available():
                self.logger.warning("本地LLM不可用，尝试使用OpenAI")
                self.ai_client = OpenAIClient()
        else:
            self.ai_client = OpenAIClient()
        
        self.ai_available = getattr(self.ai_client, 'is_available', lambda: True)()
        if not self.ai_available:
            self.logger.warning("AI分析客户端不可用，将使用基础规则评分")
        
        self.budget = BudgetController()
        self.quality_filter = ContentQualityFilter()
        self.interest_filter = UserInterestFilter()
        self.zhihu_client = zhihu_client if zhihu_client else ZhihuClient()
        self._owns_zhihu_client = zhihu_client is None
        self._zhihu_client_started = zhihu_client is not None
        self.storage = JSONStorage()
    
    def _ensure_zhihu_client_started(self):
        """确保用于抓取正文的知乎客户端已启动"""
        if self._zhihu_client_started:
            return
        self.logger.info("分析阶段启动知乎客户端，用于获取文章正文")
        self.zhihu_client.__enter__()
        self._zhihu_client_started = True
    
    def close(self):
        """关闭分析阶段自有的知乎客户端"""
        if self._owns_zhihu_client and self._zhihu_client_started:
            self.zhihu_client.close()
            self._zhihu_client_started = False
    
    def fetch_content(self, article: Dict) -> str:
        """获取文章完整内容"""
        article_type = article.get('type', 'article')
        article_id = article.get('id', '')
        
        # 尝试从缓存加载
        cache_id = f"{article_type}_{article_id}"
        cached = self.storage.load_article_content(cache_id)
        if cached:
            self.logger.info(f"[STEP 6/8] 命中正文缓存: id={cache_id}, len={len(cached)}")
            return cached
        
        # 从知乎页面获取正文。搜集阶段已经保存了 url，这里必须传完整 URL，而不是 article_id。
        article_url = article.get('url', '')
        if not article_url and article_type == 'article' and article_id:
            article_url = f"https://zhuanlan.zhihu.com/p/{article_id}"
        
        if article_url:
            try:
                self._ensure_zhihu_client_started()
                content = self.zhihu_client.get_article_content(article_url)
                if content:
                    self.storage.save_article_content(cache_id, content)
                    self.logger.info(f"[STEP 6/8] 正文已缓存: id={cache_id}, len={len(content)}")
                    return content
                self.logger.warning(f"[STEP 6/8] 未能获取正文，使用摘要降级: id={cache_id}, url={article_url}")
            except Exception as e:
                self.logger.warning(f"[STEP 6/8] 获取正文异常，使用摘要降级: id={cache_id}, url={article_url}, error={e}")
        else:
            self.logger.warning(f"[STEP 6/8] 文章缺少 URL，使用摘要降级: id={cache_id}")
        
        return article.get('excerpt', '')
    
    def analyze_article(self, article: Dict) -> Dict:
        """分析单篇文章"""
        article_id = f"{article.get('type', 'unknown')}_{article.get('id', '')}"
        
        result = {
            'article_id': article_id,
            'title': article.get('title', ''),
            'author': article.get('author', ''),
            'passed': True,
            'reasons': [],
            'analysis': {}
        }
        
        # 检查预算
        if not self.budget.can_proceed():
            self.logger.warning("预算不足，跳过AI分析")
            result['passed'] = False
            result['reasons'].append('预算不足')
            return result
        
        # 获取完整内容
        content = self.fetch_content(article)
        self.logger.info(f"[STEP 7/8] 分析文章: id={article_id}, title={article.get('title') or article.get('question_title')}, content_len={len(content)}")
        
        # 快速过滤（不含AI调用）
        quality_result = self.quality_filter.filter_article(article, content)
        
        if not quality_result['passed']:
            result['passed'] = False
            result['reasons'].extend(quality_result['reasons'])
            self.logger.info(f"[STEP 7/8] 文章未通过基础质量过滤: id={article_id}, reasons={quality_result['reasons']}")
            return result
        
        # AI分析
        ai_result = None
        if self.ai_available:
            self.logger.info(f"[STEP 7/8] 发起AI分析: id={article_id}")
            ai_result = self.ai_client.analyze_content(
                title=article.get('title', ''),
                author=article.get('author', ''),
                content=content
            )
        else:
            self.logger.info(f"[STEP 7/8] 跳过AI分析，使用基础规则评分: id={article_id}")
        
        if ai_result:
            self.logger.info(f"[STEP 7/8] AI分析成功: id={article_id}, keys={list(ai_result.keys())}")
            result['analysis'] = ai_result
            
            # 提取推荐结果
            quality_stars = ai_result.get('quality_stars', ai_result.get('内容质量', 3))
            is_recommended = ai_result.get('is_recommended', ai_result.get('是否推荐阅读', True))
            has_ad = ai_result.get('has_ad', ai_result.get('是否包含广告', False))
            
            # 质量判断
            if quality_stars < 3 or not is_recommended or has_ad:
                result['passed'] = False
                if not is_recommended:
                    result['reasons'].append('AI判定不推荐')
                if has_ad:
                    result['reasons'].append('可能包含广告')
                if quality_stars < 3:
                    result['reasons'].append(f'质量评分低: {quality_stars}')
            
            # 兴趣匹配
            interest_score = self.interest_filter.get_interest_score(
                article.get('title', ''),
                content,
                article.get('question_title', '')
            )
            result['analysis']['interest_score'] = interest_score
            
        else:
            # AI分析失败或未配置，使用基础规则评分。
            # quality_score 的量级来自过滤器：点赞档位*10 + 长度档位*5，转换为 1-5 星。
            self.ai_available = getattr(self.ai_client, 'is_available', lambda: True)()
            basic_score = quality_result['quality_score']
            quality_stars = min(5, max(1, round(basic_score / 5, 1)))
            is_recommended = quality_stars >= 3
            self.logger.warning(
                f"[STEP 7/8] AI分析不可用，使用基础规则评分: id={article_id}, "
                f"basic_score={basic_score}, quality_stars={quality_stars}, is_recommended={is_recommended}"
            )
            result['analysis'] = {
                'quality_score': basic_score,
                'quality_stars': quality_stars,
                'is_recommended': is_recommended,
                'has_ad': False
            }
        
        return result
    
    def analyze_batch(self, articles: List[Dict], 
                      priority_key: str = 'interest_score') -> List[Dict]:
        """批量分析文章"""
        # 按优先级排序
        sorted_articles = sorted(
            articles,
            key=lambda x: x.get(priority_key, 0),
            reverse=True
        )
        
        analyzed = []
        skipped = []
        
        for i, article in enumerate(sorted_articles):
            self.logger.info(f"分析进度: {i+1}/{len(sorted_articles)}")
            
            # 预算检查
            if not self.budget.can_proceed():
                self.logger.warning("预算不足，停止分析")
                skipped.append(article)
                continue
            
            result = self.analyze_article(article)
            analyzed.append({**article, **result})
        
        # 分离通过和未通过的
        passed = [a for a in analyzed if a.get('passed', False)]
        failed = [a for a in analyzed if not a.get('passed', True)]
        
        self.logger.info(f"分析完成: 通过 {len(passed)}, 未通过 {len(failed)}, 跳过 {len(skipped)}")
        
        # 保存结果
        if analyzed:
            self.storage.save_processed_articles(analyzed, 'analyzed')
        
        return {
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'budget_status': self.budget.get_status()
        }
    
    def run(self, articles: List[Dict] = None, **kwargs) -> Dict:
        """运行分析阶段"""
        if articles is None:
            self.logger.info("未传入文章，准备从原始存储加载 stock 数据")
            articles = self.storage.load_raw_articles(is_stock=True)
        
        self.logger.info(f"分析阶段输入文章数量: {len(articles)}")
        
        if not articles:
            self.logger.warning("没有待分析的文章")
            return {'passed': [], 'failed': [], 'skipped': []}
        
        try:
            return self.analyze_batch(articles)
        finally:
            self.close()
