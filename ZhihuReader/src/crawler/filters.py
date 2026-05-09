"""内容过滤器"""
import re
from typing import Dict, List, Set, Optional
from datetime import datetime
from loguru import logger

from ..utils.config import get_config


class PowerLawFilter:
    """基于幂律分布的过滤器"""
    
    def __init__(self):
        config = get_config()
        thresholds = config.get('crawler.power_law_thresholds', {})
        
        self.upvote_tiers = thresholds.get('upvote_tiers', [10, 100, 1000, 5000])
        self.answer_tiers = thresholds.get('answer_tiers', [5, 20, 100, 500])
        self.char_tiers = thresholds.get('char_tiers', [500, 2000, 5000, 10000])
    
    def get_upvote_tier(self, count: int) -> int:
        """获取点赞数档位 (0-4)"""
        tier = 0
        for threshold in self.upvote_tiers:
            if count >= threshold:
                tier += 1
        return tier
    
    def get_answer_tier(self, count: int) -> int:
        """获取回答数档位 (0-4)"""
        tier = 0
        for threshold in self.answer_tiers:
            if count >= threshold:
                tier += 1
        return tier
    
    def get_char_tier(self, count: int) -> int:
        """获取字符数档位 (0-4)"""
        tier = 0
        for threshold in self.char_tiers:
            if count >= threshold:
                tier += 1
        return tier
    
    def is_extreme(self, article: Dict) -> bool:
        """判断是否为极端指标内容"""
        upvote_tier = self.get_upvote_tier(article.get('voteup_count', 0))
        char_tier = self.get_char_tier(article.get('char_count', 0))
        
        # 高档位（3或4）视为极端
        return upvote_tier >= 3 or char_tier >= 3


class ContentQualityFilter:
    """内容质量过滤器"""
    
    # AI生成内容特征
    AI_PATTERNS = [
        r'作为一名.*语言模型',
        r'我是一个.*模型',
        r'AI.*助手',
        r'基于.*深度学习',
        r'通过.*机器学习',
        r'利用.*自然语言处理',
        r'希望.*有所帮助',
        r'如果您.*问题',
        r'如果您.*需要',
        r'希望.*解答',
        r'AI\s*(对此|特此|谨此)',
    ]
    
    # 低质量内容模式
    LOW_QUALITY_PATTERNS = [
        r'点击.*查看.*全文',
        r'关注.*公众号',
        r'私信.*领取',
        r'扫码.*关注',
        r'回复.*获取',
        r'更多.*内容.*请.*',
    ]
    
    # 机械拼凑特征
    MECHANICAL_PATTERNS = [
        r'^第一[、，、.]第二[、，、.]第三',
        r'^\d+[.、]\d+[.、]\d+',
        r'(首先|其次|最后)。*?(首先|其次|最后)',
        r'(第一|第二|第三|第四)[章节部]',
    ]
    
    def __init__(self):
        self.config = get_config()
        filters = self.config.crawler.get('filters', {})
        
        self.spam_keywords = set(filters.get('spam_keywords', []))
        self.blacklist_keywords = set(filters.get('blacklist_keywords', []))
        self.blacklist_authors = set(filters.get('blacklist_authors', []))
        
        self.ai_patterns = [re.compile(p, re.IGNORECASE) for p in self.AI_PATTERNS]
        self.low_quality_patterns = [re.compile(p, re.IGNORECASE) for p in self.LOW_QUALITY_PATTERNS]
        self.mechanical_patterns = [re.compile(p, re.IGNORECASE) for p in self.MECHANICAL_PATTERNS]
    
    def is_ai_generated(self, content: str, title: str = "") -> bool:
        """判断是否可能为AI生成内容"""
        text = (title + " " + content)[:2000]  # 只检查前2000字符
        
        # 检查AI特征模式
        ai_pattern_matches = sum(1 for p in self.ai_patterns if p.search(text))
        if ai_pattern_matches >= 2:
            return True
        
        # 检查机械拼凑特征
        mechanical_matches = sum(1 for p in self.mechanical_patterns if p.search(text))
        if mechanical_matches >= 2:
            return True
        
        return False
    
    def is_low_quality(self, content: str, title: str = "") -> bool:
        """判断是否为低质量内容"""
        text = (title + " " + content)
        
        # 检查低质量模式
        for pattern in self.low_quality_patterns:
            if pattern.search(text):
                return True
        
        # 检查关键词
        content_lower = content.lower()
        for keyword in self.spam_keywords:
            if keyword in content_lower:
                return True
        
        # 检查内容重复度（简单实现）
        if len(content) > 100:
            first_half = content[:len(content)//2]
            second_half = content[len(content)//2:]
            if first_half == second_half or first_half in second_half:
                return True
        
        return False
    
    def filter_article(self, article: Dict, content: str = "") -> Dict:
        """过滤文章，返回过滤结果"""
        result = {
            'article_id': f"{article.get('type', 'unknown')}_{article.get('id', '')}",
            'title': article.get('title', ''),
            'author': article.get('author', ''),
            'passed': True,
            'reasons': [],
            'quality_score': 0,
        }
        
        title = article.get('title', '')
        
        # 检查作者黑名单
        if article.get('author', '') in self.blacklist_authors:
            result['passed'] = False
            result['reasons'].append('黑名单作者')
        
        # 检查关键词
        if self.spam_keywords.intersection(set(title.split())):
            result['passed'] = False
            result['reasons'].append('标题含垃圾关键词')
        
        # 检查AI生成
        if content and self.is_ai_generated(content, title):
            result['passed'] = False
            result['reasons'].append('疑似AI生成内容')
        
        # 检查低质量
        if content and self.is_low_quality(content, title):
            result['passed'] = False
            result['reasons'].append('低质量内容')
        
        # 计算质量分数
        if result['passed']:
            score = 0
            # 点赞加分
            upvote_tier = PowerLawFilter().get_upvote_tier(article.get('voteup_count', 0))
            score += upvote_tier * 10
            
            # 长度加分
            char_tier = PowerLawFilter().get_char_tier(len(content) if content else 0)
            score += char_tier * 5
            
            result['quality_score'] = score
        
        return result


class UserInterestFilter:
    """用户兴趣过滤器"""
    
    def __init__(self):
        self.config = get_config()
        profile = self.config.user_profile
        self.interests = profile.get('interests', [])
        self.preferences = profile.get('content_preferences', {})
    
    def get_interest_score(self, title: str, content: str = "", 
                          question_title: str = "") -> float:
        """计算兴趣匹配分数"""
        text = (title + " " + question_title + " " + content[:1000]).lower()
        
        score = 0.0
        for interest in self.interests:
            if interest.lower() in text:
                score += 1.0
        
        # 技术深度偏好
        if self.preferences.get('technical_depth') == 'high':
            technical_keywords = ['源码', '原理', '架构', '实现', '算法', '设计', 
                                '底层', '内核', '优化', '性能', '引擎']
            tech_count = sum(1 for kw in technical_keywords if kw in text)
            score += tech_count * 0.5
        
        return score
    
    def is_highly_relevant(self, article: Dict, content: str = "") -> bool:
        """判断是否高度相关"""
        score = self.get_interest_score(
            article.get('title', ''),
            content,
            article.get('question_title', '')
        )
        return score >= 2.0
