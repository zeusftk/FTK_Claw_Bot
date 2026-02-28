# -*- coding: utf-8 -*-
from typing import List, Dict, Any
from loguru import logger

from ...events import EventBus, EventType, Event


class WSLStateAwareMixin:
    _wsl_event_bus: EventBus = None
    _wsl_subscribed: bool = False
    
    def _init_wsl_state_aware(self):
        if self._wsl_subscribed:
            return
        self._wsl_event_bus = EventBus()
        self._subscribe_wsl_events()
        self._wsl_subscribed = True
        logger.debug(f"{self.__class__.__name__}: 已订阅 WSL 状态事件")
    
    def _subscribe_wsl_events(self):
        self._wsl_event_bus.subscribe(EventType.WSL_STATUS_CHANGED, self._on_wsl_status_changed)
        self._wsl_event_bus.subscribe(EventType.WSL_DISTRO_STARTED, self._on_wsl_distro_started)
        self._wsl_event_bus.subscribe(EventType.WSL_DISTRO_STOPPED, self._on_wsl_distro_stopped)
        self._wsl_event_bus.subscribe(EventType.WSL_DISTRO_REMOVED, self._on_wsl_distro_removed)
        self._wsl_event_bus.subscribe(EventType.WSL_DISTRO_IMPORTED, self._on_wsl_distro_imported)
        self._wsl_event_bus.subscribe(EventType.WSL_LIST_CHANGED, self._on_wsl_list_changed)
    
    def _unsubscribe_wsl_events(self):
        if not self._wsl_event_bus:
            return
        self._wsl_event_bus.unsubscribe(EventType.WSL_STATUS_CHANGED, self._on_wsl_status_changed)
        self._wsl_event_bus.unsubscribe(EventType.WSL_DISTRO_STARTED, self._on_wsl_distro_started)
        self._wsl_event_bus.unsubscribe(EventType.WSL_DISTRO_STOPPED, self._on_wsl_distro_stopped)
        self._wsl_event_bus.unsubscribe(EventType.WSL_DISTRO_REMOVED, self._on_wsl_distro_removed)
        self._wsl_event_bus.unsubscribe(EventType.WSL_DISTRO_IMPORTED, self._on_wsl_distro_imported)
        self._wsl_event_bus.unsubscribe(EventType.WSL_LIST_CHANGED, self._on_wsl_list_changed)
        self._wsl_subscribed = False
    
    def _on_wsl_status_changed(self, event: Event):
        self.on_wsl_status_changed(
            event.data.get("distros", []),
            event.data.get("running_count", 0),
            event.data.get("stopped_count", 0)
        )
    
    def _on_wsl_distro_started(self, event: Event):
        self.on_wsl_distro_started(event.data.get("distro_name", ""))
    
    def _on_wsl_distro_stopped(self, event: Event):
        self.on_wsl_distro_stopped(event.data.get("distro_name", ""))
    
    def _on_wsl_distro_removed(self, event: Event):
        self.on_wsl_distro_removed(event.data.get("distro_name", ""))
    
    def _on_wsl_distro_imported(self, event: Event):
        self.on_wsl_distro_imported(event.data.get("distro_name", ""))
    
    def _on_wsl_list_changed(self, event: Event):
        self.on_wsl_list_changed(
            event.data.get("distros", []),
            event.data.get("added", []),
            event.data.get("removed", [])
        )
    
    def on_wsl_status_changed(self, distros: List[Dict], running_count: int, stopped_count: int):
        pass
    
    def on_wsl_distro_started(self, distro_name: str):
        pass
    
    def on_wsl_distro_stopped(self, distro_name: str):
        pass
    
    def on_wsl_distro_removed(self, distro_name: str):
        pass
    
    def on_wsl_distro_imported(self, distro_name: str):
        pass
    
    def on_wsl_list_changed(self, distros: List[Dict], added: List[str], removed: List[str]):
        pass
