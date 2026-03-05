# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from .channel_config import ChannelsConfig
from .skill_config import SkillsConfig


class ClawbotStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    ERROR = "error"


# ============================================================================
# 多模型配置数据类
# ============================================================================

@dataclass
class ProviderConfigItem:
    """单个 Provider 配置"""
    name: str                    # provider 名称
    api_key: str = ""            # API Key
    base_url: str = ""           # 自定义 URL
    enabled: bool = True         # 是否启用

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "enabled": self.enabled,
        }

    def to_clawbot_dict(self) -> dict:
        """转换为 clawbot 格式（字段名映射）"""
        result: dict[str, Any] = {}
        if self.api_key:
            result["apiKey"] = self.api_key
        if self.base_url:
            result["apiBase"] = self.base_url
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ProviderConfigItem":
        return cls(
            name=data.get("name", ""),
            api_key=data.get("api_key", "") or data.get("apiKey", ""),
            base_url=data.get("base_url", "") or data.get("apiBase", ""),
            enabled=data.get("enabled", True),
        )


@dataclass
class ModelConfigItem:
    """单个模型配置"""
    name: str                    # 模型名称
    provider: str                # 关联的 provider
    alias: str = ""              # 别名 (fast/balanced/powerful)
    capabilities: List[str] = field(default_factory=list)
    cost_tier: Literal["low", "medium", "high"] = "medium"
    max_tokens: int = 4096
    priority: int = 1
    temperature: Optional[float] = None
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "provider": self.provider,
            "alias": self.alias,
            "capabilities": self.capabilities,
            "cost_tier": self.cost_tier,
            "max_tokens": self.max_tokens,
            "priority": self.priority,
            "temperature": self.temperature,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModelConfigItem":
        return cls(
            name=data.get("name", ""),
            provider=data.get("provider", ""),
            alias=data.get("alias", ""),
            capabilities=data.get("capabilities", []),
            cost_tier=data.get("cost_tier", "medium"),
            max_tokens=data.get("max_tokens", 4096),
            priority=data.get("priority", 1),
            temperature=data.get("temperature"),
            enabled=data.get("enabled", True),
        )


@dataclass
class RoutingRuleItem:
    """路由规则"""
    task_type: str               # 任务类型
    preferred_model: str         # 首选模型 (alias 或 name)
    fallback: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_type": self.task_type,
            "preferred_model": self.preferred_model,
            "fallback": self.fallback,
            "conditions": self.conditions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RoutingRuleItem":
        return cls(
            task_type=data.get("task_type", ""),
            preferred_model=data.get("preferred_model", ""),
            fallback=data.get("fallback", []),
            conditions=data.get("conditions", {}),
        )


@dataclass
class MultiModelConfigItem:
    """多模型配置"""
    enabled: bool = False
    strategy: Literal["auto", "manual", "round_robin", "priority"] = "auto"
    models: List[ModelConfigItem] = field(default_factory=list)
    routing_rules: List[RoutingRuleItem] = field(default_factory=list)
    fallback_chain: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "strategy": self.strategy,
            "models": [m.to_dict() for m in self.models],
            "routing_rules": [r.to_dict() for r in self.routing_rules],
            "fallback_chain": self.fallback_chain,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MultiModelConfigItem":
        if not data:
            return cls()
        return cls(
            enabled=data.get("enabled", False),
            strategy=data.get("strategy", "auto"),
            models=[ModelConfigItem.from_dict(m) for m in data.get("models", [])],
            routing_rules=[RoutingRuleItem.from_dict(r) for r in data.get("routing_rules", [])],
            fallback_chain=data.get("fallback_chain", []),
        )


