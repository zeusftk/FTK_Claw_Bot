import subprocess
import re
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
import os

from loguru import logger

from ..models import WSLDistro, DistroStatus


@dataclass
class CommandResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int


def _validate_distro_name(name: str) -> bool:
    """验证分发名称是否有效"""
    return bool(re.match(r'^[a-zA-Z0-9_.-]+$', name))


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

    def is_wsl_installed(self) -> bool:
        try:
            result = subprocess.run(
                ["wsl.exe", "--status"],
                capture_output=True,
                text=True,
                encoding="utf-16-le",
                errors="replace",
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_available_distros(self) -> List[str]:
        try:
            result = subprocess.run(
                ["wsl.exe", "--list", "--online"],
                capture_output=True,
                text=True,
                encoding="utf-16-le",
                errors="replace",
                timeout=30
            )
            if result.returncode != 0:
                return []
            
            output = result.stdout.replace('\x00', '').strip()
            distros = []
            lines = output.split("\n")
            for line in lines:
                line = line.strip()
                if line and not line.startswith("NAME") and not line.startswith("以下是") and not line.startswith("The following"):
                    parts = re.split(r"\s+", line, 1)
                    if parts and parts[0]:
                        distros.append(parts[0])
            return distros
        except Exception:
            return []

    def install_distro(self, distro_name: str) -> bool:
        try:
            subprocess.run(
                ["wsl.exe", "--install", "-d", distro_name],
                capture_output=True,
                text=True,
                encoding="utf-16-le",
                errors="replace",
                timeout=300
            )
            return True
        except Exception as e:
            logger.error(f"Failed to install distro {distro_name}: {e}")
            return False

    def _run_wsl_command(self, args: List[str], distro: Optional[str] = None, timeout: int = 30) -> CommandResult:
        cmd = ["wsl.exe"]
        if distro:
            cmd.extend(["-d", distro, "-u", "root"])
        cmd.extend(args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-16-le",
                errors="replace",
                timeout=timeout
            )
            stdout = result.stdout.replace('\x00', '').strip()
            stderr = result.stderr.replace('\x00', '').strip()
            return CommandResult(
                success=result.returncode == 0,
                stdout=stdout,
                stderr=stderr,
                return_code=result.returncode
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"Command timed out after {timeout}s",
                return_code=-1
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

        for line in lines:
            line = line.strip()
            if not line or line.startswith("NAME"):
                continue

            is_default = line.startswith("*")
            if is_default:
                line = line[1:].strip()

            parts = re.split(r"\s+", line)
            if len(parts) >= 3:
                name = parts[0]
                if not name:
                    continue

                version_str = parts[-1]
                try:
                    version = int(version_str)
                except ValueError:
                    version = 2

                status_str = parts[-2].lower() if len(parts) > 1 else "stopped"
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
        try:
            cmd = ["wsl.exe", "-d", distro_name, "-u", "root", "--exec", "echo", "started"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-16-le",
                errors="replace",
                timeout=30
            )
            success = result.returncode == 0
            if success:
                self.list_distros()
                self._notify_callbacks()
            return success
        except Exception as e:
            logger.error(f"Failed to start distro {distro_name}: {e}")
            return False

    def stop_distro(self, distro_name: str) -> bool:
        try:
            cmd = ["wsl.exe", "--terminate", distro_name]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-16-le",
                errors="replace",
                timeout=30
            )
            success = result.returncode == 0
            if success:
                self.list_distros()
                self._notify_callbacks()
            return success
        except Exception as e:
            logger.error(f"Failed to stop distro {distro_name}: {e}")
            return False

    def shutdown_all(self) -> bool:
        try:
            cmd = ["wsl.exe", "--shutdown"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-16-le",
                errors="replace",
                timeout=30
            )
            success = result.returncode == 0
            if success:
                self.list_distros()
                self._notify_callbacks()
            return success
        except Exception as e:
            logger.error(f"Failed to shutdown all distros: {e}")
            return False

    def unregister_distro(self, distro_name: str) -> bool:
        try:
            cmd = ["wsl.exe", "--unregister", distro_name]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-16-le",
                errors="replace",
                timeout=60
            )
            success = result.returncode == 0
            if success:
                self.list_distros()
                self._notify_callbacks()
            return success
        except Exception as e:
            logger.error(f"Failed to unregister distro {distro_name}: {e}")
            return False

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
        cmd = ["wsl.exe", "-d", distro_name, "-u", "root", "--", "bash", "-c", command]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout
            )
            stdout = result.stdout.decode("utf-8", errors="replace").replace('\x00', '').strip()
            stderr = result.stderr.decode("utf-8", errors="replace").replace('\x00', '').strip()
            return CommandResult(
                success=result.returncode == 0,
                stdout=stdout,
                stderr=stderr,
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
                rest_windows = rest.replace("/", "\\")
                return f"{drive}:\\{rest_windows}"
        return wsl_path

    def get_distro_kernel_version(self, distro_name: str) -> Optional[str]:
        """Get kernel version of a distribution."""
        result = self.execute_command(distro_name, "uname -r")
        if result.success:
            return result.stdout.strip()
        return None

    def get_distro_uptime(self, distro_name: str) -> Optional[str]:
        """Get uptime of a distribution."""
        result = self.execute_command(
            distro_name, "cat /proc/uptime | awk '{print int($1)}'"
        )
        if result.success and result.stdout.strip():
            try:
                seconds = int(result.stdout.strip())
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                return f"{hours}h {minutes}m"
            except ValueError:
                pass
        return None

    def get_resource_usage(self, distro_name: str) -> Dict:
        """Get resource usage for a running distribution."""
        result = self.execute_command(
            distro_name,
            "cat /proc/meminfo | grep -E 'MemTotal|MemAvailable' && df -h / | tail -1 | awk '{print $5}' | tr -d '%'",
        )

        resources = {
            "cpu_percent": 0.0,
            "memory_used_mb": 0.0,
            "memory_total_mb": 0.0,
            "disk_percent": 0.0,
        }

        if result.success:
            try:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if "MemTotal" in line:
                        kb = int(line.split()[1])
                        resources["memory_total_mb"] = kb / 1024
                    elif "MemAvailable" in line:
                        kb = int(line.split()[1])
                        resources["memory_used_mb"] = resources["memory_total_mb"] - (kb / 1024)
                    elif line.strip().isdigit():
                        resources["disk_percent"] = float(line.strip())
            except Exception:
                pass

        return resources

    def set_default_distro(self, distro_name: str) -> bool:
        """设置 WSL 默认分发。
        
        Args:
            distro_name: 要设置为默认的分发名称
        
        Returns:
            bool: 操作是否成功
        """
        try:
            cmd = ["wsl.exe", "--set-default", distro_name]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-16-le",
                errors="replace",
                timeout=30
            )
            success = result.returncode == 0
            if success:
                self.list_distros()
                self._notify_callbacks()
            return success
        except Exception as e:
            logger.error(f"Failed to set default distro {distro_name}: {e}")
            return False

    def import_distro(
        self,
        tar_path: str,
        distro_name: str,
        install_location: Optional[str] = None
    ) -> CommandResult:
        """从 tar 文件导入 WSL 分发。
        
        Args:
            tar_path: tar 文件的完整路径
            distro_name: 要创建的分发名称
            install_location: 分发安装目录
        
        Returns:
            CommandResult: 包含执行结果的 CommandResult 对象
        """
        from loguru import logger
        
        logger.info(f"import_distro 开始: tar_path={tar_path}, distro_name={distro_name}")
        
        if not _validate_distro_name(distro_name):
            logger.error(f"分发名称无效: {distro_name}")
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"Invalid distro name: {distro_name}. Use only letters, numbers, underscore, and hyphen.",
                return_code=-1
            )

        if not Path(tar_path).exists():
            logger.error(f"tar 文件不存在: {tar_path}")
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"Tar file not found: {tar_path}",
                return_code=-1
            )
        
        if not os.path.exists(str(install_location)):
            # 自定义安装目录
            install_location = str(Path(os.getcwd()) / "WSL_installed" / distro_name)
        else:
            install_location = str(Path(install_location) / distro_name)

        logger.info(f"安装目录: {install_location}")
        Path(install_location).mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "wsl.exe",
            "--import",
            distro_name,
            install_location,
            tar_path,
            "--version", "2"
        ]
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-16-le",
                errors="replace",
                timeout=300
            )
            stdout = result.stdout.replace('\x00', '').strip()
            stderr = result.stderr.replace('\x00', '').strip()
            
            logger.info(f"命令执行完成: returncode={result.returncode}")
            logger.debug(f"stdout: {stdout}")
            if stderr:
                logger.warning(f"stderr: {stderr}")
            
            return CommandResult(
                success=result.returncode == 0,
                stdout=stdout,
                stderr=stderr,
                return_code=result.returncode
            )
        except subprocess.TimeoutExpired:
            logger.error("导入超时 (300s)")
            return CommandResult(
                success=False,
                stdout="",
                stderr="Import timed out (300s)",
                return_code=-1
            )
        except Exception as e:
            logger.error(f"导入过程异常: {e}")
            import traceback
            logger.error(f"详细堆栈: {traceback.format_exc()}")
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1
            )
