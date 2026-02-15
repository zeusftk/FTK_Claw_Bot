import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from ..models import NanobotConfig


class ConfigManager:
    DEFAULT_CONFIG_NAME = "default"

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = os.path.join(os.environ.get("APPDATA", ""), "FTK_Bot")

        self._config_dir = config_dir
        self._main_config_path = os.path.join(config_dir, "config.json")
        self._nanobot_configs_dir = os.path.join(config_dir, "nanobot_configs")
        self._configs: Dict[str, NanobotConfig] = {}
        self._default_config_name: str = self.DEFAULT_CONFIG_NAME
        self._main_config: dict = {}

        self._ensure_dirs()
        self.load()

    def _ensure_dirs(self):
        Path(self._config_dir).mkdir(parents=True, exist_ok=True)
        Path(self._nanobot_configs_dir).mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, NanobotConfig]:
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
                        self._configs[config.name] = config
                    except Exception:
                        continue

        return self._configs

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
        self._main_config["version"] = "1.0.0"

        with open(self._main_config_path, "w", encoding="utf-8") as f:
            json.dump(self._main_config, f, indent=2, ensure_ascii=False)

    def save(self, config: NanobotConfig) -> bool:
        try:
            config.updated_at = datetime.now()

            file_path = os.path.join(self._nanobot_configs_dir, f"{config.name}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)

            self._configs[config.name] = config
            return True
        except Exception:
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
            provider="openrouter",
            model="anthropic/claude-sonnet-4-20250529",
            log_level="INFO",
            enable_memory=True,
            enable_web_search=True,
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
