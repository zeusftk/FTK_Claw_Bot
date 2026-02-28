# -*- coding: utf-8 -*-
from typing import Optional, Any, Callable, Dict
from threading import Lock
from loguru import logger


class Container:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._services: Dict[str, Any] = {}
                    cls._instance._factories: Dict[str, Callable] = {}
                    cls._instance._singletons: Dict[str, Any] = {}
        return cls._instance
    
    def register(self, name: str, instance: Any) -> None:
        self._services[name] = instance
        logger.debug(f"Container: 注册服务 {name}")
    
    def register_factory(self, name: str, factory: Callable[[], Any], singleton: bool = False) -> None:
        self._factories[name] = factory
        if singleton:
            self._singletons[name] = None
        logger.debug(f"Container: 注册工厂 {name} (singleton={singleton})")
    
    def get(self, name: str) -> Optional[Any]:
        if name in self._services:
            return self._services[name]
        
        if name in self._factories:
            if name in self._singletons:
                if self._singletons[name] is None:
                    self._singletons[name] = self._factories[name]()
                return self._singletons[name]
            return self._factories[name]()
        
        logger.warning(f"Container: 服务 {name} 未注册")
        return None
    
    def has(self, name: str) -> bool:
        return name in self._services or name in self._factories
    
    def remove(self, name: str) -> bool:
        removed = False
        if name in self._services:
            del self._services[name]
            removed = True
        if name in self._factories:
            del self._factories[name]
            removed = True
        if name in self._singletons:
            del self._singletons[name]
        return removed
    
    def clear(self) -> None:
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
    
    @property
    def wsl_manager(self):
        return self.get("wsl_manager")
    
    @wsl_manager.setter
    def wsl_manager(self, value):
        self.register("wsl_manager", value)
    
    @property
    def config_manager(self):
        return self.get("config_manager")
    
    @config_manager.setter
    def config_manager(self, value):
        self.register("config_manager", value)
    
    @property
    def clawbot_controller(self):
        return self.get("clawbot_controller")
    
    @clawbot_controller.setter
    def clawbot_controller(self, value):
        self.register("clawbot_controller", value)
    
    @property
    def monitor_service(self):
        return self.get("monitor_service")
    
    @monitor_service.setter
    def monitor_service(self, value):
        self.register("monitor_service", value)
    
    @property
    def windows_bridge(self):
        return self.get("windows_bridge")
    
    @windows_bridge.setter
    def windows_bridge(self, value):
        self.register("windows_bridge", value)
    
    @property
    def plugin_manager(self):
        return self.get("plugin_manager")
    
    @plugin_manager.setter
    def plugin_manager(self, value):
        self.register("plugin_manager", value)


container = Container()
