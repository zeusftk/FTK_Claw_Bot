from typing import Protocol, Optional, Dict, Set
from ..models import ClawbotConfig


class IConfigManager(Protocol):
    def load(self, valid_distro_names: Optional[Set[str]] = None) -> Dict[str, ClawbotConfig]:
        ...
    
    def get(self, name: str) -> Optional[ClawbotConfig]:
        ...
    
    def save(self, config: ClawbotConfig) -> bool:
        ...
    
    def delete(self, name: str) -> bool:
        ...
    
    def get_all(self) -> Dict[str, ClawbotConfig]:
        ...
