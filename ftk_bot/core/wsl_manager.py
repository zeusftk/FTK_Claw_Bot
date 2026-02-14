import subprocess
import re
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass

from ..models import WSLDistro, DistroStatus


@dataclass
class CommandResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int


class WSLManager:
    def __init__(self):
        self._distros: Dict[str, WSLDistro] = {}
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running: bool = False
        self._callbacks: List[Callable] = []
        self._refresh_interval: float = 5.0

    def list_distros(self) -> List[WSLDistro]:
        result = self._run_wsl_command(["--list", "--verbose"])
        if not result.success:
            return []

        distros = self._parse_distro_list(result.stdout)
        self._distros = {d.name: d for d in distros}
        return distros

    def _run_wsl_command(self, args: List[str], distro: Optional[str] = None) -> CommandResult:
        cmd = ["wsl.exe"]
        if distro:
            cmd.extend(["-d", distro])
        cmd.extend(args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            return CommandResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode
            )
        except Exception as e:
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1
            )

    def _parse_distro_list(self, output: str) -> List[WSLDistro]:
        distros = []
        lines = output.strip().split("\n")

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            parts = re.split(r"\s+", line)
            if len(parts) >= 3:
                name = parts[0]
                is_default = name.startswith("*")
                if is_default:
                    name = name[1:].strip()

                version_str = parts[1]
                try:
                    version = int(version_str)
                except ValueError:
                    version = 2

                status_str = parts[2].lower() if len(parts) > 2 else "stopped"
                if "running" in status_str:
                    status = DistroStatus.RUNNING
                elif "stopped" in status_str:
                    status = DistroStatus.STOPPED
                else:
                    status = DistroStatus.ERROR

                distro = WSLDistro(
                    name=name,
                    version=version,
                    status=status,
                    is_default=is_default,
                    wsl_path=f"\\\\wsl$\\{name}"
                )
                distros.append(distro)

        return distros

    def start_distro(self, distro_name: str) -> bool:
        result = self._run_wsl_command(["--"], distro=distro_name)
        if result.success:
            self.list_distros()
            self._notify_callbacks()
        return result.success

    def stop_distro(self, distro_name: str) -> bool:
        result = self._run_wsl_command(["--terminate", distro_name])
        if result.success:
            self.list_distros()
            self._notify_callbacks()
        return result.success

    def shutdown_all(self) -> bool:
        result = self._run_wsl_command(["--shutdown"])
        if result.success:
            self.list_distros()
            self._notify_callbacks()
        return result.success

    def get_distro(self, distro_name: str) -> Optional[WSLDistro]:
        if distro_name not in self._distros:
            self.list_distros()
        return self._distros.get(distro_name)

    def get_distro_status(self, distro_name: str) -> Optional[DistroStatus]:
        distro = self.get_distro(distro_name)
        return distro.status if distro else None

    def execute_command(
        self,
        distro_name: str,
        command: str,
        timeout: int = 30
    ) -> CommandResult:
        cmd = ["wsl.exe", "-d", distro_name, "--", "bash", "-c", command]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout
            )
            return CommandResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                success=False,
                stdout="",
                stderr="Command timed out",
                return_code=-1
            )
        except Exception as e:
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1
            )

    def get_distro_resources(self, distro_name: str) -> Dict:
        result = self.execute_command(
            distro_name,
            "cat /proc/meminfo | head -5 && echo '---' && top -bn1 | head -3"
        )

        resources = {
            "memory_usage": 0,
            "memory_total": 0,
            "cpu_usage": 0.0,
        }

        if result.success:
            try:
                lines = result.stdout.split("\n")
                for line in lines:
                    if "MemTotal" in line:
                        match = re.search(r"(\d+)", line)
                        if match:
                            resources["memory_total"] = int(match.group(1)) * 1024
                    elif "MemAvailable" in line:
                        match = re.search(r"(\d+)", line)
                        if match:
                            available = int(match.group(1)) * 1024
                            resources["memory_usage"] = resources["memory_total"] - available
                    elif "%Cpu" in line:
                        match = re.search(r"(\d+\.?\d*)\s*id", line)
                        if match:
                            idle = float(match.group(1))
                            resources["cpu_usage"] = 100.0 - idle
            except Exception:
                pass

        return resources

    def get_distro_ip(self, distro_name: str) -> Optional[str]:
        result = self.execute_command(
            distro_name,
            "hostname -I 2>/dev/null | awk '{print $1}'"
        )
        if result.success and result.stdout.strip():
            return result.stdout.strip()
        return None

    def register_callback(self, callback: Callable):
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self):
        for callback in self._callbacks:
            try:
                callback(self._distros)
            except Exception:
                pass

    def start_monitoring(self, interval: float = 5.0):
        self._refresh_interval = interval
        self._monitor_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None

    def _monitor_loop(self):
        import time
        while self._monitor_running:
            try:
                self.list_distros()
                self._notify_callbacks()
            except Exception:
                pass
            time.sleep(self._refresh_interval)

    def convert_windows_to_wsl_path(self, windows_path: str) -> str:
        windows_path = windows_path.replace("\\", "/")
        if len(windows_path) >= 2 and windows_path[1] == ":":
            drive = windows_path[0].lower()
            rest = windows_path[2:]
            return f"/mnt/{drive}{rest}"
        return windows_path

    def convert_wsl_to_windows_path(self, wsl_path: str) -> str:
        if wsl_path.startswith("/mnt/"):
            parts = wsl_path[5:].split("/", 1)
            if len(parts) >= 1:
                drive = parts[0].upper()
                rest = parts[1] if len(parts) > 1 else ""
                return f"{drive}:\\{rest.replace('/', '\\')}"
        return wsl_path
