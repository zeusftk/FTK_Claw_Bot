# -*- coding: utf-8 -*-
import subprocess
import threading
import time
from typing import Optional, Callable
from enum import Enum

from loguru import logger

from .wsl_manager import WSLManager


class GatewayStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class ClawbotGatewayManager:
    DEFAULT_PORT = 18888

    def __init__(self, wsl_manager: WSLManager, port: int = DEFAULT_PORT):
        self._wsl_manager = wsl_manager
        self._port = port
        self._status = GatewayStatus.STOPPED
        self._process: Optional[subprocess.Popen] = None
        self._status_callbacks: list[Callable] = []
        self._distro_name: Optional[str] = None

    @property
    def status(self) -> GatewayStatus:
        return self._status

    @property
    def port(self) -> int:
        return self._port

    @property
    def is_running(self) -> bool:
        return self._status == GatewayStatus.RUNNING

    def register_status_callback(self, callback: Callable):
        if callback not in self._status_callbacks:
            self._status_callbacks.append(callback)

    def unregister_status_callback(self, callback: Callable):
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)

    def _notify_status(self):
        for callback in self._status_callbacks:
            try:
                callback(self._status)
            except Exception:
                pass

    def get_wsl_ip(self, distro_name: str) -> Optional[str]:
        return self._wsl_manager.get_distro_ip(distro_name)

    def start_gateway(
        self,
        distro_name: str,
        verbose: bool = False,
        no_guardian: bool = True
    ) -> bool:
        if self._status == GatewayStatus.RUNNING:
            logger.warning("Gateway already running")
            return True

        self._distro_name = distro_name
        self._set_status(GatewayStatus.STARTING)

        distro = self._wsl_manager.get_distro(distro_name)
        if not distro:
            logger.error(f"Distro {distro_name} not found")
            self._set_status(GatewayStatus.ERROR)
            return False

        if not distro.is_running:
            if not self._wsl_manager.start_distro(distro_name):
                logger.error(f"Failed to start distro {distro_name}")
                self._set_status(GatewayStatus.ERROR)
                return False

        cmd = [
            "wsl.exe", "-d", distro_name, "-u", "root", "--",
            "bash", "-c",
            f"clawbot gateway --port {self._port}" + (" --verbose" if verbose else "") + (" --no-guardian" if no_guardian else "")
        ]

        try:
            self._process = subprocess.Popen(
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

            if self._process.poll() is not None:
                stdout, stderr = self._process.communicate()
                logger.error(f"Gateway failed to start: {stderr}")
                self._set_status(GatewayStatus.ERROR)
                return False

            self._set_status(GatewayStatus.RUNNING)
            logger.info(f"Clawbot gateway started on port {self._port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start gateway: {e}")
            self._set_status(GatewayStatus.ERROR)
            return False

    def _monitor_gateway_process(self, distro_name: str):
        if not self._process:
            return

        def read_output(pipe, log_type):
            try:
                for line in iter(pipe.readline, ""):
                    if line:
                        cleaned = line.replace("\x00", "").strip()
                        if cleaned:
                            logger.debug(f"[gateway:{log_type}] {cleaned}")
            except Exception:
                pass

        import threading as t
        stdout_thread = t.Thread(
            target=read_output,
            args=(self._process.stdout, "stdout"),
            daemon=True
        )
        stderr_thread = t.Thread(
            target=read_output,
            args=(self._process.stderr, "stderr"),
            daemon=True
        )
        stdout_thread.start()
        stderr_thread.start()

        self._process.wait()

        if self._status == GatewayStatus.RUNNING:
            self._set_status(GatewayStatus.STOPPED)

    def stop_gateway(self) -> bool:
        if self._status != GatewayStatus.RUNNING:
            logger.warning("Gateway not running")
            return True

        self._set_status(GatewayStatus.STOPPING)

        try:
            if self._process:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()

            if self._distro_name:
                self._wsl_manager.execute_command(
                    self._distro_name,
                    "pkill -f 'clawbot gateway' || true"
                )

            self._set_status(GatewayStatus.STOPPED)
            logger.info("Clawbot gateway stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop gateway: {e}")
            self._set_status(GatewayStatus.ERROR)
            return False

    def restart_gateway(self) -> bool:
        if not self._distro_name:
            logger.error("No distro configured for gateway")
            return False

        self.stop_gateway()
        time.sleep(1)
        return self.start_gateway(self._distro_name)

    def get_gateway_url(self, use_localhost: bool = True) -> Optional[str]:
        if self._status != GatewayStatus.RUNNING or not self._distro_name:
            return None

        if use_localhost:
            return f"ws://localhost:{self._port}/ws"
        
        ip = self.get_wsl_ip(self._distro_name)
        if not ip:
            return None

        return f"ws://{ip}:{self._port}/ws"
    
    def get_gateway_url_with_host(self, distro_name: str, host: str = "localhost") -> Optional[str]:
        """
        获取 gateway URL，使用指定的主机地址。
        如果 distro_name 不为空且 host 不是 localhost，则获取 WSL IP。
        """
        if host in ["localhost", "127.0.0.1", "0.0.0.0"]:
            ip = "localhost"
        else:
            if not distro_name:
                ip = "localhost"
            else:
                ip = self.get_wsl_ip(distro_name)
                if not ip:
                    ip = "localhost"
        
        return f"ws://{ip}:{self._port}/ws"

    def _set_status(self, status: GatewayStatus):
        self._status = status
        self._notify_status()
