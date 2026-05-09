"""日志工具"""
import sys
from pathlib import Path
from loguru import logger as _logger


def setup_logger(log_file: str = None, level: str = "INFO", max_size_mb: int = 10, backup_count: int = 5):
    """配置日志"""
    _logger.remove()
    
    # 控制台输出
    _logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )
    
    # 文件输出
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        _logger.add(
            log_file,
            rotation=f"{max_size_mb} MB",
            retention=backup_count,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=level,
            encoding="utf-8"
        )
    
    return _logger


def get_logger(name: str = None):
    """获取日志记录器"""
    if name:
        return _logger.bind(name=name)
    return _logger
