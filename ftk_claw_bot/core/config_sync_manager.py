# -*- coding: utf-8 -*-
import json
from datetime import datetime
from typing import Optional, Dict, Any

from ..models import ClawbotConfig
from .wsl_manager import WSLManager


def camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


def convert_keys_to_snake(data: Any) -> Any:
    """Recursively convert camelCase keys to snake_case."""
    if isinstance(data, dict):
        return {camel_to_snake(k): convert_keys_to_snake(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_keys_to_snake(item) for item in data]
    return data


def snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def convert_keys_to_camel(data: Any) -> Any:
    """Recursively convert snake_case keys to camelCase."""
    if isinstance(data, dict):
        return {snake_to_camel(k): convert_keys_to_camel(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_keys_to_camel(item) for item in data]
    return data


class ConfigSyncManager:
    """配置同步管理器
    
    负责 FTK_claw_bot 配置与 WSL 中 clawbot 配置的双向同步
    """
    
    def __init__(self, wsl_manager: WSLManager):
        self._wsl_manager = wsl_manager
    
    def convert_ftk_to_clawbot(self, ftk_config: ClawbotConfig, base_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """将 FTK_claw_bot 的 ClawbotConfig 转换为 clawbot 配置格式
        
        Args:
            ftk_config: FTK 配置对象
            base_config: 基础配置（用于合并）
        
        Returns:
            完整的 clawbot 配置字典
        """
        return ftk_config.to_full_clawbot_config(base_config)
    
    def convert_clawbot_to_ftk(self, clawbot_config: Dict[str, Any]) -> Dict[str, Any]:
        """将 clawbot 配置转换为 FTK_claw_bot 可识别的格式
        
        Args:
            clawbot_config: clawbot 配置字典
        
        Returns:
            FTK 可识别的配置字典
        """
        from loguru import logger
        
        result = {}
        
        agents = clawbot_config.get("agents", {}).get("defaults", {})
        if "model" in agents:
            result["model"] = agents["model"]
        
        if "workspace" in agents:
            wsl_workspace = agents["workspace"]
            result["workspace"] = wsl_workspace
            windows_path = self._wsl_manager.convert_wsl_to_windows_path(wsl_workspace)
            if windows_path and windows_path != wsl_workspace:
                result["windows_workspace"] = windows_path
                result["sync_to_mnt"] = True
        
        providers = clawbot_config.get("providers", {})
        for provider_name, provider_cfg in providers.items():
            if provider_cfg.get("apiKey"):
                result["provider"] = provider_name
                result["apiKey"] = provider_cfg.get("apiKey", "")
                if provider_cfg.get("apiBase"):
                    result["base_url"] = provider_cfg["apiBase"]
                if "model" in provider_cfg:
                    result["model"] = provider_cfg["model"]
                break
        
        gateway = clawbot_config.get("gateway", {})
        if "host" in gateway:
            result["gateway_host"] = gateway["host"]
        if "port" in gateway:
            result["gateway_port"] = gateway["port"]
        
        tools = clawbot_config.get("tools", {})
        web_search = tools.get("web", {}).get("search", {})
        if web_search.get("apiKey"):
            result["enable_web_search"] = True
            result["brave_apiKey"] = web_search["apiKey"]
        
        windows_bridge = tools.get("windowsBridge", {})
        if windows_bridge.get("port"):
            result["bridge_port"] = windows_bridge["port"]
        
        return result
    
    def read_from_wsl(self, distro_name: str, config_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """从 WSL 读取配置文件
        
        Args:
            distro_name: WSL 分发名称
            config_path: 配置文件路径（可选，默认 ~/.clawbot/config.json）
        
        Returns:
            配置字典（保持原始 camelCase 键名），失败返回 None
        """
        from loguru import logger
        
        if config_path is None:
            config_path = "~/.clawbot/config.json"
        
        result = self._wsl_manager.execute_command(
            distro_name,
            f"cat {config_path} 2>/dev/null || echo '{{}}'"
        )
        
        if not result.success:
            return None
        
        try:
            data = json.loads(result.stdout)
            return data
        except json.JSONDecodeError:
            return {}
    
    def write_to_wsl(self, distro_name: str, config: Dict[str, Any], config_path: Optional[str] = None) -> bool:
        """写入配置到 WSL
        
        优化：
        1. 先备份原 config.json
        2. 覆盖修改 config.json
        
        Args:
            distro_name: WSL 分发名称
            config: 配置字典
            config_path: 配置文件路径（可选，默认 ~/.clawbot/config.json）
        
        Returns:
            是否成功
        """
        if config_path is None:
            config_path = "~/.clawbot/config.json"
        
        config_json = json.dumps(config, indent=2, ensure_ascii=False)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        cmd = f"""
if [ -f {config_path} ]; then
    cp {config_path} {config_path}.backup.{timestamp}
fi
cat > {config_path} << 'EOF'
{config_json}
EOF
"""
        
        result = self._wsl_manager.execute_command(distro_name, cmd)
        return result.success
    
    def sync_ftk_to_wsl(self, ftk_config: ClawbotConfig, merge: bool = True) -> bool:
        """同步 FTK 配置到 WSL
        
        Args:
            ftk_config: FTK 配置对象
            merge: 是否合并模式（True=保留 clawbot 其他配置，False=完全覆盖）
        
        Returns:
            是否成功
        """
        base_config = {}
        if merge:
            base_config = self.read_from_wsl(ftk_config.distro_name) or {}
        
        full_config = self.convert_ftk_to_clawbot(ftk_config, base_config)
        return self.write_to_wsl(ftk_config.distro_name, full_config)
    
    def sync_wsl_to_ftk(self, distro_name: str) -> Optional[Dict[str, Any]]:
        """从 WSL 同步配置到 FTK
        
        Args:
            distro_name: WSL 分发名称
        
        Returns:
            FTK 可识别的配置字典，失败返回 None
        """
        clawbot_config = self.read_from_wsl(distro_name)
        if clawbot_config is None:
            return None
        
        return self.convert_clawbot_to_ftk(clawbot_config)
