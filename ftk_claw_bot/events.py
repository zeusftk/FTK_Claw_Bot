# -*- coding: utf-8 -*-
from enum import Enum
from typing import Callable, Dict, List, Any
from dataclasses import dataclass
from loguru import logger


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
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers: Dict[EventType, List[Callable]] = {}
            cls._instance._once_handlers: Dict[EventType, List[Callable]] = {}
        return cls._instance
    
    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"EventBus: 订阅事件 {event_type.value}")
    
    def subscribe_once(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        if event_type not in self._once_handlers:
            self._once_handlers[event_type] = []
        self._once_handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: EventType, handler: Callable) -> bool:
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            return True
        return False
    
    def publish(self, event_type: EventType, data: Dict[str, Any] = None, source: str = "") -> None:
        event = Event(type=event_type, data=data or {}, source=source)
        logger.debug(f"EventBus: 发布事件 {event_type.value}, 数据: {data}")
        
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"EventBus: 处理事件 {event_type.value} 时出错: {e}")
        
        once_handlers = self._once_handlers.get(event_type, [])
        if once_handlers:
            for handler in once_handlers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"EventBus: 处理一次性事件 {event_type.value} 时出错: {e}")
            self._once_handlers[event_type] = []
    
    def clear(self) -> None:
        self._handlers.clear()
        self._once_handlers.clear()


event_bus = EventBus()
