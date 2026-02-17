import subprocess
import threading
import time
from typing import Optional, Callable, Dict
from enum import Enum

from loguru import logger

from .wsl_manager import WSLManager
from .port_manager import PortManager


class GatewayStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class GatewayInstance:
    def __init__(self, distro_name: str, port: int):
        self.distro_name = distro_name
        self.port = port
        self.status = GatewayStatus.STOPPED
        self.process: Optional[subprocess.Popen] = None
        self.status_callbacks: list[Callable] = []

    def register_status_callback(self, callback: Callable):
        if callback not in self.status_callbacks:
            self.status_callbacks.append(callback)

    def unregister_status_callback(self, callback: Callable):
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)

    def _notify_status(self):
        for callback in self.status_callbacks:
            try:
                callback(self.status)
            except Exception:
                pass

    def set_status(self, status: GatewayStatus):
        self.status = status
        self._notify_status()


class MultiNanobotGatewayManager:
    def __init__(self, wsl_manager: WSLManager, port_manager: Optional[PortManager] = None):
        self._wsl_manager = wsl_manager
        self._port_manager = port_manager or PortManager()
        self._gateways: Dict[str, GatewayInstance] = {}
        self._global_status_callbacks: list[Callable] = []

    @property
    def port_manager(self) -> PortManager:
        return self._port_manager

    def register_global_status_callback(self, callback: Callable):
        if callback not in self._global_status_callbacks:
            self._global_status_callbacks.append(callback)

    def unregister_global_status_callback(self, callback: Callable):
        if callback in self._global_status_callbacks:
            self._global_status_callbacks.remove(callback)

    def _notify_global_status(self, distro_name: str, status: GatewayStatus):
        for callback in self._global_status_callbacks:
            try:
                callback(distro_name, status)
            except Exception:
                pass

    def get_gateway(self, distro_name: str) -> Optional[GatewayInstance]:
        return self._gateways.get(distro_name)

    def get_all_gateways(self) -> Dict[str, GatewayInstance]:
        return self._gateways.copy()

    def start_gateway(
        self,
        distro_name: str,
        port: Optional[int] = None,
        verbose: bool = False,
        no_guardian: bool = True
    ) -> bool:
        if distro_name in self._gateways:
            gateway = self._gateways[distro_name]
            if gateway.status == GatewayStatus.RUNNING:
                logger.warning(f"Gateway for {distro_name} already running on port {gateway.port}")
                return True

        if port is None:
            port = self._port_manager.assign_port(distro_name)
            if port is None:
                logger.error(f"Failed to assign port for {distro_name}")
                return False
        else:
            if not self._port_manager.reserve_port(distro_name, port):
                logger.error(f"Failed to reserve port {port} for {distro_name}")
                return False

        gateway = GatewayInstance(distro_name, port)
        self._gateways[distro_name] = gateway

        gateway.set_status(GatewayStatus.STARTING)
        self._notify_global_status(distro_name, GatewayStatus.STARTING)

        distro = self._wsl_manager.get_distro(distro_name)
        if not distro:
            logger.error(f"Distro {distro_name} not found")
            gateway.set_status(GatewayStatus.ERROR)
            self._notify_global_status(distro_name, Gateway