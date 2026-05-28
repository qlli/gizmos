"""用户画像数据模型"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

import yaml


@dataclass
class InterestGraph:
    """兴趣图谱"""
    tags: Dict[str, float] = field(default_factory=dict)  # 标签 → 权重(0-1)
    tag_relations: Dict[str, List[str]] = field(default_factory=dict)
    updated_at: str = ""
    
    def add_interest(self, tag: str, weight: float = 0.5):
        """添加/更新兴趣标签"""
        self.tags[tag] = max(0.0, min(1.0, weight))
        self.updated_at = datetime.now().isoformat()
    
    def remove_interest(self, tag: str):
        """移除兴趣标签"""
        self.tags.pop(tag, None)
        self.tag_relations.pop(tag, None)
    
    def decay(self, factor: float = 0.95):
        """兴趣衰减 - 所有标签权重按系数衰减"""
        for tag in self.tags:
            self.tags[tag] *= factor
        # 清理权重过低的标签
        self.tags = {k: v for k, v in self.tags.items() if v > 0.01}
    
    def boost(self, tag: str, delta: float = 0.1):
        """根据互动增强某标签"""
        current = self.tags.get(tag, 0.3)
        self.tags[tag] = min(1.0, current + delta)
        self.updated_at = datetime.now().isoformat()


@dataclass
class ContentPrefs:
    """内容偏好"""
    technical_depth: str = "medium"  # low / medium / high
    prefer_practical: bool = True
    prefer_industry_insights: bool = True
    preferred_languages: List[str] = field(default_factory=lambda: ["zh", "en"])
    min_content_length: int = 100
    max_content_length: int = 50000


@dataclass
class SourcePrefs:
    """来源偏好"""
    enabled_sources: List[str] = field(default_factory=lambda: ["zhihu", "bilibili"])
    source_weights: Dict[str, float] = field(default_factory=dict)  # 平台权重


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str = "default"
    username: str = ""
    profession: str = ""
    education: str = ""
    interests: InterestGraph = field(default_factory=InterestGraph)
    content_prefs: ContentPrefs = field(default_factory=ContentPrefs)
    source_prefs: SourcePrefs = field(default_factory=SourcePrefs)
    created_at: str = ""
    updated_at: str = ""
    
    def save(self, profiles_dir: str = "data/profiles"):
        """保存用户画像到YAML文件"""
        path = Path(profiles_dir)
        path.mkdir(parents=True, exist_ok=True)
        
        file_path = path / f"{self.user_id}.yaml"
        self.updated_at = datetime.now().isoformat()
        
        data = {
            "user_id": self.user_id,
            "username": self.username,
            "profession": self.profession,
            "education": self.education,
            "interests": {
                "tags": self.interests.tags,
                "tag_relations": self.interests.tag_relations,
                "updated_at": self.interests.updated_at
            },
            "content_prefs": {
                "technical_depth": self.content_prefs.technical_depth,
                "prefer_practical": self.content_prefs.prefer_practical,
                "prefer_industry_insights": self.content_prefs.prefer_industry_insights,
                "preferred_languages": self.content_prefs.preferred_languages,
                "min_content_length": self.content_prefs.min_content_length,
                "max_content_length": self.content_prefs.max_content_length
            },
            "source_prefs": {
                "enabled_sources": self.source_prefs.enabled_sources,
                "source_weights": self.source_prefs.source_weights
            },
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    
    @classmethod
    def load(cls, user_id: str = "default", profiles_dir: str = "data/profiles") -> 'UserProfile':
        """从YAML文件加载用户画像"""
        file_path = Path(profiles_dir) / f"{user_id}.yaml"
        
        if not file_path.exists():
            # 返回默认画像
            profile = cls(user_id=user_id, created_at=datetime.now().isoformat())
            return profile
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        interests_data = data.get("interests", {})
        interests = InterestGraph(
            tags=interests_data.get("tags", {}),
            tag_relations=interests_data.get("tag_relations", {}),
            updated_at=interests_data.get("updated_at", "")
        )
        
        prefs_data = data.get("content_prefs", {})
        content_prefs = ContentPrefs(
            technical_depth=prefs_data.get("technical_depth", "medium"),
            prefer_practical=prefs_data.get("prefer_practical", True),
            prefer_industry_insights=prefs_data.get("prefer_industry_insights", True),
            preferred_languages=prefs_data.get("preferred_languages", ["zh", "en"]),
            min_content_length=prefs_data.get("min_content_length", 100),
            max_content_length=prefs_data.get("max_content_length", 50000)
        )
        
        source_data = data.get("source_prefs", {})
        source_prefs = SourcePrefs(
            enabled_sources=source_data.get("enabled_sources", ["zhihu", "bilibili"]),
            source_weights=source_data.get("source_weights", {})
        )
        
        return cls(
            user_id=data.get("user_id", user_id),
            username=data.get("username", ""),
            profession=data.get("profession", ""),
            education=data.get("education", ""),
            interests=interests,
            content_prefs=content_prefs,
            source_prefs=source_prefs,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", "")
        )
