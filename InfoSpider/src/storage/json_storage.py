"""JSON 存储 - 保存和加载采集结果"""
import json
from pathlib import Path
from datetime import datetime
from typing import List

from loguru import logger

from ..core.crawler.base import CrawlItem


class JSONStorage:
    """JSON 文件存储
    
    目录结构: data/raw/{source}/collected_{timestamp}.json
    """
    
    def __init__(self, base_dir: str = "data/raw"):
        self.base_dir = Path(base_dir)
    
    def save(self, items: List[CrawlItem], source: str = "mixed", tag: str = "") -> str:
        """保存采集结果
        
        Args:
            items: 采集结果列表
            source: 来源标识（用于目录分类）
            tag: 额外标签（用于文件名）
            
        Returns:
            保存的文件路径
        """
        save_dir = self.base_dir / source
        save_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"collected_{tag}_{timestamp}.json" if tag else f"collected_{timestamp}.json"
        file_path = save_dir / filename
        
        data = {
            "source": source,
            "count": len(items),
            "collected_at": datetime.now().isoformat(),
            "items": [item.to_dict() for item in items]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        abs_path = file_path.resolve()
        logger.info(f"[STORAGE] 已保存 {len(items)} 条结果 → {abs_path}")
        return str(abs_path)
    
    def load(self, file_path: str) -> List[CrawlItem]:
        """从文件加载采集结果"""
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"[STORAGE] 文件不存在: {file_path}")
            return []
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = [CrawlItem.from_dict(item) for item in data.get("items", [])]
        logger.info(f"[STORAGE] 已加载 {len(items)} 条结果 ← {path.resolve()}")
        return items
    
    def list_files(self, source: str = "") -> List[str]:
        """列出已保存的文件"""
        if source:
            search_dir = self.base_dir / source
        else:
            search_dir = self.base_dir
        
        if not search_dir.exists():
            return []
        
        files = sorted(search_dir.rglob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [str(f) for f in files]
