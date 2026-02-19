"""
FreeLLM Client - Python LLM 客户端
通过 freellm 本地 server 调用 LLM，无需配置 API key
"""

from .client import (
    FreeLLMClient,
    FreeLLMError,
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
    "FreeLLMClient",
    "FreeLLMError",
    "ServerNotRunningError", 
    "ServerStartError",
    "APIError",
    "Model",
    "Message",
    "ChatResult",
    "chat",
    "chat_with_session",
    "list_free_models",
    "main",
]


def main():
    """独立运行入口"""
    from .main import main as _main
    _main()
