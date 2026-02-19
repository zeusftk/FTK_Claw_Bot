"""
FreeLLM Client 日志模块
"""

import logging
import sys
from pathlib import Path


def setup_logger(name: str = "freellm", level: int = logging.INFO) -> logging.Logger:
    """设置日志器"""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


def get_logger(module_name: str = None) -> logging.Logger:
    """获取日志器"""
    if module_name:
        return logging.getLogger(f"freellm.{module_name}")
    return logging.getLogger("freellm")


logger = setup_logger()
