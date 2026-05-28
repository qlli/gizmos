"""日志工具 - loguru封装"""
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from .config import get_config


_initialized = False


def setup_logger(level: Optional[str] = None, log_file: Optional[str] = None):
    """初始化日志系统
    
    Args:
        level: 日志级别（覆盖配置文件）
        log_file: 日志文件路径（覆盖配置文件）
    """
    global _initialized
    if _initialized:
        return
    
    config = get_config()
    
    log_level = level or config.get('logging.level', 'INFO')
    log_path = log_file or config.get('logging.file', 'logs/infospider.log')
    max_size = config.get('logging.max_size_mb', 10)
    backup_count = config.get('logging.backup_count', 5)
    
    # 移除默认handler
    logger.remove()
    
    # 控制台输出
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # 文件输出
    log_dir = Path(log_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_path,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {name}:{function}:{line} - {message}",
        rotation=f"{max_size} MB",
        retention=backup_count,
        encoding="utf-8"
    )
    
    _initialized = True
    logger.info(f"日志系统已初始化 level={log_level} file={log_path}")


def get_logger(name: str = "infospider"):
    """获取命名日志实例"""
    return logger.bind(name=name)
