from typing import Protocol, List, Optional
from ..models import WSLDistro


class IWSLManager(Protocol):
    def list_distros(self) -> List[WSLDistro]:
        ...
    
    def get_distro(self, name: str) -> Optional[WSLDistro]:
        ...
    
    def start_distro(self, name: str) -> bool:
        ...
    
    def stop_distro(self, name: str) -> bool:
        ...
    
    def execute_command(self, distro_name: str, command: str, timeout: int = 30) -> any:
        ...
