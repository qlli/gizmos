"""匹配器基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from ..crawler.base import CrawlItem
from ...models.user import UserProfile


@dataclass
class MatchResult:
    """匹配结果"""
    item: CrawlItem
    passed: bool          # 是否通过匹配
    score: float = 0.0    # 综合评分 (0-1)
    reasons: List[str] = field(default_factory=list)  # 评分理由


class BaseMatcher(ABC):
    """匹配器基类 - 所有匹配策略必须实现此接口"""
    
    @abstractmethod
    async def match(self, item: CrawlItem, user_profile: UserProfile) -> MatchResult:
        """对单个条目进行匹配评估
        
        Args:
            item: 待匹配的采集条目
            user_profile: 用户画像
            
        Returns:
            匹配结果（是否通过 + 评分 + 理由）
        """
    
    async def match_batch(self, items: List[CrawlItem], user_profile: UserProfile) -> List[MatchResult]:
        """批量匹配
        
        默认实现为逐个调用 match，子类可覆盖为批量优化版本。
        """
        results = []
        for item in items:
            result = await self.match(item, user_profile)
            results.append(result)
        return results
