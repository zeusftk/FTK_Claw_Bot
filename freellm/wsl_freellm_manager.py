"""
WSL FreeLLM 服务管理器
在 WSL 分发中启动和管理 freellm serve 进程
"""

import time
import requests
import subprocess
from typing import Optional, Dict, Any, TYPE_CHECKING, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from .logger import get_logger

if TYPE_CHECKING:
    from .gui.simple_wsl_manager import SimpleWSLManager

_log = get_logger("wsl_llm")


class ServiceStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class FreeLLMServiceInfo:
    """FreeLLM 服务信息"""
    distro_name: str
    port: int
    status: ServiceStatus
    url: Optional[str] = None
    error: Optional[str] = None
    process: Optional[subprocess.Popen] = None


def _normalize_execute_result(result) -> Tuple[bool, str, str]:
    """规范化 execute_command 的返回结果，支持元组和 CommandResult 对象"""
    if isinstance(result, tuple):
        return result
    if hasattr(result, 'success'):
        return result.success, result.stdout or "", result.stderr or ""
    return bool(result), "", ""


class WSLFreeLLMManager:
    """WSL FreeLLM 服务管理器"""
    
    def __init__(self, wsl_manager: "SimpleWSLManager"):
        self._wsl_manager = wsl_manager
        self._services: Dict[str, FreeLLMServiceInfo] = {}
    
    def start_llm(
        self, 
        distro_name: str, 
        port: int = 20100,
        timeout: int = 30
    ) -> FreeLLMServiceInfo:
        """在 WSL 分发中启动 freellm serve"""
        
        if distro_name in self._services:
            info = self._services[distro_name]
            if info.status == ServiceStatus.RUNNING:
                return info
        
        info = FreeLLMServiceInfo(
            distro_name=distro_name,
            port=port,
            status=ServiceStatus.STARTING
        )
        self._services[distro_name] = info
        
        try:
            distros = self._wsl_manager.list_distros()
            distro = next((d for d in distros if d.name == distro_name), None)
            
            if not distro:
                info.status = ServiceStatus.ERROR
                info.error = f"WSL 分发 '{distro_name}' 不存在"
                _log.error(info.error)
                return info
            
            if not distro.is_running:
                if not self._wsl_manager.start_distro(distro_name):
                    info.status = ServiceStatus.ERROR
                    info.error = f"无法启动 WSL 分发 '{distro_name}'"
                    _log.error(info.error)
                    return info
            
            wsl_ip = self._wsl_manager.get_distro_ip(distro_name)
            if not wsl_ip:
                info.status = ServiceStatus.ERROR
                info.error = f"无法获取 WSL 分发 '{distro_name}' 的 IP 地址"
                _log.error(info.error)
                return info
            
            cmd = [
                "wsl.exe", "-d", distro_name, "-u", "root", "--",
                "opencode", "serve", "--port", str(port), "--hostname", "0.0.0.0"
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            info.process = process
            _log.info(f"Started freellm serve on {distro_name}:{port}, PID={process.pid}")
            
            llm_url = f"http://{wsl_ip}:{port}"
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                if process.poll() is not None:
                    info.status = ServiceStatus.ERROR
                    info.error = f"进程意外退出，返回码: {process.returncode}"
                    _log.error(info.error)
                    return info
                
                if self._check_llm_health(llm_url):
                    info.status = ServiceStatus.RUNNING
                    info.url = llm_url
                    _log.info(f"FreeLLM service ready: {llm_url}")
                    return info
                time.sleep(0.5)
            
            info.status = ServiceStatus.ERROR
            info.error = f"freellm serve 启动超时 ({timeout}s)"
            _log.error(info.error)
            
        except Exception as e:
            info.status = ServiceStatus.ERROR
            info.error = str(e)
            _log.exception(f"Failed to start freellm: {e}")
        
        return info
    
    def stop_llm(self, distro_name: str) -> bool:
        """停止 WSL 分发中的 freellm serve"""
        
        if distro_name not in self._services:
            return True
        
        info = self._services[distro_name]
        
        if info.process:
            try:
                info.process.terminate()
                info.process.wait(timeout=5)
            except Exception:
                try:
                    info.process.kill()
                except Exception:
                    pass
        
        cmd = f"pkill -f 'opencode serve.*--port {info.port}' || true"
        result = self._wsl_manager.execute_command(
            distro_name,
            cmd,
            timeout=10
        )
        success, _, _ = _normalize_execute_result(result)
        
        info.status = ServiceStatus.STOPPED
        info.url = None
        info.process = None
        
        _log.info(f"Stopped freellm service on {distro_name}")
        return success
    
    def is_llm_running(self, distro_name: str) -> bool:
        """检查 freellm serve 是否运行"""
        if distro_name not in self._services:
            return False
        
        info = self._services[distro_name]
        if not info.url:
            return False
        
        return self._check_llm_health(info.url)
    
    def get_service_info(self, distro_name: str) -> Optional[FreeLLMServiceInfo]:
        """获取服务信息"""
        return self._services.get(distro_name)
    
    def get_llm_url(self, distro_name: str) -> Optional[str]:
        """获取 freellm 服务 URL"""
        info = self._services.get(distro_name)
        return info.url if info and info.status == ServiceStatus.RUNNING else None
    
    def _check_llm_health(self, url: str) -> bool:
        """检查 freellm 服务健康状态"""
        try:
            resp = requests.get(f"{url}/global/health", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False
    
    def get_all_services(self) -> Dict[str, FreeLLMServiceInfo]:
        """获取所有服务信息"""
        return self._services.copy()
