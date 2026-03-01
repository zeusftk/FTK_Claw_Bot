# -*- coding: utf-8 -*-
import asyncio
import base64
import json
import os
import random
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

PLAYWRIGHT_AVAILABLE = True


def _get_playwright():
    global PLAYWRIGHT_AVAILABLE
    if not PLAYWRIGHT_AVAILABLE:
        return None
    try:
        from playwright.async_api import async_playwright
        return async_playwright
    except ImportError:
        PLAYWRIGHT_AVAILABLE = False
        return None


@dataclass
class PageElement:
    id: int
    tag: str
    type: str
    action_type: str
    text: str
    selector: str
    location: Dict[str, int]
    is_interactive: bool
    weight: int
    is_primary: bool = True
    duplicate_count: int = 1
    text_group_id: str = ""


@dataclass
class ExtractResult:
    url: str
    title: str
    elements: List[PageElement] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)


class WebAutomation:
    """基于 Playwright 的 Web 自动化类"""

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._page = None
        self._context = None
        self._started = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # 使用统一的 user_data 目录
        from ftk_claw_bot.utils.user_data_dir import user_data
        self._sessions_dir = str(user_data.web_sessions)
        self._cookies_dir = str(user_data.web_cookies)
        self._cookies_domain_dir = str(user_data.web_cookies_domain)
        
        # 确保目录存在
        os.makedirs(self._sessions_dir, exist_ok=True)
        os.makedirs(self._cookies_dir, exist_ok=True)
        os.makedirs(self._cookies_domain_dir, exist_ok=True)

    @property
    def is_started(self) -> bool:
        return self._started and self._browser is not None

    def _ensure_loop(self):
        if self._loop is None or not self._loop.is_running():
            self._loop = asyncio.new_event_loop()
            self._loop_thread = threading.Thread(target=self._run_loop, daemon=True)
            self._loop_thread.start()
            import time
            for _ in range(50):
                if self._loop.is_running():
                    break
                time.sleep(0.1)

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_async(self, coro):
        self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=60)

    def start(self, headless: bool = True, viewport: dict = None) -> bool:
        """
        启动浏览器
        
        Args:
            headless: 是否无头模式（默认 True）
            viewport: 视口大小，默认使用 constants 中定义的固定大小
        
        Returns:
            是否启动成功
        """
        async_playwright = _get_playwright()
        if async_playwright is None:
            return False

        # 使用固定窗口大小
        from ftk_claw_bot.constants import WebAutomation as WebConfig
        viewport = viewport or {
            "width": WebConfig.VIEWPORT_WIDTH,
            "height": WebConfig.VIEWPORT_HEIGHT
        }

        async def _start():
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=headless,
                args=[f"--window-size={viewport['width']},{viewport['height']}"]
            )
            self._context = await self._browser.new_context(
                viewport=viewport
            )
            self._page = await self._context.new_page()
            self._started = True
            return True

        try:
            return self._run_async(_start())
        except Exception as e:
            from loguru import logger
            logger.error(f"[WebAutomation] Failed to start: {e}")
            return False

    def stop(self) -> bool:
        async def _stop():
            if self._page:
                await self._page.close()
                self._page = None
            if self._context:
                await self._context.close()
                self._context = None
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            self._started = False
            return True

        try:
            if self._browser:
                return self._run_async(_stop())
            return True
        except Exception:
            return False

    def navigate(self, url: str, wait_until: str = "domcontentloaded", timeout: int = 30000) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started", "message": "Browser not started"}

        if not url.startswith(("http://", "https://")):
            return {"success": False, "error": "invalid_url", "message": "URL must start with http:// or https://"}

        async def _navigate():
            await self._page.goto(url, wait_until=wait_until, timeout=timeout)
            return await self._get_page_info()

        try:
            result = self._run_async(_navigate())
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": "navigation_failed", "message": str(e)}

    async def _get_page_info(self) -> dict:
        url = self._page.url
        title = await self._page.title()
        return {"url": url, "title": title}

    def click(self, selector: str, timeout: int = 10000) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _click():
            await self._page.click(selector, timeout=timeout)
            await self._page.wait_for_load_state("networkidle", timeout=10000)
            return True

        try:
            self._run_async(_click())
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": "element_not_found", "message": str(e)}

    def fill(self, selector: str, value: str, timeout: int = 10000) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _fill():
            await self._page.fill(selector, value, timeout=timeout)
            return True

        try:
            self._run_async(_fill())
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": "element_not_found", "message": str(e)}

    def scroll(self, direction: str = "down", amount: int = 500) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _scroll():
            if direction == "down":
                await self._page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                await self._page.evaluate(f"window.scrollBy(0, -{amount})")
            return True

        try:
            self._run_async(_scroll())
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": "scroll_failed", "message": str(e)}

    def get_content(self) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _get_content():
            content = await self._page.content()
            return content

        try:
            content = self._run_async(_get_content())
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": "get_content_failed", "message": str(e)}

    def get_url(self) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        try:
            return {"success": True, "url": self._page.url}
        except Exception as e:
            return {"success": False, "error": "get_url_failed", "message": str(e)}

    def get_title(self) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _get_title():
            return await self._page.title()

        try:
            title = self._run_async(_get_title())
            return {"success": True, "title": title}
        except Exception as e:
            return {"success": False, "error": "get_title_failed", "message": str(e)}

    def screenshot(self, selector: Optional[str] = None, full_page: bool = False) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _screenshot():
            if selector:
                element = await self._page.query_selector(selector)
                if element:
                    data = await element.screenshot()
                else:
                    return None
            else:
                data = await self._page.screenshot(full_page=full_page)
            return data

        try:
            data = self._run_async(_screenshot())
            if data is None:
                return {"success": False, "error": "element_not_found"}
            return {"success": True, "data": base64.b64encode(data).decode("utf-8")}
        except Exception as e:
            return {"success": False, "error": "screenshot_failed", "message": str(e)}

    def extract_elements(self, config: Optional[dict] = None) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        config = config or {}
        interactive_weight = config.get("interactive_weight", 100)
        min_area = config.get("min_area", 100)
        include_duplicates = config.get("include_duplicates", False)

        async def _extract():
            title = await self._page.title()
            url = self._page.url

            raw_elements = await self._page.evaluate('''
                function extractElements() {
                    const elements = [];
                    const allElements = document.querySelectorAll('*');
                    
                    allElements.forEach((el, index) => {
                        const rect = el.getBoundingClientRect();
                        const text = el.textContent.trim();
                        
                        if (text && rect.width > 0 && rect.height > 0) {
                            elements.push({
                                tag: el.tagName.toLowerCase(),
                                type: el.type || '',
                                action_type: el.tagName.toLowerCase() === 'a' ? 'click' : 
                                            el.tagName.toLowerCase() === 'input' ? 'fill' : 
                                            el.tagName.toLowerCase() === 'button' ? 'click' : 'none',
                                text: text.substring(0, 200),
                                selector: generateSelector(el),
                                location: {
                                    x: Math.round(rect.left),
                                    y: Math.round(rect.top),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height)
                                },
                                is_interactive: el.tagName.toLowerCase() === 'a' || 
                                               el.tagName.toLowerCase() === 'button' || 
                                               el.tagName.toLowerCase() === 'input' || 
                                               el.tagName.toLowerCase() === 'select' || 
                                               el.tagName.toLowerCase() === 'textarea'
                            });
                        }
                    });
                    
                    function generateSelector(el) {
                        if (el.id) {
                            return '#' + el.id;
                        }
                        if (el.className && typeof el.className === 'string') {
                            return '.' + el.className.split(' ').filter(c => c).join('.');
                        }
                        return el.tagName.toLowerCase();
                    }
                    
                    return elements;
                }
                extractElements();
            ''')

            elements_with_weight = []
            for el in raw_elements:
                loc = el['location']
                area = loc['width'] * loc['height']
                if area < min_area:
                    continue

                weight = (interactive_weight if el['is_interactive'] else 0) + area
                el['weight'] = weight
                elements_with_weight.append(el)

            elements_with_weight.sort(key=lambda x: x['weight'], reverse=True)

            text_groups = {}
            for el in elements_with_weight:
                text = el['text']
                if text not in text_groups:
                    text_groups[text] = []
                text_groups[text].append(el)

            result_elements = []
            group_id = 0
            for text, group in text_groups.items():
                group_id += 1
                group.sort(key=lambda x: x['weight'], reverse=True)

                for i, el in enumerate(group):
                    result_elements.append({
                        'id': len(result_elements) + 1,
                        'tag': el['tag'],
                        'type': el['type'],
                        'action_type': el['action_type'],
                        'text': el['text'],
                        'selector': el['selector'],
                        'location': el['location'],
                        'is_interactive': el['is_interactive'],
                        'weight': el['weight'],
                        'is_primary': (i == 0),
                        'duplicate_count': len(group),
                        'text_group_id': f"g_{group_id}"
                    })

            if not include_duplicates:
                result_elements = [e for e in result_elements if e['is_primary']]

            for i, el in enumerate(result_elements):
                el['id'] = i + 1

            interactive_count = sum(1 for e in result_elements if e['is_interactive'])

            return {
                'url': url,
                'title': title,
                'elements': result_elements,
                'summary': {
                    'total': len(result_elements),
                    'interactive': interactive_count,
                    'unique_text': len(text_groups)
                }
            }

        try:
            result = self._run_async(_extract())
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": "extract_failed", "message": str(e)}

    def extract_data(self, selectors: List[Dict[str, str]]) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _extract():
            data = {}
            for item in selectors:
                name = item.get("name")
                selector = item.get("selector")
                try:
                    elements = await self._page.query_selector_all(selector)
                    if elements:
                        if len(elements) == 1:
                            text = await elements[0].text_content()
                            data[name] = text.strip() if text else None
                        else:
                            texts = []
                            for el in elements:
                                text = await el.text_content()
                                texts.append(text.strip() if text else "")
                            data[name] = texts
                    else:
                        data[name] = None
                except Exception:
                    data[name] = None
            return data

        try:
            data = self._run_async(_extract())
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": "extract_failed", "message": str(e)}

    def get_cookies(self) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _get_cookies():
            return await self._context.cookies()

        try:
            cookies = self._run_async(_get_cookies())
            return {"success": True, "cookies": cookies}
        except Exception as e:
            return {"success": False, "error": "get_cookies_failed", "message": str(e)}

    def set_cookies(self, cookies: List[dict]) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _set_cookies():
            await self._context.add_cookies(cookies)
            return True

        try:
            self._run_async(_set_cookies())
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": "set_cookies_failed", "message": str(e)}

    def save_session(self, session_id: str) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _save():
            cookies = await self._context.cookies()
            storage = await self._context.storage_state()
            session_data = {
                "cookies": cookies,
                "storage": storage,
                "created_at": datetime.now().isoformat()
            }
            session_file = os.path.join(self._sessions_dir, f"{session_id}.json")
            with open(session_file, "w") as f:
                json.dump(session_data, f)
            return True

        try:
            self._run_async(_save())
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": "save_session_failed", "message": str(e)}

    def load_session(self, session_id: str) -> dict:
        session_file = os.path.join(self._sessions_dir, f"{session_id}.json")
        if not os.path.exists(session_file):
            return {"success": False, "error": "session_not_found"}

        try:
            with open(session_file, "r") as f:
                session_data = json.load(f)

            if not self.is_started:
                return {"success": False, "error": "browser_not_started"}

            async def _load():
                cookies = session_data.get("cookies", [])
                await self._context.add_cookies(cookies)
                return True

            self._run_async(_load())
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": "load_session_failed", "message": str(e)}

    # ========================================
    # Cookie 持久化方法
    # ========================================

    def save_cookies(self, domain: str = None) -> dict:
        """
        保存当前 cookies 到文件
        
        Args:
            domain: 指定域名则只保存该域名的 cookies，否则保存全局 cookies
        
        Returns:
            操作结果
        """
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _get_cookies():
            return await self._context.cookies()

        try:
            cookies = self._run_async(_get_cookies())
            
            if domain:
                # 只保存指定域名的 cookies
                cookies = [c for c in cookies if domain in c.get("domain", "")]
                cookie_file = os.path.join(self._cookies_domain_dir, f"{domain}.json")
            else:
                # 保存全局 cookies
                cookie_file = os.path.join(self._cookies_dir, "global_cookies.json")
            
            cookie_data = {
                "cookies": cookies,
                "saved_at": datetime.now().isoformat(),
                "domain": domain
            }
            
            with open(cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookie_data, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "count": len(cookies),
                "file": cookie_file
            }
        except Exception as e:
            return {"success": False, "error": "save_cookies_failed", "message": str(e)}

    def load_cookies(self, domain: str = None) -> dict:
        """
        从文件加载 cookies
        
        Args:
            domain: 指定域名则加载该域名的 cookies，否则加载全局 cookies
        
        Returns:
            操作结果
        """
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        try:
            if domain:
                cookie_file = os.path.join(self._cookies_domain_dir, f"{domain}.json")
            else:
                cookie_file = os.path.join(self._cookies_dir, "global_cookies.json")
            
            if not os.path.exists(cookie_file):
                return {"success": False, "error": "cookies_not_found", "message": f"No cookies file for {domain or 'global'}"}
            
            with open(cookie_file, "r", encoding="utf-8") as f:
                cookie_data = json.load(f)
            
            cookies = cookie_data.get("cookies", [])
            
            async def _add_cookies():
                await self._context.add_cookies(cookies)
                return True
            
            self._run_async(_add_cookies())
            
            return {
                "success": True,
                "count": len(cookies),
                "loaded_from": cookie_file
            }
        except Exception as e:
            return {"success": False, "error": "load_cookies_failed", "message": str(e)}

    def clear_cookies(self, domain: str = None) -> dict:
        """
        清除 cookies 文件
        
        Args:
            domain: 指定域名则清除该域名的 cookies 文件，否则清除全局 cookies 文件
        
        Returns:
            操作结果
        """
        try:
            if domain:
                cookie_file = os.path.join(self._cookies_domain_dir, f"{domain}.json")
            else:
                cookie_file = os.path.join(self._cookies_dir, "global_cookies.json")
            
            if os.path.exists(cookie_file):
                os.remove(cookie_file)
                return {"success": True, "message": f"Deleted {cookie_file}"}
            else:
                return {"success": True, "message": "No cookies file to delete"}
        except Exception as e:
            return {"success": False, "error": "clear_cookies_failed", "message": str(e)}

    def list_saved_cookies(self) -> dict:
        """
        列出所有已保存的 cookies 文件
        
        Returns:
            cookies 文件列表
        """
        try:
            result = {
                "global": None,
                "domains": []
            }
            
            # 检查全局 cookies
            global_file = os.path.join(self._cookies_dir, "global_cookies.json")
            if os.path.exists(global_file):
                with open(global_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                result["global"] = {
                    "count": len(data.get("cookies", [])),
                    "saved_at": data.get("saved_at")
                }
            
            # 检查域名 cookies
            if os.path.exists(self._cookies_domain_dir):
                for f in os.listdir(self._cookies_domain_dir):
                    if f.endswith(".json"):
                        domain = f[:-5]
                        file_path = os.path.join(self._cookies_domain_dir, f)
                        with open(file_path, "r", encoding="utf-8") as fp:
                            data = json.load(fp)
                        result["domains"].append({
                            "domain": domain,
                            "count": len(data.get("cookies", [])),
                            "saved_at": data.get("saved_at")
                        })
            
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": "list_cookies_failed", "message": str(e)}

    def login_form(self, params: dict) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        username_selector = params.get("username_selector")
        password_selector = params.get("password_selector")
        submit_selector = params.get("submit_selector")
        username = params.get("username")
        password = params.get("password")

        if not all([username_selector, password_selector, submit_selector, username, password]):
            return {"success": False, "error": "invalid_params", "message": "Missing required parameters"}

        async def _login():
            await self._page.fill(username_selector, username)
            await asyncio.sleep(random.uniform(0.3, 0.8))
            await self._page.fill(password_selector, password)
            await asyncio.sleep(random.uniform(0.3, 0.8))
            await self._page.click(submit_selector)
            await self._page.wait_for_load_state("networkidle", timeout=15000)
            return True

        try:
            self._run_async(_login())
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": "login_failed", "message": str(e)}

    def login_with_cookies(self, cookies: List[dict], url: str) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _login():
            await self._context.add_cookies(cookies)
            await self._page.goto(url, wait_until="domcontentloaded")
            await self._page.wait_for_load_state("networkidle", timeout=15000)
            return True

        try:
            self._run_async(_login())
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": "login_failed", "message": str(e)}

    def get_qr_code(self, selector: str) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _get_qr():
            element = await self._page.query_selector(selector)
            if element:
                data = await element.screenshot()
                return data
            return None

        try:
            data = self._run_async(_get_qr())
            if data is None:
                return {"success": False, "error": "element_not_found", "message": "QR code element not found"}
            return {"success": True, "data": base64.b64encode(data).decode("utf-8")}
        except Exception as e:
            return {"success": False, "error": "get_qr_failed", "message": str(e)}

    def wait_for_navigation(self, timeout: int = 30000) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _wait():
            await self._page.wait_for_load_state("networkidle", timeout=timeout)
            return await self._get_page_info()

        try:
            result = self._run_async(_wait())
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": "timeout", "message": str(e)}

    def wait_for_selector(self, selector: str, timeout: int = 10000) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _wait():
            await self._page.wait_for_selector(selector, timeout=timeout)
            return True

        try:
            self._run_async(_wait())
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": "timeout", "message": str(e)}

    def evaluate(self, script: str) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _eval():
            return await self._page.evaluate(script)

        try:
            result = self._run_async(_eval())
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": "evaluate_failed", "message": str(e)}

    def press(self, key: str) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _press():
            await self._page.keyboard.press(key)
            return True

        try:
            self._run_async(_press())
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": "press_failed", "message": str(e)}

    def type_text(self, text: str, delay: int = 50) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _type():
            await self._page.keyboard.type(text, delay=delay)
            return True

        try:
            self._run_async(_type())
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": "type_failed", "message": str(e)}

    def go_back(self) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _back():
            await self._page.go_back()
            await self._page.wait_for_load_state("networkidle", timeout=10000)
            return await self._get_page_info()

        try:
            result = self._run_async(_back())
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": "navigation_failed", "message": str(e)}

    def go_forward(self) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _forward():
            await self._page.go_forward()
            await self._page.wait_for_load_state("networkidle", timeout=10000)
            return await self._get_page_info()

        try:
            result = self._run_async(_forward())
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": "navigation_failed", "message": str(e)}

    def refresh(self) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _refresh():
            await self._page.reload()
            await self._page.wait_for_load_state("networkidle", timeout=10000)
            return await self._get_page_info()

        try:
            result = self._run_async(_refresh())
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": "refresh_failed", "message": str(e)}
