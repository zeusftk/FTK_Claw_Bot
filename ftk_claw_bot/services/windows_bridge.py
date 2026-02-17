import subprocess
import threading
from typing import Optional, Tuple, List, Any
from dataclasses import dataclass

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import pywinauto
    from pywinauto import Application
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import win32clipboard
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


@dataclass
class WindowInfo:
    handle: int
    title: str
    rect: Tuple[int, int, int, int]
    is_visible: bool
    is_enabled: bool


class WindowsAutomation:
    def __init__(self):
        self._check_dependencies()

    def _check_dependencies(self):
        if not PYAUTOGUI_AVAILABLE:
            print("Warning: pyautogui not available, some features will be disabled")
        if not PYWINAUTO_AVAILABLE:
            print("Warning: pywinauto not available, some features will be disabled")

    def mouse_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> bool:
        if not PYAUTOGUI_AVAILABLE:
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
        if not PYAUTOGUI_AVAILABLE:
            return False
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return True
        except Exception:
            return False

    def mouse_drag(self, start_x: int, start_y: int, end_x: int, end_y: int,
                   duration: float = 0.5, button: str = "left") -> bool:
        if not PYAUTOGUI_AVAILABLE:
            return False
        try:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration, button=button)
            return True
        except Exception:
            return False

    def mouse_scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        if not PYAUTOGUI_AVAILABLE:
            return False
        try:
            pyautogui.scroll(clicks, x, y)
            return True
        except Exception:
            return False

    def keyboard_type(self, text: str, interval: float = 0.0) -> bool:
        if not PYAUTOGUI_AVAILABLE:
            return False
        try:
            pyautogui.typewrite(text, interval=interval)
            return True
        except Exception:
            return False

    def keyboard_press(self, key: str) -> bool:
        if not PYAUTOGUI_AVAILABLE:
            return False
        try:
            pyautogui.press(key)
            return True
        except Exception:
            return False

    def keyboard_hotkey(self, *keys: str) -> bool:
        if not PYAUTOGUI_AVAILABLE:
            return False
        try:
            pyautogui.hotkey(*keys)
            return True
        except Exception:
            return False

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[bytes]:
        if not PYAUTOGUI_AVAILABLE or not PIL_AVAILABLE:
            return None
        try:
            img = pyautogui.screenshot(region=region)
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()
        except Exception:
            return None

    def get_screen_size(self) -> Tuple[int, int]:
        if not PYAUTOGUI_AVAILABLE:
            return (0, 0)
        return pyautogui.size()

    def get_mouse_position(self) -> Tuple[int, int]:
        if not PYAUTOGUI_AVAILABLE:
            return (0, 0)
        return pyautogui.position()

    def find_window(self, title: str) -> Optional[WindowInfo]:
        if not PYWINAUTO_AVAILABLE:
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
        if not PYWINAUTO_AVAILABLE:
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
        try:
            cmd = [app_path]
            if args:
                cmd.extend(args)
            subprocess.Popen(cmd, shell=True)
            return True
        except Exception:
            return False

    def get_clipboard(self) -> str:
        if not WIN32_AVAILABLE:
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
        if not WIN32_AVAILABLE:
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
        if not PYAUTOGUI_AVAILABLE:
            return None
        try:
            return pyautogui.locateOnScreen(image_path, confidence=confidence)
        except Exception:
            return None

    def wait_for_image(self, image_path: str, timeout: float = 10.0,
                       confidence: float = 0.9) -> Optional[Tuple[int, int, int, int]]:
        if not PYAUTOGUI_AVAILABLE:
            return None
        try:
            return pyautogui.locateOnScreen(image_path, confidence=confidence,
                                            minSearchTime=timeout)
        except Exception:
            return None


class WindowsBridge:
    def __init__(self, port: int = 9527):
        from .ipc_server import IPCServer
        self._ipc_server = IPCServer(port=port)
        self._automation = WindowsAutomation()
        self._register_handlers()

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
        app_path = params.get("app_path", "")
        args = params.get("args", [])
        success = self._automation.launch_app(app_path, args)
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
