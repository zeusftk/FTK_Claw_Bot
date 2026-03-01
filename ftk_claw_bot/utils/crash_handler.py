# -*- coding: utf-8 -*-
import sys
import threading
import traceback
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

from loguru import logger

from ..constants import Paths


class CrashHandler:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if CrashHandler._initialized:
            return
        CrashHandler._initialized = True
        
        # 使用统一的 user_data 目录
        from ftk_claw_bot.utils.user_data_dir import user_data
        self._crash_dir = user_data.crash_logs
        self._crash_dir.mkdir(parents=True, exist_ok=True)
        
        self._context: Dict[str, Any] = {}
        self._original_excepthook = None
        self._original_thread_excepthook = None
        
    def set_context(self, key: str, value: Any):
        self._context[key] = value
        
    def remove_context(self, key: str):
        if key in self._context:
            del self._context[key]
            
    def get_context(self) -> Dict[str, Any]:
        return self._context.copy()
    
    def _get_thread_info(self) -> Dict[str, Any]:
        threads_info = []
        for thread in threading.enumerate():
            threads_info.append({
                "name": thread.name,
                "ident": thread.ident,
                "daemon": thread.daemon,
                "is_alive": thread.is_alive()
            })
        return {
            "active_threads": len(threading.enumerate()),
            "threads": threads_info,
            "current_thread": {
                "name": threading.current_thread().name,
                "ident": threading.current_thread().ident
            }
        }
    
    def _get_memory_info(self) -> Dict[str, Any]:
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return {
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "cpu_percent": process.cpu_percent(),
                "num_threads": process.num_threads(),
                "num_handles": process.num_handles() if hasattr(process, 'num_handles') else None
            }
        except ImportError:
            return {"note": "psutil not installed"}
        except Exception as e:
            return {"error": str(e)}
    
    def _save_crash_report(self, exc_type, exc_value, exc_tb, thread_info: Optional[Dict] = None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        crash_file = self._crash_dir / f"crash_{timestamp}.json"
        
        crash_report = {
            "timestamp": datetime.now().isoformat(),
            "exception": {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value),
                "traceback": traceback.format_exception(exc_type, exc_value, exc_tb)
            },
            "thread_info": thread_info or self._get_thread_info(),
            "memory_info": self._get_memory_info(),
            "context": self._context,
            "process_id": os.getpid()
        }
        
        try:
            with open(crash_file, 'w', encoding='utf-8') as f:
                json.dump(crash_report, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"崩溃报告已保存: {crash_file}")
        except Exception as e:
            logger.error(f"保存崩溃报告失败: {e}")
            
        return crash_file
    
    def _log_crash(self, exc_type, exc_value, exc_tb, source: str = "main"):
        logger.critical(f"{'='*60}")
        logger.critical(f"[CRASH] 检测到未处理异常 (来源: {source})")
        logger.critical(f"[CRASH] 异常类型: {exc_type.__name__ if exc_type else 'Unknown'}")
        logger.critical(f"[CRASH] 异常消息: {exc_value}")
        logger.critical(f"[CRASH] 当前上下文: {self._context}")
        logger.critical(f"[CRASH] 线程信息: {self._get_thread_info()}")
        logger.critical("[CRASH] 堆栈跟踪:")
        for line in traceback.format_exception(exc_type, exc_value, exc_tb):
            logger.critical(line.rstrip())
        logger.critical(f"{'='*60}")
        
        self._save_crash_report(exc_type, exc_value, exc_tb)
    
    def _excepthook(self, exc_type, exc_value, exc_tb):
        self._log_crash(exc_type, exc_value, exc_tb, "main_thread")
        
        if self._original_excepthook:
            self._original_excepthook(exc_type, exc_value, exc_tb)
    
    def _thread_excepthook(self, args):
        exc_type = args.exc_type
        exc_value = args.exc_value
        exc_tb = args.exc_tb
        thread = args.thread
        
        thread_info = self._get_thread_info()
        thread_info["crashed_thread"] = {
            "name": thread.name if thread else "Unknown",
            "ident": thread.ident if thread else None
        }
        
        self._log_crash(exc_type, exc_value, exc_tb, f"thread:{thread.name if thread else 'unknown'}")
        
        if self._original_thread_excepthook:
            self._original_thread_excepthook(args)
    
    def install(self):
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._excepthook
        
        if hasattr(threading, 'excepthook'):
            self._original_thread_excepthook = threading.excepthook
            threading.excepthook = self._thread_excepthook
        
        logger.info("崩溃处理器已安装")
        logger.debug(f"崩溃报告目录: {self._crash_dir}")
        
    def uninstall(self):
        if self._original_excepthook:
            sys.excepthook = self._original_excepthook
            
        if self._original_thread_excepthook and hasattr(threading, 'excepthook'):
            threading.excepthook = self._original_thread_excepthook
            
        logger.info("崩溃处理器已卸载")


crash_handler = CrashHandler()


def install_crash_handler():
    crash_handler.install()
    

def uninstall_crash_handler():
    crash_handler.uninstall()


def set_crash_context(key: str, value: Any):
    crash_handler.set_context(key, value)


def remove_crash_context(key: str):
    crash_handler.remove_context(key)


def get_crash_context() -> Dict[str, Any]:
    return crash_handler.get_context()
