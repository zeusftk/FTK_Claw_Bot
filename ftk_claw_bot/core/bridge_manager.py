import subprocess
import threading
import time
from typing import Optional, Callable
from enum import Enum

from loguru import logger

from .wsl_manager import WSLManager


class AgentStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class BridgeManager:
    DEFAULT_WINDOWS_PORT = 9527

    def __init__(self, wsl_manager: WSLManager, windows_port: int = DEFAULT_WINDOWS_PORT):
        self._wsl_manager = wsl_manager
        self._windows_port = windows_port
        self._status = AgentStatus.STOPPED
        self._process: Optional[subprocess.Popen] = None
        self._status_callbacks: list[Callable] = []
        self._distro_name: Optional[str] = None

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def windows_port(self) -> int:
        return self._windows_port

    @property
    def is_running(self) -> bool:
        return self._status == AgentStatus.RUNNING

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

    def get_windows_ip_from_wsl(self, distro_name: str) -> Optional[str]:
        result = self._wsl_manager.execute_command(
            distro_name,
            "grep nameserver /etc/resolv.conf | awk '{print $2}'"
        )
        if result.success and result.stdout.strip():
            return result.stdout.strip()
        return None

    def get_wsl_ip(self, distro_name: str) -> Optional[str]:
        return self._wsl_manager.get_distro_ip(distro_name)

    def start_agent(
        self,
        distro_name: str,
        windows_host: Optional[str] = None,
        windows_port: Optional[int] = None
    ) -> bool:
        if self._status == AgentStatus.RUNNING:
            logger.warning("BridgeAgent already running")
            return True

        self._distro_name = distro_name
        self._set_status(AgentStatus.STARTING)

        distro = self._wsl_manager.get_distro(distro_name)
        if not distro:
            logger.error(f"Distro {distro_name} not found")
            self._set_status(AgentStatus.ERROR)
            return False

        if not distro.is_running:
            if not self._wsl_manager.start_distro(distro_name):
                logger.error(f"Failed to start distro {distro_name}")
                self._set_status(AgentStatus.ERROR)
                return False

        if windows_host is None:
            windows_host = self.get_windows_ip_from_wsl(distro_name)

        if not windows_host:
            logger.error("Could not determine Windows host IP")
            self._set_status(AgentStatus.ERROR)
            return False

        port = windows_port or self._windows_port

        cmd = [
            "wsl.exe", "-d", distro_name, "--",
            "bash", "-c",
            f"cd /mnt/c/bot_workspace/FTK_bot/FTK_bot_A && "
            f"python -m ftk_claw_bot.bridge.bridge_agent --host {windows_host} --port {port}"
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
                target=self._monitor_agent_process,
                args=(distro_name,),
                daemon=True
            )
            monitor_thread.start()

            time.sleep(2)

            if self._process.poll() is not None:
                stdout, stderr = self._process.communicate()
                logger.error(f"Agent failed to start: {stderr}")
                self._set_status(AgentStatus.ERROR)
                return False

            self._set_status(AgentStatus.RUNNING)
            logger.info(f"BridgeAgent started, connecting to {windows_host}:{port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start agent: {e}")
            self._set_status(AgentStatus.ERROR)
            return False

    def _monitor_agent_process(self, distro_name: str):
        if not self._process:
            return

        def read_output(pipe, log_type):
            try:
                for line in iter(pipe.readline, ""):
                    if line:
                        cleaned = line.replace("\x00", "").strip()
                        if cleaned:
                            logger.debug(f"[agent:{log_type}] {cleaned}")
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

        if self._status == AgentStatus.RUNNING:
            self._set_status(AgentStatus.STOPPED)

    def stop_agent(self) -> bool:
        if self._status != AgentStatus.RUNNING:
            logger.warning("Agent not running")
            return True

        self._set_status(AgentStatus.STOPPING)

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
                    "pkill -f 'bridge_agent' || true"
                )

            self._set_status(AgentStatus.STOPPED)
            logger.info("BridgeAgent stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop agent: {e}")
            self._set_status(AgentStatus.ERROR)
            return False

    def restart_agent(self) -> bool:
        if not self._distro_name:
            logger.error("No distro configured for agent")
            return False

        self.stop_agent()
        time.sleep(1)
        return self.start_agent(self._distro_name)

    def get_connection_info(self) -> Optional[dict]:
        if self._status != AgentStatus.RUNNING or not self._distro_name:
            return None

        windows_ip = self.get_windows_ip_from_wsl(self._distro_name)
        wsl_ip = self.get_wsl_ip(self._distro_name)

        return {
            "windows_host": windows_ip,
            "windows_port": self._windows_port,
            "wsl_ip": wsl_ip
        }

    def _set_status(self, status: AgentStatus):
        self._status = status
        self._notify_status()
