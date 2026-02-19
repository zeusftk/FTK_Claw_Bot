"""
OpenCode Client - Python LLM 客户端
通过 opencode 本地 server 调用 LLM，无需配置 API key
"""

from .client import (
    OpenCodeClient,
    OpenCodeError,
    ServerNotRunningError,
    ServerStartError,
    APIError,
    Model,
    Message,
    ChatResult,
    chat,
    chat_with_session,
    list_free_models,
)

__version__ = "1.0.0"
__all__ = [
    "OpenCodeClient",
    "OpenCodeError",
    "ServerNotRunningError", 
    "ServerStartError",
    "APIError",
    "Model",
    "Message",
    "ChatResult",
    "chat",
    "chat_with_session",
    "list_free_models",
]
