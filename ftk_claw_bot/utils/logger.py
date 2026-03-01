# -*- coding: utf-8 -*-
import sys
import threading
import time
import functools
from loguru import logger
from datetime import datetime
from typing import Callable, Any

from ..constants import Paths


def get_thread_info() -> str:
    current_thread = threading.current_thread()
    return f"T:{current_thread.ident}:{current_thread.name[:10]}"


def get_process_info() -> str:
    import os
    return f"P:{os.getpid()}"


def format_with_thread(record):
    record["extra"]["thread_id"] = get_thread_info()
    record["extra"]["process_id"] = get_process_info()
    return True


def setup_logger(app_name: str = "ftk_claw_bot", console: bool = True, level: str = "INFO"):
    log_dir = Paths.get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.remove()
    
    if console:
        logger.add(
            sys.stderr,
            level=level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{extra[thread_id]}</cyan> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>",
            colorize=True,
            filter=format_with_thread
        )
    
    timestamp = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{app_name}_{timestamp}.log"
    
    logger.add(
        str(log_file),
        rotation="10 MB",
        retention="7 days",
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[thread_id]} | {name}:{function}:{line} - {message}",
        encoding="utf-8",
        filter=format_with_thread
    )
    
    crash_log_file = log_dir / f"{app_name}_crash_{timestamp}.log"
    logger.add(
        str(crash_log_file),
        rotation="10 MB",
        retention="30 days",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[thread_id]} | {name}:{function}:{line} - {message}\n{exception}",
        encoding="utf-8",
        filter=format_with_thread,
        diagnose=True,
        backtrace=True
    )
    
    logger.info(f"日志系统初始化完成，日志目录: {log_dir}")
    logger.debug(f"线程信息: {get_thread_info()}, 进程信息: {get_process_info()}")
    
    return logger


def get_logger(name: str = None):
    if name:
        return logger.bind(name=name)
    return logger


def log_performance(operation_name: str = None):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            func_name = operation_name or func.__name__
            logger.debug(f"[PERF] 开始执行: {func_name}")
            try:
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.debug(f"[PERF] 完成执行: {func_name}, 耗时: {elapsed:.2f}ms")
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.error(f"[PERF] 执行异常: {func_name}, 耗时: {elapsed:.2f}ms, 错误: {type(e).__name__}: {e}")
                raise
        return wrapper
    return decorator


def log_async_performance(operation_name: str = None):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            func_name = operation_name or func.__name__
            logger.debug(f"[PERF] 开始异步执行: {func_name}")
            try:
                result = await func(*args, **kwargs)
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.debug(f"[PERF] 完成异步执行: {func_name}, 耗时: {elapsed:.2f}ms")
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.error(f"[PERF] 异步执行异常: {func_name}, 耗时: {elapsed:.2f}ms, 错误: {type(e).__name__}: {e}")
                raise
        return wrapper
    return decorator


class LogContext:
    def __init__(self, context_name: str, **extra_data):
        self.context_name = context_name
        self.extra_data = extra_data
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        logger.debug(f"[{self.context_name}] 进入上下文, 数据: {self.extra_data}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (time.perf_counter() - self.start_time) * 1000
        if exc_type:
            logger.error(f"[{self.context_name}] 上下文异常退出, 耗时: {elapsed:.2f}ms, 错误: {exc_type.__name__}: {exc_val}")
        else:
            logger.debug(f"[{self.context_name}] 正常退出上下文, 耗时: {elapsed:.2f}ms")
        return False
