import socket
import json
import uuid
import threading
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any


class IPCMessage:
    VERSION = "1.0"

    def __init__(
        self,
        msg_type: str = "request",
        msg_id: str = "",
        action: str = "",
        params: Optional[Dict[str, Any]] = None,
        result: Any = None,
        error: Optional[str] = None,
    ):
        self.version = self.VERSION
        self.msg_type = msg_type
        self.msg_id = msg_id or str(uuid.uuid4())
        self.timestamp = datetime.now().isoformat()
        self.action = action
        self.params = params or {}
        self.result = result
        self.error = error

    def to_json(self) -> str:
        data = {
            "version": self.version,
            "type": self.msg_type,
            "id": self.msg_id,
            "timestamp": self.timestamp,
            "payload": {
                "action": self.action,
                "params": self.params,
            },
        }
        if self.result is not None:
            data["payload"]["result"] = self.result
        if self.error:
            data["payload"]["error"] = self.error
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> "IPCMessage":
        data = json.loads(json_str)
        payload = data.get("payload", {})
        return cls(
            msg_type=data.get("type", "request"),
            msg_id=data.get("id", ""),
            action=payload.get("action", ""),
            params=payload.get("params", {}),
            result=payload.get("result"),
            error=payload.get("error"),
        )


class BridgeAgent:
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 9527
    RECONNECT_DELAY = 5.0
    KEEPALIVE_INTERVAL = 30.0

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        on_connected: Optional[Callable] = None,
        on_disconnected: Optional[Callable] = None,
    ):
        self._host = host
        self._port = port
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._connected = False
        self._reconnect_thread: Optional[threading.Thread] = None
        self._keepalive_thread: Optional[threading.Thread] = None
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._pending_requests: Dict[str, threading.Event] = {}
        self._responses: Dict[str, Any] = {}

    def start(self) -> bool:
        self._running = True
        self._reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self._reconnect_thread.start()
        return True

    def stop(self):
        self._running = False
        self._disconnect()
        if self._reconnect_thread:
            self._reconnect_thread.join(timeout=2.0)
        if self._keepalive_thread:
            self._keepalive_thread.join(timeout=2.0)

    def _connect(self) -> bool:
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(10.0)
            self._socket.connect((self._host, self._port))
            self._connected = True
            print(f"Connected to Windows bridge at {self._host}:{self._port}")

            if self._on_connected:
                self._on_connected()

            self._start_receive_loop()
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            self._connected = False
            return False

    def _disconnect(self):
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        self._connected = False
        if self._on_disconnected:
            self._on_disconnected()

    def _reconnect_loop(self):
        while self._running:
            if not self._connected:
                if self._connect():
                    self._start_keepalive()
                else:
                    time.sleep(self.RECONNECT_DELAY)
            else:
                time.sleep(self.RECONNECT_DELAY)

    def _start_keepalive(self):
        if self._keepalive_thread and self._keepalive_thread.is_alive():
            return
        self._keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
        self._keepalive_thread.start()

    def _keepalive_loop(self):
        while self._running and self._connected:
            time.sleep(self.KEEPALIVE_INTERVAL)
            if self._connected:
                try:
                    self.send_request("ping", {}, timeout=5.0)
                except Exception:
                    pass

    def _start_receive_loop(self):
        thread = threading.Thread(target=self._receive_loop, daemon=True)
        thread.start()

    def _receive_loop(self):
        buffer = ""
        while self._running and self._connected:
            try:
                self._socket.settimeout(1.0)
                data = self._socket.recv(65536)
                if not data:
                    break
                buffer += data.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self._handle_response(line.strip())
            except socket.timeout:
                continue
            except Exception:
                break
        self._connected = False
        if self._on_disconnected:
            self._on_disconnected()

    def _handle_response(self, message_str: str):
        try:
            message = IPCMessage.from_json(message_str)
            if message.msg_id in self._pending_requests:
                event = self._pending_requests.pop(message.msg_id)
                self._responses[message.msg_id] = message
                event.set()
        except Exception as e:
            print(f"Error handling response: {e}")

    def send_request(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Optional[Dict[str, Any]]:
        if not self._connected:
            return None

        request_id = str(uuid.uuid4())
        event = threading.Event()
        self._pending_requests[request_id] = event

        message = IPCMessage(
            msg_type="request",
            msg_id=request_id,
            action=action,
            params=params or {},
        )

        try:
            self._socket.sendall((message.to_json() + "\n").encode("utf-8"))
            if event.wait(timeout=timeout):
                response = self._responses.pop(request_id, None)
                if response:
                    if response.error:
                        raise Exception(response.error)
                    return response.result
        except Exception as e:
            print(f"Request failed: {e}")
        finally:
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]
        return None

    def mouse_click(self, x: int, y: int, button: str = "left") -> bool:
        result = self.send_request("mouse_click", {"x": x, "y": y, "button": button})
        return result.get("success", False) if result else False

    def mouse_move(self, x: int, y: int, duration: float = 0.0) -> bool:
        result = self.send_request("mouse_move", {"x": x, "y": y, "duration": duration})
        return result.get("success", False) if result else False

    def mouse_scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        params = {"clicks": clicks}
        if x is not None:
            params["x"] = x
        if y is not None:
            params["y"] = y
        result = self.send_request("mouse_scroll", params)
        return result.get("success", False) if result else False

    def keyboard_type(self, text: str, interval: float = 0.0) -> bool:
        result = self.send_request("keyboard_type", {"text": text, "interval": interval})
        return result.get("success", False) if result else False

    def keyboard_press(self, key: str) -> bool:
        result = self.send_request("keyboard_press", {"key": key})
        return result.get("success", False) if result else False

    def keyboard_hotkey(self, *keys: str) -> bool:
        result = self.send_request("keyboard_hotkey", {"keys": list(keys)})
        return result.get("success", False) if result else False

    def screenshot(self, region: Optional[tuple] = None) -> Optional[bytes]:
        params = {}
        if region:
            params["region"] = list(region)
        result = self.send_request("screenshot", params)
        if result and result.get("success"):
            import base64
            return base64.b64decode(result.get("data", ""))
        return None

    def find_window(self, title: str) -> Optional[Dict[str, Any]]:
        result = self.send_request("find_window", {"title": title})
        if result and result.get("success"):
            return result.get("window")
        return None

    def launch_app(self, app_path: str, args: Optional[list] = None) -> bool:
        params = {"app_path": app_path}
        if args:
            params["args"] = args
        result = self.send_request("launch_app", params)
        return result.get("success", False) if result else False

    def get_clipboard(self) -> str:
        result = self.send_request("get_clipboard", {})
        return result.get("text", "") if result else ""

    def set_clipboard(self, text: str) -> bool:
        result = self.send_request("set_clipboard", {"text": text})
        return result.get("success", False) if result else False

    def get_screen_size(self) -> tuple:
        result = self.send_request("get_screen_size", {})
        if result and result.get("success"):
            return (result.get("width", 0), result.get("height", 0))
        return (0, 0)

    def get_mouse_position(self) -> tuple:
        result = self.send_request("get_mouse_position", {})
        if result and result.get("success"):
            return (result.get("x", 0), result.get("y", 0))
        return (0, 0)

    @property
    def is_connected(self) -> bool:
        return self._connected


def main():
    import argparse

    parser = argparse.ArgumentParser(description="FTK Bot Bridge Agent")
    parser.add_argument("--host", default="127.0.0.1", help="Windows bridge host")
    parser.add_argument("--port", type=int, default=9527, help="Windows bridge port")
    args = parser.parse_args()

    print(f"Starting Bridge Agent, connecting to {args.host}:{args.port}")

    agent = BridgeAgent(host=args.host, port=args.port)

    def on_connected():
        print("Connected to Windows bridge")

    def on_disconnected():
        print("Disconnected from Windows bridge")

    agent._on_connected = on_connected
    agent._on_disconnected = on_disconnected
    agent.start()

    try:
        while agent.is_connected:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        agent.stop()


if __name__ == "__main__":
    main()
