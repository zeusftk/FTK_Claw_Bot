import subprocess
import threading
from typing import Optional, Tuple, List
from dataclasses import dataclass

from .action_router import ActionRouter
from .ipc_server import IPCServer
from ..bridge.protocol import TargetType

PYAUTOGUI_AVAILABLE = True
PIL_AVAILABLE = True
WIN32_AVAILABLE = True
PLAYWRIGHT_AVAILABLE = True


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


def _get_web_automation():
    global PLAYWRIGHT_AVAILABLE
    if not PLAYWRIGHT_AVAILABLE:
        return None
    try:
        from .web_automation import WebAutomation
        return WebAutomation
    except ImportError:
        PLAYWRIGHT_AVAILABLE = False
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
            # URL 处理：使用 Playwright
            if app_path.startswith(('http://', 'https://')):
                return self._launch_url(app_path, args)
            
            # 白名单检查
            if not self._check_whitelist(app_path):
                logger.warning(f"[WindowsAutomation] App not in whitelist: {app_path}")
                return False
            
            # 获取实际路径（可能是别名）
            actual_path = self._get_whitelist_path(app_path)
            if actual_path:
                app_path = actual_path
            
            # 普通应用启动
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

    def _launch_url(self, url: str, params: Optional[List[str]] = None) -> bool:
        """
        使用 Playwright 打开 URL
        
        Args:
            url: 要打开的 URL
            params: 可选参数（目前未使用）
        
        Returns:
            是否成功
        """
        from loguru import logger
        
        WebAutomation = _get_web_automation()
        if WebAutomation is None:
            logger.warning("[WindowsAutomation] Playwright not available, falling back to system browser")
            # 降级到系统浏览器
            cmd = f'start "" "{url}"'
            subprocess.Popen(cmd, shell=True)
            return True
        
        try:
            web = self._get_or_create_web_automation()
            if web is None:
                logger.error("[WindowsAutomation] Failed to create WebAutomation instance")
                return False
            
            # 启动浏览器（有头模式，固定窗口大小）
            if not web.is_started:
                from ..constants import WebAutomation as WebConfig
                if not web.start(
                    headless=False,  # 有头模式
                    viewport={"width": WebConfig.VIEWPORT_WIDTH, "height": WebConfig.VIEWPORT_HEIGHT}
                ):
                    logger.error("[WindowsAutomation] Failed to start browser")
                    return False
            
            # 提取域名
            domain = self._extract_domain(url)
            
            # 加载已保存的 cookies
            if domain:
                load_result = web.load_cookies(domain)
                if load_result.get("success"):
                    logger.info(f"[WindowsAutomation] Loaded {load_result.get('count', 0)} cookies for {domain}")
            
            # 导航到 URL
            nav_result = web.navigate(url)
            
            if nav_result.get("success"):
                logger.info(f"[WindowsAutomation] Opened URL in Playwright: {url}")
                
                # 保存 cookies
                if domain:
                    save_result = web.save_cookies(domain)
                    if save_result.get("success"):
                        logger.info(f"[WindowsAutomation] Saved {save_result.get('count', 0)} cookies for {domain}")
                
                return True
            else:
                logger.error(f"[WindowsAutomation] Navigation failed: {nav_result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"[WindowsAutomation] Failed to launch URL: {e}")
            return False

    def _get_or_create_web_automation(self):
        """获取或创建 WebAutomation 实例"""
        if hasattr(self, '_web_automation') and self._web_automation is not None:
            return self._web_automation
        
        WebAutomation = _get_web_automation()
        if WebAutomation is None:
            return None
        
        self._web_automation = WebAutomation()
        return self._web_automation

    def _extract_domain(self, url: str) -> str:
        """从 URL 提取域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""

    def _check_whitelist(self, app_name_or_path: str) -> bool:
        """
        检查应用是否在白名单中
        
        Args:
            app_name_or_path: 应用名称或路径
        
        Returns:
            是否允许执行
        """
        try:
            from .app_whitelist import whitelist_manager
            return whitelist_manager.is_allowed(app_name_or_path)
        except Exception as e:
            # 白名单模块不可用时记录错误并拒绝
            from loguru import logger
            logger.error(f"[Whitelist] Failed to check whitelist: {e}")
            return False

    def _get_whitelist_path(self, app_name_or_path: str) -> Optional[str]:
        """
        从白名单获取实际路径
        
        Args:
            app_name_or_path: 应用名称、别名或路径
        
        Returns:
            实际的可执行文件路径
        """
        try:
            from .app_whitelist import whitelist_manager
            return whitelist_manager.get_actual_path(app_name_or_path)
        except Exception:
            return None

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
        self._port = port or self.DEFAULT_PORT
        self._ipc_server = IPCServer(port=self._port)
        self._automation = WindowsAutomation()
        self._web_automation = None
        self._action_router: Optional[ActionRouter] = None
        self._router_lock = threading.Lock()
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
        self._ipc_server.register_handler("execute", self._handle_execute)
        self._ipc_server.register_handler("web_start", self._handle_web_start)
        self._ipc_server.register_handler("web_stop", self._handle_web_stop)
        self._ipc_server.register_handler("web_navigate", self._handle_web_navigate)
        self._ipc_server.register_handler("web_click", self._handle_web_click)
        self._ipc_server.register_handler("web_fill", self._handle_web_fill)
        self._ipc_server.register_handler("web_scroll", self._handle_web_scroll)
        self._ipc_server.register_handler("web_screenshot", self._handle_web_screenshot)
        self._ipc_server.register_handler("web_get_content", self._handle_web_get_content)
        self._ipc_server.register_handler("web_get_url", self._handle_web_get_url)
        self._ipc_server.register_handler("web_get_title", self._handle_web_get_title)
        self._ipc_server.register_handler("web_extract_elements", self._handle_web_extract_elements)
        self._ipc_server.register_handler("web_extract_data", self._handle_web_extract_data)
        self._ipc_server.register_handler("web_get_cookies", self._handle_web_get_cookies)
        self._ipc_server.register_handler("web_set_cookies", self._handle_web_set_cookies)
        self._ipc_server.register_handler("web_login", self._handle_web_login)
        self._ipc_server.register_handler("web_save_session", self._handle_web_save_session)
        self._ipc_server.register_handler("web_load_session", self._handle_web_load_session)
        self._ipc_server.register_handler("web_press", self._handle_web_press)
        self._ipc_server.register_handler("web_type", self._handle_web_type)
        self._ipc_server.register_handler("web_evaluate", self._handle_web_evaluate)
        self._ipc_server.register_handler("web_wait_for_selector", self._handle_web_wait_for_selector)
        self._ipc_server.register_handler("web_go_back", self._handle_web_go_back)
        self._ipc_server.register_handler("web_go_forward", self._handle_web_go_forward)
        self._ipc_server.register_handler("web_refresh", self._handle_web_refresh)

    # Automation handler mapping (class-level constant)
    _AUTOMATION_HANDLERS = {
        "mouse_click": "_handle_mouse_click",
        "mouse_move": "_handle_mouse_move",
        "mouse_drag": "_handle_mouse_drag",
        "mouse_scroll": "_handle_mouse_scroll",
        "keyboard_type": "_handle_keyboard_type",
        "keyboard_press": "_handle_keyboard_press",
        "keyboard_hotkey": "_handle_keyboard_hotkey",
        "screenshot": "_handle_screenshot",
        "find_window": "_handle_find_window",
        "launch_app": "_handle_launch_app",
        "get_clipboard": "_handle_get_clipboard",
        "set_clipboard": "_handle_set_clipboard",
        "get_screen_size": "_handle_get_screen_size",
        "get_mouse_position": "_handle_get_mouse_position",
    }

    def _get_automation_handler(self, action: str):
        """Get handler method for automation action."""
        method_name = self._AUTOMATION_HANDLERS.get(action)
        if method_name:
            return getattr(self, method_name)
        return None

    def _init_action_router(self) -> ActionRouter:
        """Initialize ActionRouter with automation executor (thread-safe)."""
        if self._action_router is None:
            with self._router_lock:
                if self._action_router is None:
                    self._action_router = ActionRouter(
                        automation_executor=self._execute_automation_action
                    )
        return self._action_router

    def _execute_automation_action(self, action: str, params: dict) -> dict:
        """Sync wrapper for automation actions to be used by ActionRouter."""
        handler = self._get_automation_handler(action)
        if handler:
            return handler(params)
        return {"success": False, "error": f"Unknown action: {action}"}

    def _route_action(self, action: str, params: dict) -> dict:
        """
        Route action through ActionRouter if target_type is browser/desktop.
        Otherwise, use existing automation directly for backward compatibility.
        """
        target_type = params.get("target_type", TargetType.GENERIC.value)

        # Check if routing is needed
        if target_type in (TargetType.BROWSER.value, TargetType.DESKTOP.value):
            router = self._init_action_router()
            payload = {
                "action": action,
                "params": params,
                "target_type": target_type
            }
            # Direct sync call - no async bridging needed
            result = router.route(payload)

            # Unwrap the result for backward compatibility
            if result.get("success"):
                return result.get("result", result)
            return result

        # Default: use existing automation handlers
        handler = self._get_automation_handler(action)
        if handler:
            return handler(params)
        return {"success": False, "error": f"Unknown action: {action}"}

    def start(self) -> bool:
        return self._ipc_server.start()

    def stop(self):
        self._ipc_server.stop()
        if self._action_router:
            try:
                self._action_router.shutdown()
            except Exception:
                pass
        if self._web_automation:
            try:
                self._web_automation.stop()
            except Exception:
                pass
            self._web_automation = None

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
        result = self._automation.launch_app(app_path, args)
        logger.info(f"[WindowsBridge] Launch result: {result}")
        
        # 处理不同返回类型：URL 场景返回 dict，普通应用返回 bool
        if isinstance(result, dict):
            return result
        elif result:
            return {"success": True}
        else:
            return {"success": False, "error": "Failed to launch app"}

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

    def _handle_execute(self, params: dict) -> dict:
        action = params.get("action")
        action_params = params.get("params", {})
        target_type = params.get("target_type")
        
        if not action:
            return {"success": False, "error": "Missing 'action' in params"}
        
        if target_type:
            action_params = {**action_params, "target_type": target_type}
        
        return self._route_action(action, action_params)

    def _get_web_automation_instance(self):
        if self._web_automation is None:
            WebAutomation = _get_web_automation()
            if WebAutomation is None:
                return None
            self._web_automation = WebAutomation()
        return self._web_automation

    def _handle_web_start(self, params: dict) -> dict:
        from loguru import logger
        web = self._get_web_automation_instance()
        if web is None:
            return {"success": False, "error": "playwright_not_available", "message": "Playwright is not installed"}
        headless = params.get("headless", True)
        logger.info(f"[WindowsBridge] Starting web automation, headless={headless}")
        result = web.start(headless=headless)
        return {"success": result}

    def _handle_web_stop(self, params: dict) -> dict:
        if self._web_automation is None:
            return {"success": True}
        result = self._web_automation.stop()
        self._web_automation = None
        return {"success": result}

    def _handle_web_navigate(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        url = params.get("url", "")
        wait_until = params.get("wait_until", "domcontentloaded")
        timeout = params.get("timeout", 30000)
        return web.navigate(url, wait_until=wait_until, timeout=timeout)

    def _handle_web_click(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        selector = params.get("selector", "")
        timeout = params.get("timeout", 10000)
        return web.click(selector, timeout=timeout)

    def _handle_web_fill(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        selector = params.get("selector", "")
        value = params.get("value", "")
        timeout = params.get("timeout", 10000)
        return web.fill(selector, value, timeout=timeout)

    def _handle_web_scroll(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        direction = params.get("direction", "down")
        amount = params.get("amount", 500)
        return web.scroll(direction=direction, amount=amount)

    def _handle_web_screenshot(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        selector = params.get("selector")
        full_page = params.get("full_page", False)
        return web.screenshot(selector=selector, full_page=full_page)

    def _handle_web_get_content(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        return web.get_content()

    def _handle_web_get_url(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        return web.get_url()

    def _handle_web_get_title(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        return web.get_title()

    def _handle_web_extract_elements(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        config = params.get("config", {})
        return web.extract_elements(config=config)

    def _handle_web_extract_data(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        selectors = params.get("selectors", [])
        return web.extract_data(selectors=selectors)

    def _handle_web_get_cookies(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        return web.get_cookies()

    def _handle_web_set_cookies(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        cookies = params.get("cookies", [])
        return web.set_cookies(cookies=cookies)

    def _handle_web_login(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        login_type = params.get("type", "form")
        login_params = params.get("params", {})
        
        if login_type == "form":
            return web.login_form(login_params)
        elif login_type == "cookie":
            cookies = login_params.get("cookies", [])
            url = login_params.get("url", "")
            return web.login_with_cookies(cookies, url)
        elif login_type == "qr":
            selector = login_params.get("selector", "")
            return web.get_qr_code(selector)
        else:
            return {"success": False, "error": "unsupported_login_type", "message": f"Unsupported login type: {login_type}"}

    def _handle_web_save_session(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        session_id = params.get("session_id", "")
        return web.save_session(session_id)

    def _handle_web_load_session(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        session_id = params.get("session_id", "")
        return web.load_session(session_id)

    def _handle_web_press(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        key = params.get("key", "")
        return web.press(key)

    def _handle_web_type(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        text = params.get("text", "")
        delay = params.get("delay", 50)
        return web.type_text(text, delay=delay)

    def _handle_web_evaluate(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        script = params.get("script", "")
        return web.evaluate(script)

    def _handle_web_wait_for_selector(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        selector = params.get("selector", "")
        timeout = params.get("timeout", 10000)
        return web.wait_for_selector(selector, timeout=timeout)

    def _handle_web_go_back(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        return web.go_back()

    def _handle_web_go_forward(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        return web.go_forward()

    def _handle_web_refresh(self, params: dict) -> dict:
        web = self._get_web_automation_instance()
        if web is None or not web.is_started:
            return {"success": False, "error": "browser_not_started"}
        return web.refresh()

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
