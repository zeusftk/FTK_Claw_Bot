from enum import Enum
from typing import Dict, Any, Optional
from pathlib import Path


VERSION = "1.0.3.1"
APP_NAME = "FTK_Claw_Bot"
APP_AUTHOR = "FTK Team"
APP_EMAIL = "zeusftk@gmail.com"


class Network:
    IPC_PORT = 9527
    GATEWAY_PORT = 18888
    DEFAULT_HOST = "0.0.0.0"
    CONNECTION_TIMEOUT = 30
    RECONNECT_INTERVAL = 5


class Paths:
    LOG_DIR_NAME = "logs"
    
    @classmethod
    def get_log_dir(cls) -> Path:
        return Path.cwd() / cls.LOG_DIR_NAME
    
    @classmethod
    def get_clawbot_configs_dir(cls) -> Path:
        return Path.cwd() / "clawbot_configs"


class UI:
    MIN_WINDOW_WIDTH = 1200
    MIN_WINDOW_HEIGHT = 800
    DEFAULT_WINDOW_WIDTH = 1400
    DEFAULT_WINDOW_HEIGHT = 900
    NAV_WIDTH = 200
    SPLASH_DURATION = 2000


class WSL:
    DEFAULT_TIMEOUT = 30
    LIST_TIMEOUT = 10
    START_TIMEOUT = 60
    STOP_TIMEOUT = 30


class Bridge:
    DEFAULT_WINDOWS_PORT = 9527


class Nanobot:
    DEFAULT_WORKSPACE = "/home/user/nanobot"
    DEFAULT_PROVIDER = "qwen_portal"
    DEFAULT_MODEL = "qwen-portal/coder-model"
    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_GATEWAY_HOST = "0.0.0.0"
    DEFAULT_GATEWAY_PORT = 18888


class Monitor:
    DEFAULT_INTERVAL = 5.0
    WSL_CHECK_INTERVAL = 10.0
    NANOBOT_CHECK_INTERVAL = 5.0


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


PANEL_NAMES = {
    "overview": "概览",
    "config": "配置管理",
    "command": "命令执行",
    "chat": "聊天",
    "bridge": "桥接",
    "log": "日志查看",
    "nanobot": "clawbot",
    "skills": "技能管理",
}


def get_version() -> str:
    return VERSION


def get_app_info() -> Dict[str, Any]:
    return {
        "name": APP_NAME,
        "version": VERSION,
        "author": APP_AUTHOR,
        "email": APP_EMAIL,
    }
