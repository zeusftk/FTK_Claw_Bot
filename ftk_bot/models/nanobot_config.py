from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict
import json


class NanobotStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    ERROR = "error"


@dataclass
class NanobotConfig:
    name: str
    distro_name: str
    workspace: str = ""
    config_path: str = ""
    provider: str = "openrouter"
    model: str = "anthropic/claude-sonnet-4-20250529"
    api_key: str = ""
    skills_dir: str = ""
    log_level: str = "INFO"
    enable_memory: bool = True
    enable_web_search: bool = True
    brave_api_key: Optional[str] = None
    windows_workspace: str = ""
    sync_to_mnt: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_nanobot_args(self) -> List[str]:
        args = []
        if self.workspace:
            args.extend(["--workspace", self.workspace])
        if self.config_path:
            args.extend(["--config", self.config_path])
        if self.model:
            args.extend(["--model", self.model])
        if self.provider:
            args.extend(["--provider", self.provider])
        if self.log_level:
            args.extend(["--log-level", self.log_level])
        if not self.enable_memory:
            args.append("--no-memory")
        if not self.enable_web_search:
            args.append("--no-web-search")
        return args

    def to_config_json(self) -> dict:
        config = {
            "providers": {
                self.provider: {
                    "api_key": self.api_key,
                    "model": self.model
                }
            }
        }
        if self.enable_web_search and self.brave_api_key:
            config["web_search"] = {
                "enabled": True,
                "api_key": self.brave_api_key
            }
        return config

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "distro_name": self.distro_name,
            "workspace": self.workspace,
            "config_path": self.config_path,
            "provider": self.provider,
            "model": self.model,
            "api_key": self.api_key,
            "skills_dir": self.skills_dir,
            "log_level": self.log_level,
            "enable_memory": self.enable_memory,
            "enable_web_search": self.enable_web_search,
            "brave_api_key": self.brave_api_key,
            "windows_workspace": self.windows_workspace,
            "sync_to_mnt": self.sync_to_mnt,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NanobotConfig":
        return cls(
            name=data["name"],
            distro_name=data["distro_name"],
            workspace=data.get("workspace", ""),
            config_path=data.get("config_path", ""),
            provider=data.get("provider", "openrouter"),
            model=data.get("model", "anthropic/claude-sonnet-4-20250529"),
            api_key=data.get("api_key", ""),
            skills_dir=data.get("skills_dir", ""),
            log_level=data.get("log_level", "INFO"),
            enable_memory=data.get("enable_memory", True),
            enable_web_search=data.get("enable_web_search", True),
            brave_api_key=data.get("brave_api_key"),
            windows_workspace=data.get("windows_workspace", ""),
            sync_to_mnt=data.get("sync_to_mnt", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
        )


@dataclass
class NanobotInstance:
    config: NanobotConfig
    status: NanobotStatus = NanobotStatus.STOPPED
    pid: Optional[int] = None
    started_at: Optional[datetime] = None
    message_count: int = 0
    last_error: Optional[str] = None
    logs: List[dict] = field(default_factory=list)
    max_logs: int = 1000

    @property
    def running_duration(self) -> Optional[str]:
        if not self.started_at:
            return None
        delta = datetime.now() - self.started_at
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def add_log(self, log_type: str, message: str) -> None:
        """Add a log entry to the instance."""
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": log_type,
            "message": message
        })
        # Keep only the last max_logs entries
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]

    def get_logs(self, lines: int = 100) -> List[str]:
        """Get the last N log lines formatted as strings."""
        recent_logs = self.logs[-lines:] if lines < len(self.logs) else self.logs
        return [f"[{log['type']}] {log['timestamp']}: {log['message']}" for log in recent_logs]

    def clear_logs(self) -> None:
        """Clear all logs."""
        self.logs.clear()
