from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional


class DistroStatus(Enum):
    RUNNING = "Running"
    STOPPED = "Stopped"
    INSTALLING = "Installing"
    ERROR = "Error"


@dataclass
class WSLDistro:
    name: str
    version: int
    status: DistroStatus
    is_default: bool = False
    wsl_path: str = ""
    cpu_usage: float = 0.0
    memory_usage: int = 0
    memory_total: int = 0
    disk_usage: int = 0
    disk_total: int = 0
    ip_address: Optional[str] = None
    running_since: Optional[datetime] = None

    @property
    def is_running(self) -> bool:
        return self.status == DistroStatus.RUNNING

    @property
    def memory_usage_percent(self) -> float:
        if self.memory_total == 0:
            return 0.0
        return (self.memory_usage / self.memory_total) * 100

    @property
    def disk_usage_percent(self) -> float:
        if self.disk_total == 0:
            return 0.0
        return (self.disk_usage / self.disk_total) * 100

    @property
    def running_duration(self) -> Optional[str]:
        if not self.running_since:
            return None
        delta = datetime.now() - self.running_since
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "status": self.status.value,
            "is_default": self.is_default,
            "wsl_path": self.wsl_path,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "memory_total": self.memory_total,
            "disk_usage": self.disk_usage,
            "disk_total": self.disk_total,
            "ip_address": self.ip_address,
            "running_since": self.running_since.isoformat() if self.running_since else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WSLDistro":
        return cls(
            name=data["name"],
            version=data["version"],
            status=DistroStatus(data["status"]),
            is_default=data.get("is_default", False),
            wsl_path=data.get("wsl_path", ""),
            cpu_usage=data.get("cpu_usage", 0.0),
            memory_usage=data.get("memory_usage", 0),
            memory_total=data.get("memory_total", 0),
            disk_usage=data.get("disk_usage", 0),
            disk_total=data.get("disk_total", 0),
            ip_address=data.get("ip_address"),
            running_since=datetime.fromisoformat(data["running_since"]) if data.get("running_since") else None,
        )
