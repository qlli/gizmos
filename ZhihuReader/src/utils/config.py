"""配置加载工具"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger


class Config:
    """配置管理器"""
    
    _instance: Optional['Config'] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """加载配置文件"""
        config_path = Path(__file__).parent.parent.parent / "config" / "setting.json"
        
        if not config_path.exists():
            logger.warning(f"配置文件不存在: {config_path}")
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            logger.info(f"配置加载成功: {config_path}")
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项，支持点号分隔的路径"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    @property
    def crawler(self) -> Dict[str, Any]:
        return self._config.get('crawler', {})
    
    @property
    def ai_analysis(self) -> Dict[str, Any]:
        return self._config.get('ai_analysis', {})
    
    @property
    def storage(self) -> Dict[str, Any]:
        return self._config.get('storage', {})
    
    @property
    def user_profile(self) -> Dict[str, Any]:
        return self._config.get('user_profile', {})
    
    def reload(self):
        """重新加载配置"""
        self._load_config()


def get_config() -> Config:
    """获取配置单例"""
    return Config()
