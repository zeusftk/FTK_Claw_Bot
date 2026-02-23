from .ipc_server import IPCServer
from .windows_bridge import WindowsBridge, WindowsAutomation
from .monitor_service import MonitorService
from .nanobot_chat_client import NanobotChatClient, ConnectionStatus
from .wsl_state_service import WSLStateService, init_wsl_state_service, get_wsl_state_service

from .service_registry import (
    ServiceRegistry, register_service, ServiceInfo, ServiceStatus
)

from .embedding import register_embedding_service, EmbeddingService
from . import clawbot_upgrader

register_embedding_service()

__all__ = [
    "IPCServer",
    "WindowsBridge",
    "WindowsAutomation",
    "MonitorService",
    "NanobotChatClient",
    "ConnectionStatus",
    "WSLStateService",
    "init_wsl_state_service",
    "get_wsl_state_service",
    "ServiceRegistry",
    "register_service",
    "ServiceInfo",
    "ServiceStatus",
    "register_embedding_service",
    "EmbeddingService",
]
