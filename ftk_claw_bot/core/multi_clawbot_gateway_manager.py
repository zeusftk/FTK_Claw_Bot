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


class MultiClawbotGatewayManager:
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
            self._notify_global_status(distro_name, GatewayStatus.ERROR)
            return False

        if not distro.is_running:
            if not self._wsl_manager.start_distro(distro_name):
                logger.error(f"Failed to start distro {distro_name}")
                gateway.set_status(GatewayStatus.ERROR)
                self._notify_global_status(distro_name, GatewayStatus.ERROR)
                return False

        cmd = [
            "wsl.exe", "-d", distro_name, "-u", "root", "--",
            "bash", "-c",
            f"clawbot gateway --port {port}" + (" --verbose" if verbose else "") + (" --no-guardian" if no_guardian else "")
        ]

        try:
            gateway.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            monitor_thread = threading.Thread(
                target=self._monitor_gateway_process,
                args=(distro_name,),
                daemon=True
            )
            monitor_thread.start()

            time.sleep(2)

            if gateway.process.poll() is not None:
                stdout, stderr = gateway.process.communicate()
                logger.error(f"Gateway failed to start: {stderr}")
                gateway.set_status(GatewayStatus.ERROR)
                self._notify_global_status(distro_name, GatewayStatus.ERROR)
                return False

            gateway.set_status(GatewayStatus.RUNNING)
            self._notify_global_status(distro_name, GatewayStatus.RUNNING)
            logger.info(f"Clawbot gateway started for {distro_name} on port {port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start gateway: {e}")
            gateway.set_status(GatewayStatus.ERROR)
            self._notify_global_status(distro_name, GatewayStatus.ERROR)
            return False

    def _monitor_gateway_process(self, distro_name: str):
        gateway = self._gateways.get(distro_name)
        if not gateway or not gateway.process:
            return

        def read_output(pipe, log_type):
            try:
                for line in iter(pipe.readline, ""):
                    if line:
                        cleaned = line.replace("\x00", "").strip()
                        if cleaned:
                            logger.debug(f"[gateway:{distro_name}:{log_type}] {cleaned}")
            except Exception:
                pass

        stdout_thread = threading.Thread(
            target=read_output,
            args=(gateway.process.stdout, "stdout"),
            daemon=True
        )
        stderr_thread = threading.Thread(
            target=read_output,
            args=(gateway.process.stderr, "stderr"),
            daemon=True
        )
        stdout_thread.start()
        stderr_thread.start()

        gateway.process.wait()

        if gateway.status == GatewayStatus.RUNNING:
            gateway.set_status(GatewayStatus.STOPPED)
            self._notify_global_status(distro_name, GatewayStatus.STOPPED)

    def stop_gateway(self, distro_name: str) -> bool:
        gateway = self._gateways.get(distro_name)
        if not gateway:
            logger.warning(f"No gateway for {distro_name}")
            return True

        if gateway.status != GatewayStatus.RUNNING:
            logger.warning(f"Gateway for {distro_name} not running")
            return True

        gateway.set_status(GatewayStatus.STOPPING)
        self._notify_global_status(distro_name, GatewayStatus.STOPPING)

        try:
            if gateway.process:
                gateway.process.terminate()
                try:
                    gateway.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    gateway.process.kill()
                    gateway.process.wait()

            self._wsl_manager.execute_command(
                distro_name,
                "pkill -f 'clawbot gateway' || true"
            )

            self._port_manager.release_port(distro_name)
            gateway.set_status(GatewayStatus.STOPPED)
            self._notify_global_status(distro_name, GatewayStatus.STOPPED)
            logger.info(f"Clawbot gateway stopped for {distro_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop gateway: {e}")
            gateway.set_status(GatewayStatus.ERROR)
            self._notify_global_status(distro_name, GatewayStatus.ERROR)
            return False

    def stop_all_gateways(self) -> bool:
        success = True
        for distro_name in list(self._gateways.keys()):
            if not self.stop_gateway(distro_name):
                success = False
        return success

    def get_gateway_url(self, distro_name: str, use_localhost: bool = True) -> Optional[str]:
        gateway = self._gateways.get(distro_name)
        if not gateway or gateway.status != GatewayStatus.RUNNING:
            return None

        if use_localhost:
            return f"ws://localhost:{gateway.port}/ws"

        ip = self._wsl_manager.get_distro_ip(distro_name)
        if not ip:
            return None

        return f"ws://{ip}:{gateway.port}/ws"