@dataclass
class ClawbotConfig:
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
    embedding_url: str = ""
    embedding_enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    channels: ChannelsConfig = field(default_factory=ChannelsConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    # 多模型配置支持
    providers: List[ProviderConfigItem] = field(default_factory=list)
    multi_model: MultiModelConfigItem = field(default_factory=MultiModelConfigItem)

    def to_clawbot_args(self) -> List[str]:
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
    
    def to_full_clawbot_config(self, base_config: Optional[dict] = None) -> dict:
        """
        生成完整的 clawbot 配置
        
        Args:
            base_config: 基础配置（用于合并）
        
        Returns:
            完整的 clawbot 配置字典
        """
        config = base_config or {}
        
        config.setdefault("agents", {})
        config.setdefault("providers", {})
        config.setdefault("gateway", {})
        config.setdefault("tools", {})
        config.setdefault("channels", {})
        
        # 辅助函数：规范化 provider 名称
        def normalize_provider(name: str) -> str:
            return "custom" if name in ["自定义", "custom"] else name
        
        # 收集所有模型使用的 provider 名称（用于同步 providers 配置）
        used_providers = set()
        for m in self.multi_model.models:
            provider_name = normalize_provider(m.provider)
            used_providers.add(provider_name)
        
        # providers 完整替换（清除未使用的 provider）
        # 重新初始化 providers，只保留被模型使用的
        config["providers"] = {}
        
        # 计算默认模型和参数（从第一个启用的模型获取）
        default_model = self.model
        default_max_tokens = 8192
        default_temperature = 0.7
        
        if self.multi_model.models:
            # 从第一个启用的模型获取默认值
            first_enabled = next((m for m in self.multi_model.models if m.enabled), None)
            if first_enabled:
                provider_name = normalize_provider(first_enabled.provider)
                default_model = f"{provider_name}/{first_enabled.name}"
                default_max_tokens = first_enabled.max_tokens or 8192
                default_temperature = first_enabled.temperature if first_enabled.temperature is not None else 0.7
        elif self.model and "/" not in self.model:
            # 如果没有多模型配置，但有单个模型，添加 provider 前缀
            default_model = f"{normalize_provider(self.provider)}/{self.model}"
        
        # 同步被模型使用的 providers（从 providers 列表中提取）
        for p in self.providers:
            provider_key = normalize_provider(p.name)
            # 只同步被模型使用的 provider
            if provider_key in used_providers:
                clawbot_provider_config = p.to_clawbot_dict()
                if clawbot_provider_config:  # 只有非空配置才添加
                    config["providers"][provider_key] = clawbot_provider_config
        
        # 合并 agents.defaults（保留非 FTK 管理的字段）
        defaults = config["agents"].setdefault("defaults", {})
        defaults.update({
            "workspace": self.workspace or "~/.clawbot/workspace",
            "model": default_model,
            "max_tokens": default_max_tokens,
            "temperature": default_temperature,
            "max_tool_iterations": 20,
            "memory_window": 50
        })
        
        # 保留原有的单个 provider 配置（向后兼容）
        # 注意：这里使用 apiKey 字段（FTK 本地配置），如果 providers 列表中已有则不覆盖
        if self.apiKey and not self.multi_model.models:
            provider_config = {"apiKey": self.apiKey}
            if self.base_url:
                provider_config["apiBase"] = self.base_url
            
            provider_name = normalize_provider(self.provider)
            
            if provider_name not in config["providers"]:
                config["providers"][provider_name] = provider_config
        
        config["gateway"]["host"] = self.gateway_host or "0.0.0.0"
        config["gateway"]["port"] = self.gateway_port or 18888
        
        if self.enable_web_search and self.brave_apiKey:
            config["tools"].setdefault("web", {})
            config["tools"]["web"]["search"] = {
                "apiKey": self.brave_apiKey,
                "max_results": 5
            }
        
        # 合并 tools.windowsBridge（保留非 FTK 管理的字段）
        config["tools"].setdefault("windowsBridge", {})
        config["tools"]["windowsBridge"].update({
            "enabled": True,
            "host": None,
            "port": self.bridge_port,
            "autoConnect": True
        })
        
        # 合并 memory（保留非 FTK 管理的字段）
        memory_config = config.setdefault("memory", {})
        memory_config.setdefault("embedding_api", {})
        memory_config["embedding_api"].update({
            "enabled": self.embedding_enabled and bool(self.embedding_url),
            "base_url": self.embedding_url
        })
        
        config["channels"] = self.channels.to_clawbot_config()
        
        # 同步技能配置（包含启用列表和优先级）
        config["skills"] = {
            "enabled": self.skills.enabled_skills if self.skills.enabled_skills else None,
            "priorities": self.skills.skill_priorities
        }
        
        # 合并 multi_model 配置（保留非 FTK 管理的字段）
        # multi_model 完整替换（因为存在删除操作，不能使用合并）
        # 即使 multi_model.enabled=False 也同步所有模型配置
        # clawbot 会根据 enabled 字段决定是否使用智能路由
        if self.multi_model.models:
            # 规范化 model 的 provider 名称
            normalized_models = []
            for m in self.multi_model.models:
                m_dict = m.to_dict()
                m_dict["provider"] = normalize_provider(m_dict["provider"])
                normalized_models.append(m_dict)
            
            # 完整替换 multi_model 配置
            config["agents"]["multi_model"] = {
                "enabled": self.multi_model.enabled,
                "strategy": self.multi_model.strategy,
                "models": normalized_models,
                "routing_rules": [r.to_dict() for r in self.multi_model.routing_rules],
                "fallback_chain": self.multi_model.fallback_chain,
            }
        else:
            # 如果没有模型配置，设置空的 multi_model（保持结构一致）
            config["agents"]["multi_model"] = {
                "enabled": False,
                "strategy": "auto",
                "models": [],
                "routing_rules": [],
                "fallback_chain": [],
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
            "embedding_url": self.embedding_url,
            "embedding_enabled": self.embedding_enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "channels": self.channels.to_dict(),
            "skills": self.skills.to_dict(),
            "providers": [p.to_dict() for p in self.providers],
            "multi_model": self.multi_model.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClawbotConfig":
        channels_data = data.get("channels", {})
        skills_data = data.get("skills", {})
        providers_data = data.get("providers", [])
        multi_model_data = data.get("multi_model", {})
        
        # === 自动迁移旧配置 ===
        # 如果 providers 和 multi_model 为空，但从旧字段中可以提取配置，则自动迁移
        provider_name = data.get("provider", "qwen_portal")
        model_name = data.get("model", "")
        api_key = data.get("apiKey", "")
        base_url = data.get("base_url", "")
        
        # 检查是否需要迁移
        need_migration = False
        if not providers_data and api_key:
            # 旧配置有 API Key 但没有 providers 列表
            need_migration = True
        
        if need_migration:
            # 从 model 字段中解析 provider 和模型名
            # 格式可能是 "provider/model" 或直接 "model"
            if "/" in model_name:
                parts = model_name.split("/", 1)
                provider_from_model = parts[0].lower().replace("-", "_")
                actual_model_name = parts[1]
            else:
                provider_from_model = provider_name.lower().replace("-", "_")
                actual_model_name = model_name
            
            # 处理中文 provider 名称
            if provider_from_model in ["自定义", "custom"]:
                provider_from_model = "custom"
            
            # 创建 provider 配置
            providers_data = [{
                "name": provider_from_model,
                "api_key": api_key,
                "base_url": base_url,
                "enabled": True,
            }]
            
            # 更新 provider_name 为规范化后的值
            provider_name = provider_from_model
            
            # 创建 multi_model 配置（单一模型模式）
            if not multi_model_data and actual_model_name:
                multi_model_data = {
                    "enabled": False,  # 单一模型模式
                    "strategy": "auto",
                    "models": [{
                        "name": actual_model_name,
                        "provider": provider_from_model,
                        "alias": "default",
                        "capabilities": [],
                        "cost_tier": "medium",
                        "max_tokens": 4096,
                        "priority": 1,
                        "enabled": True,
                    }],
                    "routing_rules": [],
                    "fallback_chain": ["default"],
                }
        
        # 规范化 provider 名称（处理中文等）
        normalized_provider = provider_name
        if normalized_provider in ["自定义", "custom"]:
            normalized_provider = "custom"
        
        return cls(
            name=data["name"],
            distro_name=data["distro_name"],
            workspace=data.get("workspace", ""),
            config_path=data.get("config_path", ""),
            provider=normalized_provider,
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
            embedding_url=data.get("embedding_url", ""),
            embedding_enabled=data.get("embedding_enabled", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            channels=ChannelsConfig.from_dict(channels_data) if channels_data else ChannelsConfig(),
            skills=SkillsConfig.from_dict(skills_data) if skills_data else SkillsConfig(),
            providers=[ProviderConfigItem.from_dict(p) for p in providers_data] if providers_data else [],
            multi_model=MultiModelConfigItem.from_dict(multi_model_data) if multi_model_data else MultiModelConfigItem(),
        )


@dataclass
class ClawbotInstance:
    config: ClawbotConfig
    status: ClawbotStatus = ClawbotStatus.STOPPED
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
