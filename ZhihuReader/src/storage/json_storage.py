"""JSON存储模块"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger

from ..utils.config import get_config


class JSONStorage:
    """JSON文件存储"""
    
    def __init__(self):
        config = get_config()
        json_config = config.storage.get('json', {})
        
        self.stock_path = Path(json_config.get('stock_path', 'data/raw/stock'))
        self.incremental_path = Path(json_config.get('incremental_path', 'data/raw/incremental'))
        self.processed_path = Path(json_config.get('processed_path', 'data/processed'))
        
        # 创建目录
        self.stock_path.mkdir(parents=True, exist_ok=True)
        self.incremental_path.mkdir(parents=True, exist_ok=True)
        self.processed_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "JSON存储目录: stock={}, incremental={}, processed={}",
            self.stock_path.resolve(),
            self.incremental_path.resolve(),
            self.processed_path.resolve()
        )
    
    def save_raw_articles(self, articles: List[Dict], is_stock: bool = True,
                         filename: str = None) -> Path:
        """保存原始搜集的文章"""
        path = self.stock_path if is_stock else self.incremental_path
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"collected_{timestamp}.json"
        
        filepath = path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'count': len(articles),
                    'type': 'stock' if is_stock else 'incremental'
                },
                'articles': articles
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"保存 {len(articles)} 篇文章到 {filepath.resolve()}")
        return filepath
    
    def load_raw_articles(self, filepath: str = None, is_stock: bool = True) -> List[Dict]:
        """加载原始文章"""
        if filepath:
            path = Path(filepath)
        else:
            # 加载最新文件
            path = self.stock_path if is_stock else self.incremental_path
            files = sorted(path.glob("collected_*.json"), key=lambda p: p.stat().st_mtime)
            logger.info(f"准备加载原始文章: dir={path.resolve()}, files={len(files)}")
            if not files:
                logger.warning(f"未找到原始文章文件: {path.resolve()}")
                return []
            path = files[-1]
        
        if not path.exists():
            logger.warning(f"原始文章文件不存在: {path.resolve()}")
            return []
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            articles = data.get('articles', [])
            logger.info(f"已加载原始文章: file={path.resolve()}, count={len(articles)}")
            return articles
    
    def save_processed_articles(self, articles: List[Dict], 
                                category: str = 'analyzed') -> Path:
        """保存处理后的文章"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{category}_{timestamp}.json"
        filepath = self.processed_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'count': len(articles),
                    'category': category
                },
                'articles': articles
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"保存 {len(articles)} 篇处理后文章到 {filepath.resolve()}")
        return filepath
    
    def load_processed_articles(self, category: str = None) -> List[Dict]:
        """加载处理后的文章"""
        if category:
            files = sorted(self.processed_path.glob(f"{category}_*.json"), 
                         key=lambda p: p.stat().st_mtime, reverse=True)
        else:
            files = sorted(self.processed_path.glob("*.json"), 
                         key=lambda p: p.stat().st_mtime, reverse=True)
        
        logger.info(
            f"准备加载处理后文章: dir={self.processed_path.resolve()}, category={category or 'all'}, files={len(files)}"
        )
        if not files:
            logger.warning(f"未找到处理后文章文件: {self.processed_path.resolve()}")
            return []
        
        all_articles = []
        seen_ids = set()
        
        for filepath in files[:5]:  # 最多加载最近5个文件
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for article in data.get('articles', []):
                    aid = f"{article.get('type', '')}_{article.get('id', '')}"
                    if aid not in seen_ids:
                        seen_ids.add(aid)
                        all_articles.append(article)
        
        return all_articles
    
    def save_article_content(self, article_id: str, content: str):
        """保存文章完整内容"""
        content_dir = self.processed_path / 'contents'
        content_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = content_dir / f"{article_id}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'article_id': article_id,
                'content': content,
                'fetched_at': datetime.now().isoformat()
            }, f, ensure_ascii=False)
    
    def load_article_content(self, article_id: str) -> Optional[str]:
        """加载文章完整内容"""
        filepath = self.processed_path / 'contents' / f"{article_id}.json"
        
        if not filepath.exists():
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('content')
    
    def get_statistics(self) -> Dict:
        """获取存储统计"""
        stats = {
            'stock_files': len(list(self.stock_path.glob("collected_*.json"))),
            'incremental_files': len(list(self.incremental_path.glob("collected_*.json"))),
            'processed_files': len(list(self.processed_path.glob("*.json"))),
            'content_files': len(list((self.processed_path / 'contents').glob("*.json")))
                       if (self.processed_path / 'contents').exists() else 0
        }
        
        return stats
