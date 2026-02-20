import subprocess
import threading
from typing import Optional, Tuple, List, Any
from dataclasses import dataclass

PYAUTOGUI_AVAILABLE = True
PIL_AVAILABLE = True
WIN32_AVAILABLE = True


def _get_pyautogui():
    global PYAUTOGUI_AVAILABLE
    if not PYAUTOGUI_AVAILABLE:
        return None
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
        return pyautogui
    except ImportError:
        PYAUTOGUI_AVAILABLE = False
        return None


def _get_pil():
    global PIL_AVAILABLE
    if not PIL_AVAILABLE:
        return None
    try:
        from PIL import Image
        import io
        return Image, io
    except ImportError:
        PIL_AVAILABLE = False
        return None


def _get_win32():
    global WIN32_AVAILABLE
    if not WIN32_AVAILABLE:
        return None, None
    try:
        import win32clipboard
        import win32con
        return win32clipboard, win32con
    except ImportError:
        WIN32_AVAILABLE = False
        return None, None


def _get_pywinauto_app():
    try:
        from pywinauto import Application
        return Application
    except ImportError:
        return None


@dataclass
class WindowInfo:
    handle: int
    title: str
    rect: Tuple[int, int, int, int]
    is_visible: bool
    is_enabled: bool


class WindowsAutomation:
    def __init__(self):
        pass

    def mouse_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> bool:
        pyautogui = _get_pyautogui()
        if pyautogui is None:
            return False
        try:
            pyautogui.click(x=x, y=y, button=button, clicks=clicks)
            return True
        except Exception:
            return False

    def mouse_double_click(self, x: int, y: int, button: str = "left") -> bool:
        return self.mouse_click(x, y, button, clicks=2)

    def mouse_right_click(self, x: int, y: int) -> bool:
        return self.mouse_click(x, y, button="right")

    def mouse_move(self, x: int, y: int, duration: float = 0.0) -> bool:
        pyautogui = _get_pyautogui()
        if pyautogui is None:
            return False
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return True
        except Exception:
            return False

    def mouse_drag(self, start_x: int, start_y: int, end_x: int, end_y: int,
                   duration: float = 0.5, button: str = "left") -> bool:
        pyautogui = _get_pyautogui()
        if pyautogui is None:
            return False
        try:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration, button=button)
            return True
        except Exception:
            return False

    def mouse_scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        pyautogui = _get_pyautogui()
        if pyautogui is None:
            return False
        try:
            pyautogui.scroll(clicks, x, y)
            return True
        except Exception:
            return False

    def keyboard_type(self, text: str, interval: float = 0.0) -> bool:
        pyautogui = _get_pyautogui()
        if pyautogui is None:
            return False
        try:
            if self._contains_non_ascii(text):
                return self._type_via_clipboard(text)
            else:
                pyautogui.typewrite(text, interval=interval)
                return True
        except Exception:
            return False

    def _contains_non_ascii(self, text: str) -> bool:
        return any(ord(char) > 127 for char in text)

    def _type_via_clipboard(self, text: str) -> bool:
        pyautogui = _get_pyautogui()
        if pyautogui is None:
            return False
        if not self.set_clipboard(text):
            return False
        try:
            pyautogui.hotkey('ctrl', 'v')
            return True
        except Exception:
            return False

    def keyboard_press(self, key: str) -> bool:
        pyautogui = _get_pyautogui()
        if pyautogui is None:
            return False
        try:
            pyautogui.press(key)
            return True
        except Exception:
            return False

    def keyboard_hotkey(self, *keys: str) -> bool:
        pyautogui = _get_pyautogui()
        if pyautogui is None:
            return False
        try:
            pyautogui.hotkey(*keys)
            return True
        except Exception:
            return False

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[bytes]:
        pyautogui = _get_pyautogui()
        result = _get_pil()
        if pyautogui is None or result is None:
            return None
        Image, io = result
        try:
            img = pyautogui.screenshot(region=region)
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()
        except Exception:
            return None

    def get_screen_size(self) -> Tuple[int, int]:
        pyautogui = _get_pyautogui()
        if pyautogui is None:
            return (0, 0)
        return pyautogui.size()

    def get_mouse_position(self) -> Tuple[int, int]:
        pyautogui = _get_pyautogui()
        if pyautogui is None:
            return (0, 0)
        return pyautogui.position()

    def find_window(self, title: str) -> Optional[WindowInfo]:
        Application = _get_pywinauto_app()
        if Application is None:
            return None
        try:
            app = Application(backend="uia").connect(title_re=f".*{title}.*", timeout=5)
            window = app.top_window()
            rect = window.rectangle()
            return WindowInfo(
                handle=window.handle,
                title=window.window_text(),
                rect=(rect.left, rect.top, rect.right, rect.bottom),
                is_visible=window.is_visible(),
                is_enabled=window.is_enabled()
            )
        except Exception:
            return None

    def list_windows(self) -> List[WindowInfo]:
        Application = _get_pywinauto_app()
        if Application is None:
            return []
        try:
            windows = []
            app = Application(backend="uia").connect(timeout=1)
            for window in app.windows():
                try:
                    rect = window.rectangle()
                    windows.append(WindowInfo(
                        handle=window.handle,
                        title=window.window_text(),
                        rect=(rect.left, rect.top, rect.right, rect.bottom),
                        is_visible=window.is_visible(),
                        is_enabled=window.is_enabled()
                    ))
                except Exception:
                    continue
            return windows
        except Exception:
            return []

    def launch_app(self, app_path: str, args: Optional[List[str]] = None) -> bool:
        from loguru import logger
        import shlex
        try:
            # Check if it's a URL (http:// or https://)
            if app_path.startswith(('http://', 'https://')):
                # Use start command with quoted URL to handle special characters like &
                cmd = f'start "" "{app_path}"'
                logger.info(f"[WindowsAutomation] Opening URL: {app_path}")
                subprocess.Popen(cmd, shell=True)
                return True
            else:
                # Regular application launch
                cmd = [app_path]
                if args:
                    cmd.extend(args)
                cmd_str = ' '.join(shlex.quote(str(arg)) for arg in cmd)
                logger.info(f"[WindowsAutomation] Executing: {cmd_str}")
                subprocess.Popen(cmd, shell=False)
                return True
        except Exception as e:
            logger.error(f"[WindowsAutomation] Failed to launch: {e}")
            return False

    def get_clipboard(self) -> str:
        win32clipboard, win32con = _get_win32()
        if win32clipboard is None:
            return ""
        try:
            win32clipboard.OpenClipboard()
            try:
                data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                return data or ""
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            return ""

    def set_clipboard(self, text: str) -> bool:
        win32clipboard, win32con = _get_win32()
        if win32clipboard is None:
            return False
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
                return True
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            return False

    def locate_on_screen(self, image_path: str, confidence: float = 0.9) -> Optional[Tuple[int, int, int, int]]:
        pyautogui = _get_pyautogui()
        if pyautogui is None:
            return None
        try:
            return pyautogui.locateOnScreen(image_path, confidence=confidence)
        except Exception:
            return None

    def wait_for_image(self, image_path: str, timeout: float = 10.0,
                       confidence: float = 0.9) -> Optional[Tuple[int, int, int, int]]:
        pyautogui = _get_pyautogui()
        if pyautogui is None:
            return None
        try:
            return pyautogui.locateOnScreen(image_path, confidence=confidence,
                                            minSearchTime=timeout)
        except Exception:
            return None


