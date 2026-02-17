from typing import Protocol, Optional, Dict, List
from ..models import NanobotConfig, NanobotStatus


class INanobotController(Protocol):
    def start(self, config: NanobotConfig) -> bool:
        ...
    
    def stop(self, name: str) -> bool:
        ...
    
    def get_status(self, name: str) -> NanobotStatus:
        ...
    
    def get_instances(self) -> Dict[str, any]:
        ...
    
    def add_log_callback(self, callback) -> None:
        ...
    
    def add_status_callback(self, callback) -> None:
        ...
