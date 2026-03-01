# -*- coding: utf-8 -*-
from enum import Enum
from typing import Dict, Any
from pathlib import Path


VERSION = "1.0.9"
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
    """路径配置 - 使用统一的 user_data 目录"""
    
    @classmethod
    def get_log_dir(cls) -> Path:
        """获取日志目录"""
        from ftk_claw_bot.utils.user_data_dir import user_data
        return user_data.logs
    
    @classmethod
    def get_clawbot_configs_dir(cls) -> Path:
        """获取 Clawbot 实例配置目录"""
        from ftk_claw_bot.utils.user_data_dir import user_data
        return user_data.clawbot_configs
    
    @classmethod
    def get_config_dir(cls) -> Path:
        """获取配置目录"""
        from ftk_claw_bot.utils.user_data_dir import user_data
        return user_data.config
    
    @classmethod
    def get_user_data_dir(cls) -> Path:
        """获取用户数据根目录"""
        from ftk_claw_bot.utils.user_data_dir import user_data
        return user_data.base


class WebAutomation:
    """Web 自动化配置"""
    # 浏览器窗口固定大小
    VIEWPORT_WIDTH = 1280
    VIEWPORT_HEIGHT = 800
    
    # 默认超时时间（秒）
    DEFAULT_TIMEOUT = 30
    PAGE_LOAD_TIMEOUT = 60
    
    # 截图配置
    SCREENSHOT_QUALITY = 80
    SCREENSHOT_TYPE = "jpeg"  # jpeg 或 png


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


class Clawbot:
    DEFAULT_WORKSPACE = "/home/user/clawbot"
    DEFAULT_PROVIDER = "qwen_portal"
    DEFAULT_MODEL = "qwen-portal/coder-model"
    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_GATEWAY_HOST = "0.0.0.0"
    DEFAULT_GATEWAY_PORT = 18888


class Monitor:
    DEFAULT_INTERVAL = 5.0
    WSL_CHECK_INTERVAL = 10.0
    CLAWBOT_CHECK_INTERVAL = 5.0


class Language:
    DEFAULT = "zh_CN"
    SUPPORTED = {
        "zh_CN": "简体中文",
        "en_US": "English"
    }


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
    "clawbot": "clawbot",
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
