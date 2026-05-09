"""Excel存储模块"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger

from ..utils.config import get_config


class ExcelStorage:
    """Excel存档管理器"""
    
    def __init__(self, filepath: str = None):
        config = get_config()
        excel_config = config.storage.get('excel', {})
        
        if filepath:
            self.filepath = Path(filepath)
        else:
            self.filepath = Path(excel_config.get('archive_path', 'data/archive/articles.xlsx'))
        
        self.sheet_names = excel_config.get('sheet_names', {
            'high_quality': '高质量文章',
            'reviewed': '已评价',
            'favorites': '收藏'
        })
        
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Excel存档文件: {self.filepath.resolve()}")
    
    def _get_columns(self) -> List[str]:
        """获取Excel列定义"""
        return [
            'article_id',
            'type',
            'title',
            'url',
            'author',
            'author_id',
            'created_time',
            'voteup_count',
            'comment_count',
            'char_count',
            'excerpt',
            'summary',
            'quality_score',
            'quality_stars',
            'is_recommended',
            'has_ad',
            'user_rating',      # 用户评价（1-5星）
            'user_comment',    # 用户评语
            'user_interested', # 是否感兴趣
            'reviewed_at',
            'archived_at',
            'question_title',
            'question_id',
        ]
    
    def _article_to_row(self, article: Dict) -> Dict:
        """转换文章为行数据"""
        columns = self._get_columns()
        row = {col: '' for col in columns}
        
        # 基础信息
        row['article_id'] = f"{article.get('type', 'unknown')}_{article.get('id', '')}"
        row['type'] = article.get('type', '')
        row['title'] = article.get('title', '')
        row['url'] = article.get('url', '')
        row['author'] = article.get('author', '')
        row['author_id'] = article.get('author_id', '')
        row['created_time'] = article.get('created_time', '')
        row['voteup_count'] = article.get('voteup_count', 0)
        row['comment_count'] = article.get('comment_count', 0)
        row['char_count'] = article.get('char_count', 0)
        row['excerpt'] = article.get('excerpt', '')
        row['question_title'] = article.get('question_title', '')
        row['question_id'] = article.get('question_id', '')
        
        # 分析结果
        analysis = article.get('analysis', {})
        if analysis:
            row['summary'] = analysis.get('summary', analysis.get('主要内容摘要', ''))
            row['quality_score'] = analysis.get('quality_score', analysis.get('质量评分', 0))
            row['quality_stars'] = analysis.get('quality_stars', analysis.get('内容质量', 3))
            row['is_recommended'] = analysis.get('is_recommended', analysis.get('是否推荐阅读', True))
            row['has_ad'] = analysis.get('has_ad', analysis.get('是否包含广告', False))
        
        # 用户反馈
        feedback = article.get('feedback', {})
        if feedback:
            row['user_rating'] = feedback.get('rating', 0)
            row['user_comment'] = feedback.get('comment', '')
            row['user_interested'] = feedback.get('interested', False)
            row['reviewed_at'] = feedback.get('reviewed_at', datetime.now().isoformat())
        
        row['archived_at'] = datetime.now().isoformat()
        
        return row
    
    def save_articles(self, articles: List[Dict], sheet: str = 'high_quality'):
        """保存文章到Excel"""
        if not articles:
            logger.warning("没有文章需要保存")
            return
        
        sheet_name = self.sheet_names.get(sheet, sheet)
        
        # 转换为DataFrame
        rows = [self._article_to_row(article) for article in articles]
        df = pd.DataFrame(rows, columns=self._get_columns())
        
        # 追加模式
        if self.filepath.exists():
            try:
                existing_df = pd.read_excel(self.filepath, sheet_name=sheet_name)
                df = pd.concat([existing_df, df], ignore_index=True)
                # 去重
                df = df.drop_duplicates(subset=['article_id'], keep='last')
            except Exception:
                logger.warning(f"读取现有Excel失败，将覆盖")
        
        # 写入Excel
        logger.info(
            f"[STEP 8/8] 准备写入Excel: path={self.filepath.resolve()}, sheet={sheet_name}, rows={len(df)}"
        )
        with pd.ExcelWriter(self.filepath, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info(f"[STEP 8/8] Excel 写入完成: 保存 {len(articles)} 篇文章到 {self.filepath.resolve()}, Sheet: {sheet_name}")
    
    def load_articles(self, sheet: str = 'high_quality') -> List[Dict]:
        """从Excel加载文章"""
        if not self.filepath.exists():
            return []
        
        sheet_name = self.sheet_names.get(sheet, sheet)
        
        try:
            df = pd.read_excel(self.filepath, sheet_name=sheet_name)
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"读取Excel失败: {e}")
            return []
    
    def add_feedback(self, article_id: str, rating: int, comment: str = '',
                    interested: bool = None, sheet: str = 'high_quality'):
        """添加用户反馈"""
        articles = self.load_articles(sheet)
        
        for article in articles:
            if article.get('article_id') == article_id:
                article['user_rating'] = rating
                article['user_comment'] = comment
                article['user_interested'] = interested
                article['reviewed_at'] = datetime.now().isoformat()
        
        self.save_articles(articles, sheet)
    
    def get_favorites(self) -> List[Dict]:
        """获取收藏的文章"""
        articles = self.load_articles('reviewed')
        return [a for a in articles if a.get('user_rating', 0) >= 4]
    
    def export_to_json(self, output_path: str = None):
        """导出为JSON"""
        if output_path is None:
            output_path = str(self.filepath.with_suffix('.json'))
        
        all_articles = []
        for sheet in ['high_quality', 'reviewed', 'favorites']:
            all_articles.extend(self.load_articles(sheet))
        
        # 去重
        seen = set()
        unique = []
        for article in all_articles:
            aid = article.get('article_id')
            if aid not in seen:
                seen.add(aid)
                unique.append(article)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(unique, f, ensure_ascii=False, indent=2)
        
        logger.info(f"导出 {len(unique)} 篇文章到 {output_path}")
