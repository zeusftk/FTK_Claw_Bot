import socket
from typing import Dict, Optional, Set
from loguru import logger


class PortManager:
    DEFAULT_START_PORT = 18888
    DEFAULT_END_PORT = 18890

    def __init__(self, start_port: int = DEFAULT_START_PORT, end_port: int = DEFAULT_END_PORT):
        self._start_port = start_port
        self._end_port = end_port
        self._assigned_ports: Dict[str, int] = {}
        self._used_ports: Set[int] = set()

    def is_port_available(self, port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return True
        except OSError:
            return False

    def find_available_port(self) -> Optional[int]:
        for port in range(self._start_port, self._end_port + 1):
            if port not in self._used_ports and self.is_port_available(port):
                return port
        logger.error(f"No available ports in range {self._start_port}-{self._end_port}")
        return None

    def assign_port(self, key: str) -> Optional[int]:
        if key in self._assigned_ports:
            return self._assigned_ports[key]

        port = self.find_available_port()
        if port:
            self._assigned_ports[key] = port
            self._used_ports.add(port)
            logger.info(f"Assigned port {port} for {key}")
        return port

    def release_port(self, key: str) -> bool:
        if key in self._assigned_ports:
            port = self._assigned_ports.pop(key)
            self._used_ports.discard(port)
            logger.info(f"Released port {port} from {key}")
            return True
        return False

    def get_assigned_port(self, key: str) -> Optional[int]:
        return self._assigned_ports.get(key)

    def get_all_assigned_ports(self) -> Dict[str, int]:
        return self._assigned_ports.copy()

    def reserve_port(self, key: str, port: int) -> bool:
        if port in self._used_ports:
            logger.warning(f"Port {port} is already in use")
            return False
        
        if key in self._assigned_ports:
            old_port = self._assigned_ports[key]
            self._used_ports.discard(old_port)
        
        self._assigned_ports[key] = port
        self._used_ports.add(port)
        logger.info(f"Reserved port {port} for {key}")
        return True

    def reset(self):
        self._assigned_ports.clear()
        self._used_ports.clear()
        logger.info("Port manager reset")
