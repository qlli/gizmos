"""汇总阶段"""
from typing import Dict, List
from datetime import datetime
from loguru import logger

from ..storage.excel_storage import ExcelStorage
from ..storage.json_storage import JSONStorage
from ..utils.config import get_config


class ArchiverStage:
    """汇总阶段 - 流水线第四阶段"""
    
    def __init__(self):
        self.excel_storage = ExcelStorage()
        self.json_storage = JSONStorage()
        self.config = get_config()
        self.logger = logger.bind(name="archiver")
    
    def archive_articles(self, articles: List[Dict], 
                         min_quality: int = 3,
                         is_stock: bool = True) -> List[Dict]:
        """存档高质量文章"""
        self.logger.info(f"[STEP 8/8] 开始归档高质量文章: 输入 {len(articles)} 篇, 质量门槛={min_quality}星")
        
        # 筛选高质量内容
        high_quality = []
        skipped_not_passed = 0
        below_quality = 0
        score_samples = []
        
        for article in articles:
            article_id = article.get('article_id') or f"{article.get('type', '')}_{article.get('id', '')}"
            if not article.get('passed', False):
                skipped_not_passed += 1
                continue
            
            analysis = article.get('analysis', {})
            quality_stars = analysis.get('quality_stars', analysis.get('内容质量', 0))
            
            # 质量门槛
            if isinstance(quality_stars, str):
                try:
                    quality_stars = float(quality_stars)
                except ValueError:
                    quality_stars = 0
            
            score_samples.append(f"{article_id}:{quality_stars}")
            if quality_stars >= min_quality:
                high_quality.append(article)
            else:
                below_quality += 1
        
        self.logger.info(
            f"[STEP 8/8] 归档筛选统计: not_passed={skipped_not_passed}, "
            f"below_quality={below_quality}, score_samples={score_samples[:10]}"
        )
        
        self.logger.info(f"[STEP 8/8] 筛选出 {len(high_quality)} 篇高质量文章（门槛: {min_quality}星）")
        
        # 存档到Excel
        if high_quality:
            sheet = 'high_quality' if is_stock else 'incremental'
            self.logger.info(f"[STEP 8/8] 准备写入Excel: count={len(high_quality)}, sheet={sheet}")
            self.excel_storage.save_articles(high_quality, sheet=sheet)
        else:
            self.logger.warning("[STEP 8/8] 没有符合归档条件的高质量文章，因此不会生成/更新 articles.xlsx")
        
        return high_quality
    
    def add_feedback(self, article_id: str, rating: int, 
                    comment: str = '', interested: bool = None) -> bool:
        """添加阅读反馈"""
        try:
            self.excel_storage.add_feedback(
                article_id=article_id,
                rating=rating,
                comment=comment,
                interested=interested
            )
            
            # 更新JSON存储
            articles = self.json_storage.load_processed_articles('analyzed')
            for article in articles:
                aid = f"{article.get('type', '')}_{article.get('id', '')}"
                if aid == article_id:
                    article['feedback'] = {
                        'rating': rating,
                        'comment': comment,
                        'interested': interested,
                        'reviewed_at': datetime.now().isoformat()
                    }
                    break
            
            self.json_storage.save_processed_articles(articles, 'reviewed')
            
            self.logger.info(f"反馈已保存: {article_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存反馈失败: {e}")
            return False
    
    def get_articles_to_review(self, limit: int = 20) -> List[Dict]:
        """获取待评价的文章"""
        # 从高质量文章中获取未评价的
        articles = self.excel_storage.load_articles('high_quality')
        
        to_review = []
        for article in articles:
            if not article.get('user_rating') or article.get('user_rating') == 0:
                to_review.append(article)
                if len(to_review) >= limit:
                    break
        
        return to_review
    
    def get_favorites(self) -> List[Dict]:
        """获取收藏（4星以上）"""
        return self.excel_storage.get_favorites()
    
    def generate_report(self) -> Dict:
        """生成报告"""
        high_quality = self.excel_storage.load_articles('high_quality')
        reviewed = self.excel_storage.load_articles('reviewed')
        favorites = self.excel_storage.get_favorites()
        
        # 统计评分分布
        rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for article in reviewed:
            rating = article.get('user_rating', 0)
            if rating in rating_dist:
                rating_dist[rating] += 1
        
        # 统计兴趣分布
        interested_count = sum(1 for a in reviewed if a.get('user_interested'))
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_archived': len(high_quality),
            'total_reviewed': len(reviewed),
            'total_favorites': len(favorites),
            'rating_distribution': rating_dist,
            'interested_count': interested_count,
            'storage_stats': self.json_storage.get_statistics()
        }
        
        self.logger.info(f"报告生成: {report}")
        return report
    
    def run(self, articles: List[ Dict] = None, 
            min_quality: int = 3) -> Dict:
        """运行汇总阶段"""
        if articles is None:
            articles = self.json_storage.load_processed_articles('analyzed')
        
        if not articles:
            self.logger.warning("没有待存档的文章")
            return {'archived': []}
        
        # 存档
        archived = self.archive_articles(articles, min_quality)
        
        # 生成报告
        report = self.generate_report()
        
        return {
            'archived': archived,
            'report': report
        }
