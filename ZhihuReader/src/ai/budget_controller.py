"""AI预算控制器"""
import json
import time
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict
from loguru import logger

from ..utils.config import get_config


class BudgetController:
    """Token预算控制器"""
    
    _instance: Optional['BudgetController'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        """初始化"""
        self.config = get_config()
        self.budget_config = self.config.ai_analysis.get('budget', {})
        
        self.daily_limit_usd = self.budget_config.get('daily_limit_usd', 20)
        self.alert_threshold = self.budget_config.get('alert_threshold_percent', 80)
        self.cost_per_1k_tokens = self.budget_config.get('cost_per_1k_tokens', {})
        
        # 存储路径
        self.storage_path = Path("data/processed/budget")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 加载当日消费
        self._load_today_usage()
    
    def _load_today_usage(self):
        """加载当日消费记录"""
        today = date.today().isoformat()
        filepath = self.storage_path / f"{today}.json"
        
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.today_cost = data.get('total_cost', 0.0)
                    self.today_tokens = data.get('total_tokens', 0)
            except Exception:
                self.today_cost = 0.0
                self.today_tokens = 0
        else:
            self.today_cost = 0.0
            self.today_tokens = 0
    
    def _save_today_usage(self):
        """保存当日消费记录"""
        today = date.today().isoformat()
        filepath = self.storage_path / f"{today}.json"
        
        data = {
            'date': today,
            'total_cost': self.today_cost,
            'total_tokens': self.today_tokens,
            'last_updated': datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, 
                       model: str = None) -> float:
        """计算成本"""
        if model is None:
            model = self.config.get('ai_analysis.openai.model', 'gpt-4o-mini')
        
        cost_rate = self.cost_per_1k_tokens.get(model, 0.00015)
        
        # 估算成本 (input + output)
        total_tokens = prompt_tokens + completion_tokens
        cost = (total_tokens / 1000) * cost_rate
        
        return cost
    
    def can_proceed(self, estimated_cost: float = None) -> bool:
        """检查是否可以继续执行"""
        remaining = self.daily_limit_usd - self.today_cost
        
        if estimated_cost and remaining < estimated_cost:
            logger.warning(f"预算不足: 剩余 ${remaining:.2f}, 预计消耗 ${estimated_cost:.2f}")
            return False
        
        if remaining <= 0:
            logger.warning("今日预算已耗尽")
            return False
        
        # 预警
        usage_percent = (self.today_cost / self.daily_limit_usd) * 100
        if usage_percent >= self.alert_threshold:
            logger.warning(f"预算使用已达 {usage_percent:.0f}%")
        
        return True
    
    def record_usage(self, prompt_tokens: int, completion_tokens: int, 
                    model: str = None) -> Dict:
        """记录使用量"""
        cost = self.calculate_cost(prompt_tokens, completion_tokens, model)
        
        self.today_cost += cost
        self.today_tokens += prompt_tokens + completion_tokens
        
        self._save_today_usage()
        
        return {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': prompt_tokens + completion_tokens,
            'cost': cost,
            'daily_cost_total': self.today_cost,
            'daily_limit': self.daily_limit_usd,
            'remaining': self.daily_limit_usd - self.today_cost
        }
    
    def get_status(self) -> Dict:
        """获取当前状态"""
        return {
            'date': date.today().isoformat(),
            'daily_cost': self.today_cost,
            'daily_limit': self.daily_limit_usd,
            'remaining': self.daily_limit_usd - self.today_cost,
            'usage_percent': (self.today_cost / self.daily_limit_usd) * 100 if self.daily_limit_usd > 0 else 0,
            'total_tokens': self.today_tokens
        }
    
    def reset(self):
        """重置（每日自动）"""
        self.today_cost = 0.0
        self.today_tokens = 0
        self._save_today_usage()
