"""采集任务数据模型"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    SEARCH = "search"
    TRENDING = "trending"
    PERIODIC = "periodic"


@dataclass
class CrawlTask:
    """采集任务"""
    task_id: str = ""
    user_id: str = "default"
    task_type: TaskType = TaskType.SEARCH
    sources: List[str] = field(default_factory=list)  # 目标平台列表
    keywords: List[str] = field(default_factory=list)
    limit: int = 20
    filters: Dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    
    def start(self):
        """标记任务开始"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now().isoformat()
    
    def complete(self, result_count: int = 0):
        """标记任务完成"""
        self.status = TaskStatus.COMPLETED
        self.result_count = result_count
        self.completed_at = datetime.now().isoformat()
    
    def fail(self, error: str):
        """标记任务失败"""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now().isoformat()
