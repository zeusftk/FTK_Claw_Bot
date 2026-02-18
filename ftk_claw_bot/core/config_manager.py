import os
import json
from typing import Dict, List, Optional, Set
from datetime import datetime
from pathlib import Path
from loguru import logger

from ..models import NanobotConfig, ChannelsConfig, SkillsConfig
from ..constants import Paths, VERSION


class ConfigManager:
    DEFAULT_CONFIG_NAME = "default"

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = str(Path.cwd() / "config")

        self._config_dir = config_dir
        self._main_config_path = str(Path(config_dir) / "config.json")
        self._nanobot_configs_dir = str(Path(config_dir) / "nanobot_configs")
        self._configs: Dict[str, NanobotConfig] = {}
        self._default_config_name: str = self.DEFAULT_CONFIG_NAME
        self._main_config: dict = {}

        self._ensure_dirs()
        self.load()

    def _ensure_dirs(self):
        Path(self._config_dir).mkdir(parents=True, exist_ok=True)
        Path(self._nanobot_configs_dir).mkdir(parents=True, exist_ok=True)

    def load(self, valid_distro_names: Optional[Set[str]] = None) -> Dict[str, NanobotConfig]:
        """加载配置
        
        Args:
            valid_distro_names: 有效的 WSL 分发名称集合，如果提供则过滤掉无效分发的配置
        """
        self._load_main_config()

        if os.path.exists(self._nanobot_configs_dir):
            for filename in os.listdir(self._nanobot_configs_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(self._nanobot_configs_dir, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        config = NanobotConfig.from_dict(data)
                        if config.distro_name and ('\x00' in config.distro_name or config.distro_name == '*'):
                            config.distro_name = ""
                        
                        if config.name == self.DEFAULT_CONFIG_NAME:
                            logger.warning(f"跳过旧的默认配置文件: {filename}")
                            continue
                        
                        if valid_distro_names and config.distro_name:
                            if config.distro_name not in valid_distro_names:
                                logger.warning(f"配置 '{config.name}' 的分发 '{config.distro_name}' 不存在，跳过加载")
                                continue
                        
                        self._configs[config.name] = config
                    except Exception as e:
                        logger.warning(f"加载配置文件失败 {filename}: {e}")
                        continue

        return self._configs
    
    def load_and_sync_from_wsl(self, wsl_manager, nanobot_controller, valid_distro_names: Optional[Set[str]] = None) -> Dict[str, NanobotConfig]:
        """加载配置并从 WSL 同步
        
        Args:
            wsl_manager: WSLManager 实例
            nanobot_controller: NanobotController 实例
            valid_distro_names: 有效的 WSL 分发名称集合
        
        Returns:
            配置字典
        """
        self.load(valid_distro_names)
        
        for config_name, config in list(self._configs.items()):
            if config.distro_name and valid_distro_names and config.distro_name in valid_distro_names:
                logger.info(f"尝试从 WSL 分发 '{config.distro_name}' 同步配置到 '{config_name}'")
                try:
                    wsl_config = nanobot_controller.read_config_from_wsl(config.distro_name)
                    if wsl_config and wsl_config != {}:
                        self.apply_wsl_config_to_ftk(config, wsl_config, wsl_manager)
                        self.save(config)
                        logger.info(f"已从 WSL 同步配置到 '{config_name}'")
                    else:
                        logger.info(f"WSL 中没有配置或配置为空，跳过同步: '{config_name}'")
                except Exception as e:
                    logger.warning(f"从 WSL 同步配置失败 '{config_name}': {e}")
        
        return self._configs
    
    def apply_wsl_config_to_ftk(self, ftk_config: NanobotConfig, wsl_config: dict, wsl_manager=None):
        """将 WSL 配置应用到 FTK 配置
        
        Args:
            ftk_config: FTK 配置对象
            wsl_config: WSL 配置字典
            wsl_manager: WSLManager 实例（用于路径转换）
        """
        agents = wsl_config.get("agents", {}).get("defaults", {})
        
        if "model" in agents:
            ftk_config.model = agents["model"]
        
        if "workspace" in agents:
            wsl_workspace = agents["workspace"]
            ftk_config.workspace = wsl_workspace
            
            if wsl_manager:
                windows_path = wsl_manager.convert_wsl_to_windows_path(wsl_workspace)
                if windows_path and windows_path != wsl_workspace:
                    ftk_config.windows_workspace = windows_path
                    ftk_config.sync_to_mnt = True
        
        providers = wsl_config.get("providers", {})
        for provider_name, provider_cfg in providers.items():
            ftk_config.provider = provider_name
            if provider_cfg.get("apiKey"):
                ftk_config.apiKey = provider_cfg.get("apiKey", "")
            if provider_cfg.get("apiBase"):
                ftk_config.base_url = provider_cfg["apiBase"]
            if "model" in provider_cfg:
                ftk_config.model = provider_cfg["model"]
            break
        
        gateway = wsl_config.get("gateway", {})
        if "host" in gateway:
            ftk_config.gateway_host = gateway["host"]
        if "port" in gateway:
            ftk_config.gateway_port = gateway["port"]
        
        tools = wsl_config.get("tools", {})
        web_search = tools.get("web", {}).get("search", {})
        if web_search.get("apiKey"):
            ftk_config.enable_web_search = True
            ftk_config.brave_apiKey = web_search["apiKey"]
        elif tools.get("web"):
            ftk_config.enable_web_search = True
        
        windows_bridge = tools.get("windowsBridge", {})
        if windows_bridge.get("port"):
            ftk_config.bridge_port = windows_bridge["port"]
        
        channels = wsl_config.get("channels", {})
        if channels:
            self._apply_channels_config(ftk_config, channels)
        
        skills = wsl_config.get("skills", {})
        if skills:
            self._apply_skills_config(ftk_config, skills)
    
    def _apply_channels_config(self, ftk_config: NanobotConfig, channels: dict):
        from ..models import (
            WhatsAppConfig, TelegramConfig, DiscordConfig, FeishuConfig,
            DingTalkConfig, SlackConfig, EmailConfig, QQConfig, MochatConfig
        )
        
        if "telegram" in channels:
            ftk_config.channels.telegram = TelegramConfig.from_nanobot_config(channels["telegram"])
        if "discord" in channels:
            ftk_config.channels.discord = DiscordConfig.from_nanobot_config(channels["discord"])
        if "feishu" in channels:
            ftk_config.channels.feishu = FeishuConfig.from_nanobot_config(channels["feishu"])
        if "dingtalk" in channels:
            ftk_config.channels.dingtalk = DingTalkConfig.from_nanobot_config(channels["dingtalk"])
        if "slack" in channels:
            ftk_config.channels.slack = SlackConfig.from_nanobot_config(channels["slack"])
        if "email" in channels:
            ftk_config.channels.email = EmailConfig.from_nanobot_config(channels["email"])
        if "qq" in channels:
            ftk_config.channels.qq = QQConfig.from_nanobot_config(channels["qq"])
        if "whatsapp" in channels:
            ftk_config.channels.whatsapp = WhatsAppConfig.from_nanobot_config(channels["whatsapp"])
        if "mochat" in channels:
            ftk_config.channels.mochat = MochatConfig.from_nanobot_config(channels["mochat"])
    
    def _apply_skills_config(self, ftk_config: NanobotConfig, skills: dict):
        from ..models import SkillInfo
        
        if "enabled_skills" in skills:
            ftk_config.skills.enabled_skills = skills["enabled_skills"]
        if "custom_skills_dir" in skills:
            ftk_config.skills.custom_skills_dir = skills["custom_skills_dir"]
        if "skill_settings" in skills:
            ftk_config.skills.skill_settings = skills["skill_settings"]
    
    _apply_wsl_config_to_ftk = apply_wsl_config_to_ftk

    def _load_main_config(self):
        if os.path.exists(self._main_config_path):
            try:
                with open(self._main_config_path, "r", encoding="utf-8") as f:
                    self._main_config = json.load(f)
                self._default_config_name = self._main_config.get(
                    "default_config",
                    self.DEFAULT_CONFIG_NAME
                )
            except Exception:
                self._main_config = {}

    def _save_main_config(self):
        self._main_config["default_config"] = self._default_config_name
        self._main_config["version"] = VERSION

        with open(self._main_config_path, "w", encoding="utf-8") as f:
            json.dump(self._main_config, f, indent=2, ensure_ascii=False)

    def save_main_config(self):
        self._save_main_config()

    def save(self, config: NanobotConfig) -> bool:
        try:
            config.updated_at = datetime.now()

            # 允许覆盖已有配置（因为配置名称等于WSL分发名称，一一对应）
            file_path = os.path.join(self._nanobot_configs_dir, f"{config.name}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)

            self._configs[config.name] = config
            logger.info(f"配置保存成功: {config.name}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def delete(self, config_name: str) -> bool:
        if config_name not in self._configs:
            return False

        try:
            file_path = os.path.join(self._nanobot_configs_dir, f"{config_name}.json")
            if os.path.exists(file_path):
                os.remove(file_path)

            del self._configs[config_name]

            if self._default_config_name == config_name:
                remaining = list(self._configs.keys())
                self._default_config_name = remaining[0] if remaining else self.DEFAULT_CONFIG_NAME
                self._save_main_config()

            return True
        except Exception:
            return False

    def get(self, config_name: str) -> Optional[NanobotConfig]:
        return self._configs.get(config_name)

    def get_all(self) -> Dict[str, NanobotConfig]:
        return self._configs.copy()

    def get_default(self) -> Optional[NanobotConfig]:
        return self._configs.get(self._default_config_name)

    def get_default_name(self) -> str:
        return self._default_config_name

    def set_default(self, config_name: str) -> bool:
        if config_name not in self._configs:
            return False

        self._default_config_name = config_name
        self._save_main_config()
        return True

    def exists(self, config_name: str) -> bool:
        return config_name in self._configs

    def rename(self, old_name: str, new_name: str) -> bool:
        if old_name not in self._configs:
            return False

        if new_name in self._configs:
            return False

        config = self._configs[old_name]
        config.name = new_name

        if not self.save(config):
            return False

        self.delete(old_name)

        if self._default_config_name == old_name:
            self.set_default(new_name)

        return True

    def create_default_config(self, distro_name: str = "") -> NanobotConfig:
        if not distro_name or distro_name == "*":
            distro_name = ""
        config = NanobotConfig(
            name=self.DEFAULT_CONFIG_NAME,
            distro_name=distro_name,
            workspace="~/.nanobot",
            provider="custom",
            model=" ",
            log_level="INFO",
            enable_memory=True,
            enable_web_search=True,
            gateway_host="0.0.0.0",
            gateway_port=18888,
        )
        self.save(config)
        return config

    def get_main_config(self) -> dict:
        return self._main_config.copy()

    def update_main_config(self, key: str, value) -> bool:
        try:
            self._main_config[key] = value
            self._save_main_config()
            return True
        except Exception:
            return False

    def get_config_dir(self) -> str:
        return self._config_dir

    def get_nanobot_configs_dir(self) -> str:
        return self._nanobot_configs_dir
