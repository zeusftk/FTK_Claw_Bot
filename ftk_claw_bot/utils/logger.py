# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from loguru import logger
from datetime import datetime
from ..constants import Paths


def setup_logger(app_name: str = "ftk_claw_bot", console: bool = True, level: str = "INFO"):
    log_dir = Paths.get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.remove()
    
    if console:
        logger.add(
            sys.stderr,
            level=level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True
        )
    
    timestamp = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{app_name}_{timestamp}.log"
    
    logger.add(
        str(log_file),
        rotation="10 MB",
        retention="7 days",
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8"
    )
    
    logger.info(f"日志系统初始化完成，日志目录: {log_dir}")
    
    return logger


def get_logger(name: str = None):
    if name:
        return logger.bind(name=name)
    return logger
