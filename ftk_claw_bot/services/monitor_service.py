import threading
import time
from typing import Callable, Dict, Optional
from datetime import datetime

from ..core import WSLManager, NanobotController
from ..models import DistroStatus, NanobotStatus


class MonitorService:
    def __init__(self, wsl_manager: WSLManager, nanobot_controller: NanobotController):
        self._wsl_manager = wsl_manager
        self._nanobot_controller = nanobot_controller
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._refresh_interval: float = 5.0
        self._callbacks: Dict[str, list] = {
            "wsl_status": [],
            "nanobot_status": [],
            "resources": [],
        }
        self._last_distro_status: Dict[str, DistroStatus] = {}
        self._last_nanobot_status: Dict[str, NanobotStatus] = {}

    def start(self, interval: float = 5.0):
        if self._running:
            return

        self._refresh_interval = interval
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None

    def _monitor_loop(self):
        while self._running:
            try:
                self._check_wsl_status()
                self._check_nanobot_status()
                self._check_resources()
            except Exception:
                pass

            time.sleep(self._refresh_interval)

    def _check_wsl_status(self):
        distros = self._wsl_manager.list_distros()

        for distro in distros:
            old_status = self._last_distro_status.get(distro.name)
            if old_status != distro.status:
                self._last_distro_status[distro.name] = distro.status
                self._notify_callbacks("wsl_status", {
                    "distro_name": distro.name,
                    "status": distro.status.value,
                    "is_running": distro.is_running,
                })

    def _check_nanobot_status(self):
        """Check nanobot instance status and notify callbacks of changes."""
        from ..models import NanobotStatus

        try:
            # Get all instances from controller
            instances = getattr(self._nanobot_controller, '_instances', {})

            for instance_name, instance in instances.items():
                old_status = self._last_nanobot_status.get(instance_name)
                current_status = instance.status

                # Only notify if status changed
                if old_status != current_status:
                    self._last_nanobot_status[instance_name] = current_status
                    self._notify_callbacks("nanobot_status", {
                        "instance_name": instance_name,
                        "status": current_status.value,
                        "is_running": current_status == NanobotStatus.RUNNING,
                        "pid": instance.pid,
                        "last_error": instance.last_error,
                    })
        except Exception:
            # Silently handle errors to prevent monitor loop from crashing
            pass

    def _check_resources(self):
        for distro_name, status in self._last_distro_status.items():
            if status == DistroStatus.RUNNING:
                try:
                    resources = self._wsl_manager.get_distro_resources(distro_name)
                    ip = self._wsl_manager.get_distro_ip(distro_name)

                    self._notify_callbacks("resources", {
                        "distro_name": distro_name,
                        "cpu_usage": resources.get("cpu_usage", 0.0),
                        "memory_usage": resources.get("memory_usage", 0),
                        "memory_total": resources.get("memory_total", 0),
                        "ip_address": ip,
                        "timestamp": datetime.now().isoformat(),
                    })
                except Exception:
                    pass

    def register_callback(self, event_type: str, callback: Callable):
        if event_type in self._callbacks:
            if callback not in self._callbacks[event_type]:
                self._callbacks[event_type].append(callback)

    def unregister_callback(self, event_type: str, callback: Callable):
        if event_type in self._callbacks:
            if callback in self._callbacks[event_type]:
                self._callbacks[event_type].remove(callback)

    def _notify_callbacks(self, event_type: str, data: dict):
        if event_type in self._callbacks:
            for callback in self._callbacks[event_type]:
                try:
                    callback(data)
                except Exception:
                    pass

    @property
    def is_running(self) -> bool:
        return self._running

    def set_refresh_interval(self, interval: float):
        self._refresh_interval = max(1.0, interval)
