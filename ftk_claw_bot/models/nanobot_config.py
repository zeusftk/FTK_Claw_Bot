from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from .channel_config import ChannelsConfig
from .skill_config import SkillsConfig


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
    provider: str = "qwen_portal"
    model: str = "qwen-portal/coder-model"
    apiKey: str = ""
    base_url: str = ""
    skills_dir: str = ""
    log_level: str = "INFO"
    enable_memory: bool = True
    enable_web_search: bool = True
    brave_apiKey: Optional[str] = None
    windows_workspace: str = ""
    sync_to_mnt: bool = True
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 18888
    bridge_port: int = 9527
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    channels: ChannelsConfig = field(default_factory=ChannelsConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)

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
        if self.base_url:
            args.extend(["--base-url", self.base_url])
        if self.log_level:
            args.extend(["--log-level", self.log_level])
        if not self.enable_memory:
            args.append("--no-memory")
        if not self.enable_web_search:
            args.append("--no-web-search")
        if self.gateway_host and self.gateway_host != "0.0.0.0":
            args.extend(["--gateway-host", self.gateway_host])
        if self.gateway_port and self.gateway_port != 18888:
            args.extend(["--gateway-port", str(self.gateway_port)])
        return args

    def to_config_json(self) -> dict:
        provider_config = {
            "apiKey": self.apiKey,
            "model": self.model
        }
        if self.base_url:
            provider_config["base_url"] = self.base_url
        config = {
            "providers": {
                self.provider: provider_config
            }
        }
        if self.enable_web_search and self.brave_apiKey:
            config["web_search"] = {
                "enabled": True,
                "apiKey": self.brave_apiKey
            }
        return config
    
    def to_full_nanobot_config(self, base_config: Optional[dict] = None) -> dict:
        """
        生成完整的 nanobot 配置
        
        Args:
            base_config: 基础配置（用于合并）
        
        Returns:
            完整的 nanobot 配置字典
        """
        config = base_config or {}
        
        config.setdefault("agents", {})
        config.setdefault("providers", {})
        config.setdefault("gateway", {})
        config.setdefault("tools", {})
        config.setdefault("channels", {})
        
        config["agents"]["defaults"] = {
            "workspace": self.workspace or "~/.nanobot/workspace",
            "model": self.model,
            "max_tokens": 8192,
            "temperature": 0.7,
            "max_tool_iterations": 20,
            "memory_window": 50
        }
        
        provider_config = {
            "apiKey": self.apiKey
        }
        if self.base_url:
            provider_config["apiBase"] = self.base_url
        
        provider_name = self.provider
        if provider_name == "自定义":
            provider_name = "custom"
        
        config["providers"][provider_name] = provider_config
        
        config["gateway"]["host"] = self.gateway_host or "0.0.0.0"
        config["gateway"]["port"] = self.gateway_port or 18888
        
        if self.enable_web_search and self.brave_apiKey:
            config["tools"].setdefault("web", {})
            config["tools"]["web"]["search"] = {
                "apiKey": self.brave_apiKey,
                "max_results": 5
            }
        
        config["tools"]["windowsBridge"] = {
            "enabled": True,
            "host": None,
            "port": self.bridge_port,
            "autoConnect": True
        }
        
        config["channels"] = self.channels.to_nanobot_config()
        
        return config

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "distro_name": self.distro_name,
            "workspace": self.workspace,
            "config_path": self.config_path,
            "provider": self.provider,
            "model": self.model,
            "apiKey": self.apiKey,
            "base_url": self.base_url,
            "skills_dir": self.skills_dir,
            "log_level": self.log_level,
            "enable_memory": self.enable_memory,
            "enable_web_search": self.enable_web_search,
            "brave_apiKey": self.brave_apiKey,
            "windows_workspace": self.windows_workspace,
            "sync_to_mnt": self.sync_to_mnt,
            "gateway_host": self.gateway_host,
            "gateway_port": self.gateway_port,
            "bridge_port": self.bridge_port,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "channels": self.channels.to_dict(),
            "skills": self.skills.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NanobotConfig":
        channels_data = data.get("channels", {})
        skills_data = data.get("skills", {})
        return cls(
            name=data["name"],
            distro_name=data["distro_name"],
            workspace=data.get("workspace", ""),
            config_path=data.get("config_path", ""),
            provider=data.get("provider", "qwen_portal"),
            model=data.get("model", "qwen-portal/coder-model"),
            apiKey=data.get("apiKey", ""),
            base_url=data.get("base_url", ""),
            skills_dir=data.get("skills_dir", ""),
            log_level=data.get("log_level", "INFO"),
            enable_memory=data.get("enable_memory", True),
            enable_web_search=data.get("enable_web_search", True),
            brave_apiKey=data.get("brave_apiKey"),
            windows_workspace=data.get("windows_workspace", ""),
            sync_to_mnt=data.get("sync_to_mnt", True),
            gateway_host=data.get("gateway_host", "0.0.0.0"),
            gateway_port=data.get("gateway_port", 18888),
            bridge_port=data.get("bridge_port", 9527),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            channels=ChannelsConfig.from_dict(channels_data) if channels_data else ChannelsConfig(),
            skills=SkillsConfig.from_dict(skills_data) if skills_data else SkillsConfig(),
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
