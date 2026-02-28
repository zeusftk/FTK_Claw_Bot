# -*- coding: utf-8 -*-
import time
from functools import wraps
from loguru import logger


def measure_time(operation_name: str = None):
    """测量函数执行时间的装饰器
    
    Args:
        operation_name: 操作名称，默认使用函数名
    
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.time() - start) * 1000
                if elapsed > 100:  # 只记录超过100ms的操作
                    logger.warning(f"[性能] {name} 耗时 {elapsed:.1f}ms")
                return result
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                logger.error(f"[性能] {name} 失败，耗时 {elapsed:.1f}ms: {e}")
                raise
        return wrapper
    return decorator


class PerformanceMonitor:
    """性能监控器
    
    用于手动监控代码块的执行时间
    """
    
    def __init__(self):
        self._operations = {}
    
    def start(self, name: str):
        """开始监控操作
        
        Args:
            name: 操作名称
        """
        self._operations[name] = time.time()
    
    def end(self, name: str) -> float:
        """结束监控操作
        
        Args:
            name: 操作名称
        
        Returns:
            执行时间（毫秒）
        """
        if name in self._operations:
            elapsed = (time.time() - self._operations[name]) * 1000
            del self._operations[name]
            if elapsed > 100:
                logger.warning(f"[性能] {name} 耗时 {elapsed:.1f}ms")
            return elapsed
        return 0
