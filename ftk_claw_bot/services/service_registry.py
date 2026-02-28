# -*- coding: utf-8 -*-
from typing import Protocol, Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum


class ServiceStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class ServiceInfo:
    id: str
    name: str
    description: str
    status: ServiceStatus
    port: Optional[int] = None
    error: Optional[str] = None


class LocalService(Protocol):
    """服务协议 - 无需继承，只需实现这些方法"""
    
    @property
    def id(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    
    def start(self) -> bool: ...
    def stop(self) -> bool: ...
    def get_status(self) -> ServiceInfo: ...
    def get_config(self) -> Dict[str, Any]: ...
    def set_config(self, config: Dict[str, Any]) -> bool: ...


class ServiceRegistry:
    """服务注册表 - 极简管理"""
    
    _services: Dict[str, LocalService] = {}
    _auto_start_services: List[str] = []
    
    @classmethod
    def register(cls, service: LocalService) -> None:
        cls._services[service.id] = service
    
    @classmethod
    def unregister(cls, service_id: str) -> None:
        if service_id in cls._services:
            del cls._services[service_id]
    
    @classmethod
    def get(cls, service_id: str) -> Optional[LocalService]:
        return cls._services.get(service_id)
    
    @classmethod
    def get_all(cls) -> List[LocalService]:
        return list(cls._services.values())
    
    @classmethod
    def start_all(cls) -> Dict[str, bool]:
        return {s.id: s.start() for s in cls._services.values()}
    
    @classmethod
    def stop_all(cls) -> Dict[str, bool]:
        return {s.id: s.stop() for s in cls._services.values()}
    
    @classmethod
    def clear(cls) -> None:
        cls._services.clear()
        cls._auto_start_services.clear()
    
    @classmethod
    def register_auto_start(cls, service_id: str) -> None:
        """注册服务为自启动"""
        if service_id not in cls._auto_start_services:
            cls._auto_start_services.append(service_id)
    
    @classmethod
    def get_auto_start_services(cls) -> List[str]:
        """获取自启动服务 ID 列表"""
        return cls._auto_start_services.copy()
    
    @classmethod
    def start_auto_start_services(cls, progress_callback=None) -> Dict[str, bool]:
        """启动所有自启动服务
        
        Args:
            progress_callback: 进度回调函数，接收 (service_id, service_name, index, total) 参数
        """
        results = {}
        total = len(cls._auto_start_services)
        
        for index, service_id in enumerate(cls._auto_start_services):
            service = cls.get(service_id)
            if service:
                if progress_callback:
                    progress_callback(service_id, service.name, index, total)
                
                try:
                    results[service_id] = service.start()
                except Exception as e:
                    results[service_id] = False
        
        return results


def register_service(service: LocalService) -> None:
    """便捷注册函数"""
    ServiceRegistry.register(service)
