# -*- coding: utf-8 -*-
import threading
import time
import traceback
from enum import Enum
from typing import Callable, Dict, List, Any
from dataclasses import dataclass
from loguru import logger


def _get_thread_info() -> str:
    return f"T:{threading.current_thread().ident}:{threading.current_thread().name[:10]}"


class EventType(Enum):
    WSL_STATUS_CHANGED = "wsl_status_changed"
    WSL_DISTRO_STARTED = "wsl_distro_started"
    WSL_DISTRO_STOPPED = "wsl_distro_stopped"
    WSL_DISTRO_REMOVED = "wsl_distro_removed"
    WSL_DISTRO_IMPORTED = "wsl_distro_imported"
    WSL_LIST_CHANGED = "wsl_list_changed"
    
    CLAWBOT_STARTED = "clawbot_started"
    CLAWBOT_STOPPED = "clawbot_stopped"
    CLAWBOT_STATUS_CHANGED = "clawbot_status_changed"
    CLAWBOT_LOG = "clawbot_log"
    
    CONFIG_UPDATED = "config_updated"
    CONFIG_CREATED = "config_created"
    CONFIG_DELETED = "config_deleted"
    
    BRIDGE_CONNECTED = "bridge_connected"
    BRIDGE_DISCONNECTED = "bridge_disconnected"
    BRIDGE_STATUS_CHANGED = "bridge_status_changed"
    
    CHAT_CONNECTED = "chat_connected"
    CHAT_DISCONNECTED = "chat_disconnected"
    CHAT_MESSAGE = "chat_message"
    
    APP_STARTED = "app_started"
    APP_SHUTDOWN = "app_shutdown"
    APP_ERROR = "app_error"


@dataclass
class Event:
    type: EventType
    data: Dict[str, Any]
    source: str = ""


class EventBus:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._handlers: Dict[EventType, List[Callable]] = {}
                    cls._instance._once_handlers: Dict[EventType, List[Callable]] = {}
                    cls._instance._handler_lock = threading.Lock()
        return cls._instance
    
    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        with self._handler_lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            handler_name = getattr(handler, '__name__', str(handler))
            logger.debug(f"[EventBus] 订阅事件: {event_type.value}, 处理器: {handler_name}, "
                        f"当前订阅数: {len(self._handlers[event_type])}, 线程: {_get_thread_info()}")
    
    def subscribe_once(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        with self._handler_lock:
            if event_type not in self._once_handlers:
                self._once_handlers[event_type] = []
            self._once_handlers[event_type].append(handler)
            handler_name = getattr(handler, '__name__', str(handler))
            logger.debug(f"[EventBus] 订阅一次性事件: {event_type.value}, 处理器: {handler_name}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable) -> bool:
        with self._handler_lock:
            if event_type in self._handlers and handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
                handler_name = getattr(handler, '__name__', str(handler))
                logger.debug(f"[EventBus] 取消订阅: {event_type.value}, 处理器: {handler_name}")
                return True
            return False
    
    def publish(self, event_type: EventType, data: Dict[str, Any] = None, source: str = "") -> None:
        publish_start = time.perf_counter()
        event = Event(type=event_type, data=data or {}, source=source)
        
        with self._handler_lock:
            handlers = list(self._handlers.get(event_type, []))
            once_handlers = list(self._once_handlers.get(event_type, []))
            if event_type in self._once_handlers:
                self._once_handlers[event_type] = []
        
        total_handlers = len(handlers) + len(once_handlers)
        
        logger.debug(f"[EventBus] 发布事件: {event_type.value}, 数据: {data}, "
                    f"处理器数: {total_handlers}, 来源: {source}, 线程: {_get_thread_info()}")
        
        success_count = 0
        error_count = 0
        
        for handler in handlers:
            handler_name = getattr(handler, '__name__', str(handler))
            handler_start = time.perf_counter()
            try:
                handler(event)
                handler_elapsed = (time.perf_counter() - handler_start) * 1000
                success_count += 1
                if handler_elapsed > 100:
                    logger.warning(f"[EventBus] 处理器执行缓慢: {handler_name}, 耗时: {handler_elapsed:.2f}ms")
                else:
                    logger.debug(f"[EventBus] 处理器完成: {handler_name}, 耗时: {handler_elapsed:.2f}ms")
            except Exception as e:
                error_count += 1
                handler_elapsed = (time.perf_counter() - handler_start) * 1000
                logger.error(f"[EventBus] 处理器异常: {handler_name}, 耗时: {handler_elapsed:.2f}ms, "
                           f"错误: {type(e).__name__}: {e}")
                logger.error(f"[EventBus] 堆栈跟踪:\n{traceback.format_exc()}")
        
        for handler in once_handlers:
            handler_name = getattr(handler, '__name__', str(handler))
            handler_start = time.perf_counter()
            try:
                handler(event)
                handler_elapsed = (time.perf_counter() - handler_start) * 1000
                success_count += 1
                logger.debug(f"[EventBus] 一次性处理器完成: {handler_name}, 耗时: {handler_elapsed:.2f}ms")
            except Exception as e:
                error_count += 1
                logger.error(f"[EventBus] 一次性处理器异常: {handler_name}, "
                           f"错误: {type(e).__name__}: {e}")
                logger.error(f"[EventBus] 堆栈跟踪:\n{traceback.format_exc()}")
        
        publish_elapsed = (time.perf_counter() - publish_start) * 1000
        logger.debug(f"[EventBus] 事件发布完成: {event_type.value}, "
                    f"成功: {success_count}, 失败: {error_count}, 总耗时: {publish_elapsed:.2f}ms")
    
    def clear(self) -> None:
        with self._handler_lock:
            handler_count = sum(len(h) for h in self._handlers.values())
            once_count = sum(len(h) for h in self._once_handlers.values())
            self._handlers.clear()
            self._once_handlers.clear()
            logger.info(f"[EventBus] 清空所有处理器, 原有: {handler_count} 个常规, {once_count} 个一次性")


event_bus = EventBus()
