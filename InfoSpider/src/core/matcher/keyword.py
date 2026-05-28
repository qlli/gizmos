"""关键字匹配器 - 三层过滤链

Layer 1: 硬过滤（黑名单/垃圾词）
Layer 2: 质量评分（互动数据幂律分档）
Layer 3: 兴趣匹配（关键词命中 + 用户画像权重）
"""
import math
from typing import List

from loguru import logger

from .base import BaseMatcher, MatchResult
from ..crawler.base import CrawlItem
from ...models.user import UserProfile
from ...utils.config import get_config


class KeywordMatcher(BaseMatcher):
    """关键字匹配器
    
    从 ZhihuReader 的三层过滤器重构而来，支持多平台通用评分。
    """
    
    def __init__(self):
        config = get_config()
        
        # 黑名单配置（合并所有源的配置）
        self.blacklist_keywords: List[str] = []
        self.spam_keywords: List[str] = []
        self.blacklist_authors: List[str] = []
        
        # 从各源配置中合并黑名单
        for source in ["zhihu", "bilibili", "github"]:
            source_cfg = config.get_source_config(source)
            filters = source_cfg.get("filters", {})
            self.blacklist_keywords.extend(filters.get("blacklist_keywords", []))
            self.spam_keywords.extend(filters.get("spam_keywords", []))
            self.blacklist_authors.extend(filters.get("blacklist_authors", []))
        
        # 去重
        self.blacklist_keywords = list(set(self.blacklist_keywords))
        self.spam_keywords = list(set(self.spam_keywords))
        self.blacklist_authors = list(set(self.blacklist_authors))
        
        # 幂律分档阈值
        self.voteup_tiers = [10, 100, 1000, 10000, 100000]
        self.view_tiers = [1000, 10000, 100000, 1000000, 10000000]
    
    async def match(self, item: CrawlItem, user_profile: UserProfile) -> MatchResult:
        """三层匹配评估"""
        reasons = []
        
        # Layer 1: 硬过滤
        reject_reason = self._hard_filter(item)
        if reject_reason:
            return MatchResult(item=item, passed=False, score=0.0, reasons=[reject_reason])
        
        # Layer 2: 质量评分 (0-0.5)
        quality_score = self._quality_score(item)
        reasons.append(f"质量分={quality_score:.2f}")
        
        # Layer 3: 兴趣匹配 (0-0.5)
        interest_score = self._interest_score(item, user_profile)
        reasons.append(f"兴趣分={interest_score:.2f}")
        
        # 综合评分
        total_score = quality_score + interest_score
        passed = total_score >= 0.3  # 最低通过阈值
        
        if passed:
            reasons.append("PASS")
        else:
            reasons.append(f"REJECT (score={total_score:.2f} < 0.3)")
        
        return MatchResult(item=item, passed=passed, score=total_score, reasons=reasons)
    
    def _hard_filter(self, item: CrawlItem) -> str:
        """Layer 1: 硬过滤 - 返回拒绝原因或空字符串"""
        text = (item.title + " " + item.excerpt).lower()
        
        # 黑名单关键词
        for kw in self.blacklist_keywords:
            if kw in text:
                return f"黑名单关键词: {kw}"
        
        # 垃圾内容
        for kw in self.spam_keywords:
            if kw in text:
                return f"垃圾关键词: {kw}"
        
        # 黑名单作者
        if item.author in self.blacklist_authors:
            return f"黑名单作者: {item.author}"
        
        return ""
    
    def _quality_score(self, item: CrawlItem) -> float:
        """Layer 2: 质量评分 (0-0.5)
        
        基于互动数据的幂律分档评分
        """
        # 点赞/好评分 (0-0.25)
        vote_score = self._tier_score(item.voteup, self.voteup_tiers) * 0.25
        
        # 播放/浏览分 (0-0.15)
        view_score = self._tier_score(item.view_count, self.view_tiers) * 0.15
        
        # 评论分 (0-0.1)
        comment_score = min(item.comment_count / 500, 1.0) * 0.1
        
        return vote_score + view_score + comment_score
    
    def _interest_score(self, item: CrawlItem, user_profile: UserProfile) -> float:
        """Layer 3: 兴趣匹配 (0-0.5)
        
        基于用户画像兴趣标签的关键词命中评分
        """
        if not user_profile.interests.tags:
            return 0.25  # 无画像时给中间分
        
        text = (item.title + " " + item.excerpt + " " + item.author).lower()
        
        total_weight = 0.0
        hits = 0
        
        for tag, weight in user_profile.interests.tags.items():
            if tag.lower() in text:
                total_weight += weight
                hits += 1
        
        if hits == 0:
            return 0.1  # 无命中给底分
        
        # 归一化到 0-0.5
        score = min(total_weight / max(hits, 1), 1.0) * 0.4 + 0.1
        return min(score, 0.5)
    
    @staticmethod
    def _tier_score(value: int, tiers: List[int]) -> float:
        """幂律分档评分 (0-1)
        
        value 落在 tiers 中的哪个区间，给出对应的归一化分数。
        """
        if value <= 0:
            return 0.0
        
        for i, threshold in enumerate(tiers):
            if value < threshold:
                # 在区间内线性插值
                prev = tiers[i - 1] if i > 0 else 0
                ratio = (value - prev) / (threshold - prev)
                base = i / len(tiers)
                step = 1 / len(tiers)
                return base + ratio * step
        
        return 1.0  # 超过最高档
