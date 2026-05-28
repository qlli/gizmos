"""YAML 配置管理器 - 单例模式，支持点号路径访问"""
import os
from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger


class Config:
    """全局配置管理器
    
    支持分层加载：
    - config/default.yaml（全局默认）
    - config/sources/{source}.yaml（各源独立配置）
    """
    
    _instance: Optional['Config'] = None
    _data: dict = {}
    _source_configs: dict = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance
    
    def load(self, config_dir: Optional[str] = None):
        """加载配置文件"""
        if config_dir is None:
            config_dir = self._find_config_dir()
        
        config_path = Path(config_dir)
        
        # 加载全局默认配置
        default_file = config_path / "default.yaml"
        if default_file.exists():
            with open(default_file, 'r', encoding='utf-8') as f:
                self._data = yaml.safe_load(f) or {}
            logger.debug(f"已加载全局配置: {default_file}")
        
        # 加载各源配置
        sources_dir = config_path / "sources"
        if sources_dir.exists():
            for source_file in sources_dir.glob("*.yaml"):
                source_name = source_file.stem
                with open(source_file, 'r', encoding='utf-8') as f:
                    self._source_configs[source_name] = yaml.safe_load(f) or {}
                logger.debug(f"已加载源配置: {source_name}")
        
        self._loaded = True
    
    def _find_config_dir(self) -> str:
        """自动查找配置目录"""
        # 从当前文件向上查找 config 目录
        current = Path(__file__).resolve()
        for parent in [current.parent, current.parent.parent, current.parent.parent.parent]:
            config_dir = parent / "config"
            if config_dir.exists():
                return str(config_dir)
        
        # 从工作目录查找
        cwd_config = Path.cwd() / "config"
        if cwd_config.exists():
            return str(cwd_config)
        
        return str(Path(__file__).resolve().parent.parent.parent / "config")
    
    def get(self, key: str, default: Any = None) -> Any:
        """通过点号路径获取配置值
        
        示例: config.get('logging.level', 'INFO')
        """
        if not self._loaded:
            self.load()
        
        keys = key.split('.')
        value = self._data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value
    
    def get_source_config(self, source_name: str) -> dict:
        """获取指定源的完整配置"""
        if not self._loaded:
            self.load()
        return self._source_configs.get(source_name, {})
    
    def get_source(self, source_name: str, key: str, default: Any = None) -> Any:
        """获取指定源的配置项
        
        示例: config.get_source('zhihu', 'rate_limit.requests_per_minute', 20)
        """
        source_cfg = self.get_source_config(source_name)
        keys = key.split('.')
        value = source_cfg
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value
    
    @property
    def data(self) -> dict:
        """获取完整配置字典"""
        if not self._loaded:
            self.load()
        return self._data


def get_config() -> Config:
    """获取全局配置实例"""
    return Config()