class WindowsBridge:
    DEFAULT_PORT = 9527
    
    def __init__(self, port: int = None):
        from .ipc_server import IPCServer
        self._port = port or self.DEFAULT_PORT
        self._ipc_server = IPCServer(port=self._port)
        self._automation = WindowsAutomation()
        self._register_handlers()

    @property
    def port(self) -> int:
        return self._port

    def update_port(self, port: int) -> bool:
        """Update the bridge port. Requires restart to take effect."""
        if port == self._port:
            return True
        was_running = self.is_running
        if was_running:
            self.stop()
        self._port = port
        self._ipc_server = IPCServer(port=self._port)
        self._register_handlers()
        if was_running:
            return self.start()
        return True

    def _register_handlers(self):
        self._ipc_server.register_handler("mouse_click", self._handle_mouse_click)
        self._ipc_server.register_handler("mouse_move", self._handle_mouse_move)
        self._ipc_server.register_handler("mouse_drag", self._handle_mouse_drag)
        self._ipc_server.register_handler("mouse_scroll", self._handle_mouse_scroll)
        self._ipc_server.register_handler("keyboard_type", self._handle_keyboard_type)
        self._ipc_server.register_handler("keyboard_press", self._handle_keyboard_press)
        self._ipc_server.register_handler("keyboard_hotkey", self._handle_keyboard_hotkey)
        self._ipc_server.register_handler("screenshot", self._handle_screenshot)
        self._ipc_server.register_handler("find_window", self._handle_find_window)
        self._ipc_server.register_handler("launch_app", self._handle_launch_app)
        self._ipc_server.register_handler("get_clipboard", self._handle_get_clipboard)
        self._ipc_server.register_handler("set_clipboard", self._handle_set_clipboard)
        self._ipc_server.register_handler("get_screen_size", self._handle_get_screen_size)
        self._ipc_server.register_handler("get_mouse_position", self._handle_get_mouse_position)

    def start(self) -> bool:
        return self._ipc_server.start()

    def stop(self):
        self._ipc_server.stop()

    def _handle_mouse_click(self, params: dict) -> dict:
        x = params.get("x", 0)
        y = params.get("y", 0)
        button = params.get("button", "left")
        clicks = params.get("clicks", 1)
        success = self._automation.mouse_click(x, y, button, clicks)
        return {"success": success}

    def _handle_mouse_move(self, params: dict) -> dict:
        x = params.get("x", 0)
        y = params.get("y", 0)
        duration = params.get("duration", 0.0)
        success = self._automation.mouse_move(x, y, duration)
        return {"success": success}

    def _handle_mouse_drag(self, params: dict) -> dict:
        start_x = params.get("start_x", 0)
        start_y = params.get("start_y", 0)
        end_x = params.get("end_x", 0)
        end_y = params.get("end_y", 0)
        duration = params.get("duration", 0.5)
        button = params.get("button", "left")
        success = self._automation.mouse_drag(start_x, start_y, end_x, end_y, duration, button)
        return {"success": success}

    def _handle_mouse_scroll(self, params: dict) -> dict:
        clicks = params.get("clicks", 0)
        x = params.get("x")
        y = params.get("y")
        success = self._automation.mouse_scroll(clicks, x, y)
        return {"success": success}

    def _handle_keyboard_type(self, params: dict) -> dict:
        text = params.get("text", "")
        interval = params.get("interval", 0.0)
        success = self._automation.keyboard_type(text, interval)
        return {"success": success}

    def _handle_keyboard_press(self, params: dict) -> dict:
        key = params.get("key", "")
        success = self._automation.keyboard_press(key)
        return {"success": success}

    def _handle_keyboard_hotkey(self, params: dict) -> dict:
        keys = params.get("keys", [])
        success = self._automation.keyboard_hotkey(*keys)
        return {"success": success}

    def _handle_screenshot(self, params: dict) -> dict:
        region = params.get("region")
        data = self._automation.screenshot(region)
        if data:
            import base64
            return {"success": True, "data": base64.b64encode(data).decode("utf-8")}
        return {"success": False, "error": "Failed to capture screenshot"}

    def _handle_find_window(self, params: dict) -> dict:
        title = params.get("title", "")
        window = self._automation.find_window(title)
        if window:
            return {
                "success": True,
                "window": {
                    "handle": window.handle,
                    "title": window.title,
                    "rect": window.rect,
                    "is_visible": window.is_visible,
                    "is_enabled": window.is_enabled
                }
            }
        return {"success": False, "error": "Window not found"}

    def _handle_launch_app(self, params: dict) -> dict:
        from loguru import logger
        app_path = params.get("app_path", "")
        args = params.get("args", [])
        logger.info(f"[WindowsBridge] Launching app: {app_path}, args: {args}")
        success = self._automation.launch_app(app_path, args)
        logger.info(f"[WindowsBridge] Launch result: {success}")
        return {"success": success}

    def _handle_get_clipboard(self, params: dict) -> dict:
        text = self._automation.get_clipboard()
        return {"success": True, "text": text}

    def _handle_set_clipboard(self, params: dict) -> dict:
        text = params.get("text", "")
        success = self._automation.set_clipboard(text)
        return {"success": success}

    def _handle_get_screen_size(self, params: dict) -> dict:
        size = self._automation.get_screen_size()
        return {"success": True, "width": size[0], "height": size[1]}

    def _handle_get_mouse_position(self, params: dict) -> dict:
        pos = self._automation.get_mouse_position()
        return {"success": True, "x": pos[0], "y": pos[1]}

    @property
    def is_running(self) -> bool:
        return self._ipc_server.is_running

    @property
    def connected_clients(self) -> int:
        return self._ipc_server.connected_clients

    def get_status(self) -> dict:
        return {
            "running": self.is_running,
            "port": self._port,
            "connected_clients": self.connected_clients
        }

    def get_connected_clients_info(self) -> list:
        return self._ipc_server.get_connected_clients_info()

    def notify_port_change(self, new_port: int) -> None:
        self._ipc_server.notify_port_change(new_port)
