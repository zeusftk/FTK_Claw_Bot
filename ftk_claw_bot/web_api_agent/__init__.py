"""Web API Agent - 浏览器自动化库"""
__version__ = "1.0.0"

from ftk_claw_bot.web_api_agent.config import config
from ftk_claw_bot.web_api_agent.core.session_manager import SessionManager, Session
from ftk_claw_bot.web_api_agent.core.web_agent import WebAgent
from ftk_claw_bot.web_api_agent.core.data_extractor import DataExtractor

__all__ = [
    "config",
    "SessionManager",
    "Session",
    "WebAgent",
    "DataExtractor",
]
