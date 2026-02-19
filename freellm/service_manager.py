"""
FreeLLM 服务管理器
整合 LLM 和 Router 服务管理
"""

from typing import Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .logger import get_logger
from .service_config import ServiceConfig, ServiceInstanceConfig, get_default_config_path
from .wsl_freellm_manager import WSLFreeLLMManager, ServiceStatus as LLMStatus

if TYPE_CHECKING:
    from .gui.simple_wsl_manager import SimpleWSLManager

_log = get_logger("service_manager")


class ServiceState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class ServiceInstanceState:
    """服务实例状态"""
    distro_name: str
    llm_status: ServiceState
    router_status: ServiceState
    llm_url: Optional[str] = None
    router_url: Optional[str] = None
    error: Optional[str] = None


class ServiceManager:
    """FreeLLM 服务管理器"""
    
    def __init__(
        self, 
        wsl_manager: "SimpleWSLManager",
        config_path: Optional[Path] = None
    ):
        self._wsl_manager = wsl_manager
        self._config_path = config_path or get_default_config_path()
        self._config = ServiceConfig.load(self._config_path)
        
        self._llm_manager = WSLFreeLLMManager(wsl_manager)
        self._router_services: Dict[str, "OpenAIRouterService"] = {}
        self._states: Dict[str, ServiceInstanceState] = {}
    
    def start_service(self, distro_name: str) -> ServiceInstanceState:
        """启动指定 WSL 分发的完整服务"""
        config = self._config.get_instance(distro_name)
        
        state = ServiceInstanceState(
            distro_name=distro_name,
            llm_status=ServiceState.STARTING,
            router_status=ServiceState.STOPPED
        )
        self._states[distro_name] = state
        
        try:
            llm_info = self._llm_manager.start_llm(
                distro_name,
                port=config.llm_port
            )
            
            if llm_info.status != LLMStatus.RUNNING:
                state.llm_status = ServiceState.ERROR
                state.error = llm_info.error or "LLM 服务启动失败"
                _log.error(f"Failed to start LLM for {distro_name}: {state.error}")
                return state
            
            state.llm_status = ServiceState.RUNNING
            state.llm_url = llm_info.url
            
            from .router import OpenAIRouterService
            router = OpenAIRouterService()
            
            if router.start_router(config.router_port, llm_info.url):
                state.router_status = ServiceState.RUNNING
                state.router_url = router.get_url()
                self._router_services[distro_name] = router
                _log.info(f"Service started for {distro_name}: LLM={llm_info.url}, Router={state.router_url}")
            else:
                state.router_status = ServiceState.ERROR
                state.error = "Router 服务启动失败"
                _log.error(f"Failed to start Router for {distro_name}")
            
        except Exception as e:
            state.llm_status = ServiceState.ERROR
            state.error = str(e)
            _log.exception(f"Exception starting service for {distro_name}: {e}")
        
        return state
    
    def stop_service(self, distro_name: str) -> bool:
        """停止指定 WSL 分发的服务"""
        self._llm_manager.stop_llm(distro_name)
        
        if distro_name in self._router_services:
            self._router_services[distro_name].stop_router()
            del self._router_services[distro_name]
        
        if distro_name in self._states:
            self._states[distro_name].llm_status = ServiceState.STOPPED
            self._states[distro_name].router_status = ServiceState.STOPPED
        
        _log.info(f"Service stopped for {distro_name}")
        return True
    
    def stop_all_services(self):
        """停止所有服务"""
        for distro_name in list(self._states.keys()):
            self.stop_service(distro_name)
        _log.info("All services stopped")
    
    def get_service_state(self, distro_name: str) -> Optional[ServiceInstanceState]:
        """获取服务状态"""
        return self._states.get(distro_name)
    
    def get_all_states(self) -> Dict[str, ServiceInstanceState]:
        """获取所有服务状态"""
        return self._states.copy()
    
    def get_config(self) -> ServiceConfig:
        """获取配置"""
        return self._config
    
    def save_config(self):
        """保存配置"""
        self._config.save(self._config_path)
    
    def update_instance_config(
        self, 
        distro_name: str, 
        llm_port: Optional[int] = None,
        router_port: Optional[int] = None,
        auto_start: Optional[bool] = None
    ):
        """更新实例配置"""
        config = self._config.get_instance(distro_name)
        if llm_port is not None:
            config.llm_port = llm_port
        if router_port is not None:
            config.router_port = router_port
        if auto_start is not None:
            config.auto_start = auto_start
        self.save_config()
    
    def restore_auto_start_services(self):
        """恢复配置为自动启动的服务"""
        for distro_name, instance in self._config.instances.items():
            if instance.auto_start:
                self.start_service(distro_name)
