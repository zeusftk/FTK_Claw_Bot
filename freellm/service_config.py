"""
FreeLLM 服务配置模型
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, List
from pathlib import Path


@dataclass
class ServiceInstanceConfig:
    """单个 WSL 分发的服务配置"""
    distro_name: str
    llm_port: int = 20100
    router_port: int = 20200
    auto_start: bool = False
    enabled: bool = True
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ServiceInstanceConfig":
        if "opencode_port" in data:
            data["llm_port"] = data.pop("opencode_port")
        return cls(**data)


@dataclass
class ServiceConfig:
    """所有服务的配置"""
    instances: Dict[str, ServiceInstanceConfig] = field(default_factory=dict)
    default_llm_port_start: int = 20100
    default_router_port_start: int = 20200
    
    def to_dict(self) -> dict:
        return {
            "instances": {k: v.to_dict() for k, v in self.instances.items()},
            "default_llm_port_start": self.default_llm_port_start,
            "default_router_port_start": self.default_router_port_start,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ServiceConfig":
        instances = {}
        for k, v in data.get("instances", {}).items():
            instances[k] = ServiceInstanceConfig.from_dict(v)
        return cls(
            instances=instances,
            default_llm_port_start=data.get("default_llm_port_start", data.get("default_opencode_port_start", 20100)),
            default_router_port_start=data.get("default_router_port_start", 20200),
        )
    
    def get_instance(self, distro_name: str) -> ServiceInstanceConfig:
        if distro_name not in self.instances:
            instance_count = len(self.instances)
            llm_port = self.default_llm_port_start + instance_count
            router_port = self.default_router_port_start + instance_count
            self.instances[distro_name] = ServiceInstanceConfig(
                distro_name=distro_name,
                llm_port=llm_port,
                router_port=router_port
            )
        return self.instances[distro_name]
    
    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, path: Path) -> "ServiceConfig":
        if not path.exists():
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return cls()


def get_default_config_path() -> Path:
    """获取默认配置文件路径"""
    return Path(__file__).parent / "config.json"
