"""
简化 WSL 管理器 - 用于独立模式
不依赖 ftk_claw_bot，提供基本的 WSL 操作功能
"""

import subprocess
import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class WSLDistroInfo:
    """WSL 分发信息"""
    name: str
    version: int
    is_running: bool
    is_default: bool


class SimpleWSLManager:
    """简化的 WSL 管理器"""
    
    def list_distros(self) -> List[WSLDistroInfo]:
        """列出所有 WSL 分发"""
        try:
            result = subprocess.run(
                ["wsl.exe", "--list", "--verbose"],
                capture_output=True,
                text=True,
                encoding="utf-16-le",
                errors="replace",
                timeout=30
            )
            if result.returncode != 0:
                return []
            
            return self._parse_distro_list(result.stdout)
        except Exception:
            return []
    
    def _parse_distro_list(self, output: str) -> List[WSLDistroInfo]:
        """解析 wsl --list --verbose 输出"""
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
                is_running = "running" in status_str
                
                distros.append(WSLDistroInfo(
                    name=name,
                    version=version,
                    is_running=is_running,
                    is_default=is_default
                ))
        
        return distros
    
    def start_distro(self, name: str) -> bool:
        """启动 WSL 分发"""
        try:
            result = subprocess.run(
                ["wsl.exe", "-d", name, "-u", "root", "--exec", "echo", "started"],
                capture_output=True,
                text=True,
                encoding="utf-16-le",
                errors="replace",
                timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def stop_distro(self, name: str) -> bool:
        """停止 WSL 分发"""
        try:
            result = subprocess.run(
                ["wsl.exe", "--terminate", name],
                capture_output=True,
                text=True,
                encoding="utf-16-le",
                errors="replace",
                timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def execute_command(
        self, 
        distro_name: str, 
        command: str, 
        timeout: int = 30
    ) -> tuple:
        """在 WSL 中执行命令，返回 (success, stdout, stderr)"""
        cmd = ["wsl.exe", "-d", distro_name, "-u", "root", "--", "bash", "-c", command]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout
            )
            stdout = result.stdout.decode("utf-8", errors="replace").replace('\x00', '').strip()
            stderr = result.stderr.decode("utf-8", errors="replace").replace('\x00', '').strip()
            return result.returncode == 0, stdout, stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
    
    def get_distro_ip(self, distro_name: str) -> Optional[str]:
        """获取 WSL 分发的 IP 地址"""
        success, stdout, _ = self.execute_command(
            distro_name,
            "hostname -I 2>/dev/null | awk '{print $1}'"
        )
        if success and stdout.strip():
            return stdout.strip()
        return None
    
    def is_wsl_installed(self) -> bool:
        """检查 WSL 是否已安装"""
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
