# -*- coding: utf-8 -*-
import socket
import json
import threading
import uuid
from datetime import datetime
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
    DEFAULT_HOST = "0.0.0.0"
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
        self._client_info: Dict[socket.socket, dict] = {}
        self._lock = threading.Lock()

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

        with self._lock:
            for client in self._clients:
                try:
                    client.close()
                except Exception:
                    pass
            self._clients.clear()
            self._client_info.clear()

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
        from loguru import logger
        while self._running:
            try:
                self._socket.settimeout(1.0)
                client_socket, address = self._socket.accept()
                logger.info(f"[IPC] 新客户端连接: {address}")
                with self._lock:
                    self._clients.append(client_socket)
                    self._client_info[client_socket] = {
                        "address": address,
                        "distro_name": None,
                        "clawbot_name": None,
                        "workspace": None,
                        "connected_at": datetime.now().isoformat()
                    }

                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    logger.debug(f"[IPC] accept 异常: {e}")
                    continue
                break

    def _handle_client(self, client_socket: socket.socket, address):
        buffer = ""
        
        self._request_client_identify(client_socket)

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
                        response = self._process_message_with_client(line.strip(), client_socket)
                        client_socket.sendall((response + "\n").encode("utf-8"))

            except socket.timeout:
                continue
            except Exception:
                break

        with self._lock:
            if client_socket in self._clients:
                self._clients.remove(client_socket)
            if client_socket in self._client_info:
                del self._client_info[client_socket]
        try:
            client_socket.close()
        except Exception:
            pass

    def _request_client_identify(self, client_socket: socket.socket):
        """请求客户端发送身份信息"""
        request = {
            "version": "1.0",
            "type": "request",
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "payload": {"action": "request_identify"}
        }
        try:
            client_socket.sendall((json.dumps(request) + "\n").encode("utf-8"))
        except Exception:
            pass

    def _process_message_with_client(self, message_str: str, client_socket: socket.socket) -> str:
        from loguru import logger
        try:
            message = IPCMessage.from_json(message_str)
            action = message.payload.get("action", "")
            params = message.payload.get("params", {})

            # Log all requests for debugging
            logger.info(f"[IPC] Received request - action: {action}, params: {params}")

            if action == "identify":
                return self._handle_identify(client_socket, message, params)

            if action in self._handlers:
                result = self._handlers[action](params)
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

    def _handle_identify(self, client_socket: socket.socket, message: IPCMessage, params: dict) -> str:
        from loguru import logger
        with self._lock:
            if client_socket in self._client_info:
                self._client_info[client_socket].update({
                    "distro_name": params.get("distro_name"),
                    "clawbot_name": params.get("clawbot_name"),
                    "workspace": params.get("workspace"),
                    "identified_at": datetime.now().isoformat()
                })
                logger.info(f"[IPC] 客户端识别: {self._client_info[client_socket]}")

        response = IPCMessage(
            msg_type="response",
            msg_id=message.msg_id,
            payload={"success": True, "result": {"identified": True}}
        )
        return response.to_json()

    def notify_port_change(self, new_port: int) -> None:
        notification = {
            "type": "notification",
            "action": "port_changed",
            "data": {"new_port": new_port}
        }
        notification_str = json.dumps(notification) + "\n"

        with self._lock:
            for client_socket in self._clients:
                try:
                    client_socket.sendall(notification_str.encode("utf-8"))
                except Exception:
                    pass

    def get_connected_clients_info(self) -> list:
        from loguru import logger
        with self._lock:
            result = []
            for client_socket in self._clients:
                if self._is_client_connected(client_socket):
                    info = self._client_info.get(client_socket, {})
                    result.append(info.copy())
            logger.debug(f"[IPC] get_connected_clients_info: {len(self._clients)} 个客户端, 返回 {len(result)} 个已连接")
            return result

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def address(self) -> tuple:
        return (self._host, self._port)

    @property
    def connected_clients(self) -> int:
        with self._lock:
            return len([c for c in self._clients if self._is_client_connected(c)])

    def _is_client_connected(self, client_socket: socket.socket) -> bool:
        try:
            client_socket.getpeername()
            return True
        except Exception:
            return False
