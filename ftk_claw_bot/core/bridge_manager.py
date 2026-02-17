from typing import Optional, Callable

from loguru import logger

from .wsl_manager import WSLManager


class BridgeManager:
    def __init__(self, wsl_manager: WSLManager, windows_port: int = 9527):
        self._wsl_manager = wsl_manager
        self._windows_port = windows_port
        self._status_callbacks: list[Callable] = []

    @property
    def windows_port(self) -> int:
        return self._windows_port

    def update_port(self, port: int) -> None:
        self._windows_port = port

    def register_status_callback(self, callback: Callable):
        if callback not in self._status_callbacks:
            self._status_callbacks.append(callback)

    def unregister_status_callback(self, callback: Callable):
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)

    def get_windows_ip_from_wsl(self, distro_name: str) -> Optional[str]:
        result = self._wsl_manager.execute_command(
            distro_name,
            "grep nameserver /etc/resolv.conf | cut -d' ' -f2"
        )
        if result.success and result.stdout.strip():
            ip = result.stdout.strip()
            if ip and not ip.startswith("nameserver"):
                return ip
        return None

    def get_wsl_ip(self, distro_name: str) -> Optional[str]:
        return self._wsl_manager.get_distro_ip(distro_name)

    def get_connection_info(self, distro_name: str) -> Optional[dict]:
        windows_ip = self.get_windows_ip_from_wsl(distro_name)
        wsl_ip = self.get_wsl_ip(distro_name)

        return {
            "windows_host": windows_ip,
            "windows_port": self._windows_port,
            "wsl_ip": wsl_ip
        }
