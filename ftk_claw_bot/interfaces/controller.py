from typing import Protocol, Optional, Dict, List
from ..models import ClawbotConfig, ClawbotStatus


class IClawbotController(Protocol):
    def start(self, config: ClawbotConfig) -> bool:
        ...
    
    def stop(self, name: str) -> bool:
        ...
    
    def get_status(self, name: str) -> ClawbotStatus:
        ...
    
    def get_instances(self) -> Dict[str, any]:
        ...
    
    def add_log_callback(self, callback) -> None:
        ...
    
    def add_status_callback(self, callback) -> None:
        ...
