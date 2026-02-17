import socket
import json
import threading
from typing import Optional, Callable, Dict
from dataclasses import dataclass


@dataclass
class IPCMessage:
    version: str = "1.0"
    msg_type: str = "request"
    msg_id: str = ""
    timestamp: str = ""
    payload: dict = None

    def to_json(self) -> str:
        return json.dumps({
            "version": self.version,
            "type": self.msg_type,
            "id": self.msg_id,
            "timestamp": self.timestamp,
            "payload": self.payload or {}
        })

    @classmethod
    def from_json(cls, json_str: str) -> "IPCMessage":
        data = json.loads(json_str)
        return cls(
            version=data.get("version", "1.0"),
            msg_type=data.get("type", "request"),
            msg_id=data.get("id", ""),
            timestamp=data.get("timestamp", ""),
            payload=data.get("payload", {})
        )


class IPCServer:
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 9527
    BUFFER_SIZE = 65536

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self._host = host
        self._port = port
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._server_thread: Optional[threading.Thread] = None
        self._handlers: Dict[str, Callable] = {}
        self._clients: list = []

    def register_handler(self, action: str, handler: Callable):
        self._handlers[action] = handler

    def unregister_handler(self, action: str):
        if action in self._handlers:
            del self._handlers[action]

    def start(self) -> bool:
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self._host, self._port))
            self._socket.listen(5)
            self._running = True

            self._server_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._server_thread.start()
            return True
        except Exception as e:
            print(f"Failed to start IPC server: {e}")
            return False

    def stop(self):
        self._running = False

        for client in self._clients:
            try:
                client.close()
            except Exception:
                pass
        self._clients.clear()

        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

        if self._server_thread:
            self._server_thread.join(timeout=2.0)
            self._server_thread = None

    def _accept_loop(self):
        while self._running:
            try:
                self._socket.settimeout(1.0)
                client_socket, address = self._socket.accept()
                self._clients.append(client_socket)

                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                thread.start()
            except socket.timeout:
                continue
            except Exception:
                if self._running:
                    continue
                break

    def _handle_client(self, client_socket: socket.socket, address):
        buffer = ""

        while self._running:
            try:
                client_socket.settimeout(1.0)
                data = client_socket.recv(self.BUFFER_SIZE)
                if not data:
                    break

                buffer += data.decode("utf-8")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        response = self._process_message(line.strip())
                        client_socket.sendall((response + "\n").encode("utf-8"))

            except socket.timeout:
                continue
            except Exception:
                break

        if client_socket in self._clients:
            self._clients.remove(client_socket)
        try:
            client_socket.close()
        except Exception:
            pass

    def _process_message(self, message_str: str) -> str:
        try:
            message = IPCMessage.from_json(message_str)
            action = message.payload.get("action", "")

            if action in self._handlers:
                result = self._handlers[action](message.payload.get("params", {}))
                response = IPCMessage(
                    msg_type="response",
                    msg_id=message.msg_id,
                    payload={"success": True, "result": result}
                )
            else:
                response = IPCMessage(
                    msg_type="response",
                    msg_id=message.msg_id,
                    payload={"success": False, "error": f"Unknown action: {action}"}
                )

            return response.to_json()
        except Exception as e:
            response = IPCMessage(
                msg_type="response",
                payload={"success": False, "error": str(e)}
            )
            return response.to_json()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def address(self) -> tuple:
        return (self._host, self._port)
