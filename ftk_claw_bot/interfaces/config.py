from typing import Protocol, Optional, Dict, Set
from ..models import NanobotConfig


class IConfigManager(Protocol):
    def load(self, valid_distro_names: Optional[Set[str]] = None) -> Dict[str, NanobotConfig]:
        ...
    
    def get(self, name: str) -> Optional[NanobotConfig]:
        ...
    
    def save(self, config: NanobotConfig) -> bool:
        ...
    
    def delete(self, name: str) -> bool:
        ...
    
    def get_all(self) -> Dict[str, NanobotConfig]:
        ...
