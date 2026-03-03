# -*- coding: utf-8 -*-
import asyncio
import base64
import json
import os
import random
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any

from loguru import logger

PLAYWRIGHT_AVAILABLE = True


def _check_playwright():
    global PLAYWRIGHT_AVAILABLE
    try:
        from playwright.async_api import async_playwright
        return True
    except ImportError:
        PLAYWRIGHT_AVAILABLE = False
        return False


_check_playwright()


class WebAutomation:
    """Web 自动化类 - 基于 web_api_agent 方案"""

    def __init__(self):
        self._session_id: Optional[str] = None
        self._session_manager = None
        self._web_agent = None
        self._started = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._headless = True
        
        from ftk_claw_bot.utils.user_data_dir import user_data
        self._sessions_dir = str(user_data.web_sessions)
        self._cookies_dir = str(user_data.web_cookies)
        self._cookies_domain_dir = str(user_data.web_cookies_domain)
        
        os.makedirs(self._sessions_dir, exist_ok=True)
        os.makedirs(self._cookies_dir, exist_ok=True)
        os.makedirs(self._cookies_domain_dir, exist_ok=True)

    @property
    def is_started(self) -> bool:
        return self._started and self._session_id is not None

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
        return future.result(timeout=120)

    async def _get_session_manager(self):
        if self._session_manager is None:
            from web_api_agent.core.session_manager import SessionManager
            self._session_manager = SessionManager()
            await self._session_manager.initialize()
        return self._session_manager

    async def _get_web_agent(self):
        if self._web_agent is None and self._session_id:
            session_manager = await self._get_session_manager()
            session = await session_manager.get_session(self._session_id)
            if session:
                from web_api_agent.core.web_agent import WebAgent
                self._web_agent = WebAgent(session.page)
        return self._web_agent

    def start(self, headless: bool = True, viewport: dict = None) -> bool:
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("[WebAutomation] Playwright not available")
            return False

        from ftk_claw_bot.constants import WebAutomation as WebConfig
        viewport = viewport or {
            "width": WebConfig.VIEWPORT_WIDTH,
            "height": WebConfig.VIEWPORT_HEIGHT
        }

        async def _start():
            session_manager = await self._get_session_manager()
            self._session_id = await session_manager.create_session()
            
            session = await session_manager.get_session(self._session_id)
            if session:
                from web_api_agent.core.web_agent import WebAgent
                self._web_agent = WebAgent(session.page)
                self._started = True
                self._headless = headless
                logger.info(f"[WebAutomation] Started session: {self._session_id}")
                return True
            return False

        try:
            return self._run_async(_start())
        except Exception as e:
            logger.error(f"[WebAutomation] Failed to start: {e}")
            return False

    def stop(self) -> bool:
        async def _stop():
            if self._session_id and self._session_manager:
                await self._session_manager.close_session(self._session_id)
            self._session_id = None
            self._web_agent = None
            self._started = False
            return True

        try:
            if self._session_id:
                return self._run_async(_stop())
            return True
        except Exception as e:
            logger.error(f"[WebAutomation] Failed to stop: {e}")
            return False

    def navigate(self, url: str, wait_until: str = "domcontentloaded", timeout: int = 30000) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started", "message": "Browser not started"}

        if not url.startswith(("http://", "https://")):
            return {"success": False, "error": "invalid_url", "message": "URL must start with http:// or https://"}

        async def _navigate():
            agent = await self._get_web_agent()
            if agent is None:
                return {"success": False, "error": "agent_not_available"}
            
            result = await agent.navigate(url)
            return {
                "success": not bool(result.get("error")),
                "url": result.get("url", ""),
                "title": result.get("title", ""),
                "elements": result.get("elements", []),
                "summary": result.get("summary", {}),
                "error": result.get("error")
            }

        try:
            result = self._run_async(_navigate())
            return result
        except Exception as e:
            return {"success": False, "error": "navigation_failed", "message": str(e)}

    def click(self, selector: str, timeout: int = 10000) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _click():
            agent = await self._get_web_agent()
            if agent is None:
                return {"success": False, "error": "agent_not_available"}
            
            result = await agent.click(selector)
            return {
                "success": not bool(result.get("error")),
                "error": result.get("error")
            }

        try:
            return self._run_async(_click())
        except Exception as e:
            return {"success": False, "error": "element_not_found", "message": str(e)}

    def fill(self, selector: str, value: str, timeout: int = 10000) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _fill():
            agent = await self._get_web_agent()
            if agent is None:
                return {"success": False, "error": "agent_not_available"}
            
            result = await agent.fill(selector, value)
            return {
                "success": not bool(result.get("error")),
                "error": result.get("error")
            }

        try:
            return self._run_async(_fill())
        except Exception as e:
            return {"success": False, "error": "element_not_found", "message": str(e)}

    def scroll(self, direction: str = "down", amount: int = 500) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _scroll():
            agent = await self._get_web_agent()
            if agent is None:
                return {"success": False, "error": "agent_not_available"}
            
            result = await agent.scroll(direction, amount)
            return {
                "success": not bool(result.get("error")),
                "error": result.get("error")
            }

        try:
            return self._run_async(_scroll())
        except Exception as e:
            return {"success": False, "error": "scroll_failed", "message": str(e)}

    def get_content(self) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _get_content():
            agent = await self._get_web_agent()
            if agent is None:
                return {"success": False, "error": "agent_not_available"}
            
            content = await agent.get_page_content()
            return {"success": True, "content": content}

        try:
            return self._run_async(_get_content())
        except Exception as e:
            return {"success": False, "error": "get_content_failed", "message": str(e)}

    def get_url(self) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _get_url():
            agent = await self._get_web_agent()
            if agent is None:
                return {"success": False, "error": "agent_not_available"}
            
            url = await agent.get_current_url()
            return {"success": True, "url": url}

        try:
            return self._run_async(_get_url())
        except Exception as e:
            return {"success": False, "error": "get_url_failed", "message": str(e)}

    def get_title(self) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _get_title():
            session_manager = await self._get_session_manager()
            session = await session_manager.get_session(self._session_id)
            if session and session.page:
                title = await session.page.title()
                return {"success": True, "title": title}
            return {"success": False, "error": "session_not_found"}

        try:
            return self._run_async(_get_title())
        except Exception as e:
            return {"success": False, "error": "get_title_failed", "message": str(e)}

    def screenshot(self, selector: Optional[str] = None, full_page: bool = False) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _screenshot():
            session_manager = await self._get_session_manager()
            session = await session_manager.get_session(self._session_id)
            if not session or not session.page:
                return {"success": False, "error": "session_not_found"}
            
            page = session.page
            
            if selector:
                element = await page.query_selector(selector)
                if element:
                    data = await element.screenshot()
                else:
                    return {"success": False, "error": "element_not_found"}
            else:
                data = await page.screenshot(full_page=full_page)
            
            return {"success": True, "data": base64.b64encode(data).decode("utf-8")}

        try:
            return self._run_async(_screenshot())
        except Exception as e:
            return {"success": False, "error": "screenshot_failed", "message": str(e)}

    def extract_elements(self, config: Optional[dict] = None) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _extract():
            agent = await self._get_web_agent()
            if agent is None:
                return {"success": False, "error": "agent_not_available"}
            
            result = await agent.get_page_structure(config)
            return {
                "success": not bool(result.get("error")),
                "url": result.get("url", ""),
                "title": result.get("title", ""),
                "elements": result.get("elements", []),
                "forms": result.get("forms", []),
                "summary": result.get("summary", {}),
                "error": result.get("error")
            }

        try:
            return self._run_async(_extract())
        except Exception as e:
            return {"success": False, "error": "extract_failed", "message": str(e)}

    def extract_data(self, selectors: List[Dict[str, str]]) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _extract():
            agent = await self._get_web_agent()
            if agent is None:
                return {"success": False, "error": "agent_not_available"}
            
            data = await agent.extract_data(selectors)
            return {"success": True, "data": data}

        try:
            return self._run_async(_extract())
        except Exception as e:
            return {"success": False, "error": "extract_failed", "message": str(e)}

    def get_cookies(self) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _get_cookies():
            agent = await self._get_web_agent()
            if agent is None:
                return {"success": False, "error": "agent_not_available"}
            
            cookies = await agent.get_cookies()
            return {"success": True, "cookies": cookies}

        try:
            return self._run_async(_get_cookies())
        except Exception as e:
            return {"success": False, "error": "get_cookies_failed", "message": str(e)}

    def set_cookies(self, cookies: List[dict]) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _set_cookies():
            agent = await self._get_web_agent()
            if agent is None:
                return {"success": False, "error": "agent_not_available"}
            
            result = await agent.set_cookies(cookies)
            return {"success": result}

        try:
            return self._run_async(_set_cookies())
        except Exception as e:
            return {"success": False, "error": "set_cookies_failed", "message": str(e)}

    def save_session(self, session_id: str) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _save():
            session_manager = await self._get_session_manager()
            session = await session_manager.get_session(self._session_id)
            if not session:
                return {"success": False, "error": "session_not_found"}
            
            cookies = await session.context.cookies()
            storage = await session.context.storage_state()
            session_data = {
                "cookies": cookies,
                "storage": storage,
                "created_at": datetime.now().isoformat()
            }
            session_file = os.path.join(self._sessions_dir, f"{session_id}.json")
            with open(session_file, "w") as f:
                json.dump(session_data, f)
            return {"success": True}

        try:
            return self._run_async(_save())
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
                session_manager = await self._get_session_manager()
                session = await session_manager.get_session(self._session_id)
                if session:
                    cookies = session_data.get("cookies", [])
                    await session.context.add_cookies(cookies)
                    return {"success": True}
                return {"success": False, "error": "session_not_found"}

            return self._run_async(_load())
        except Exception as e:
            return {"success": False, "error": "load_session_failed", "message": str(e)}

    def save_cookies(self, domain: str = None) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _get_cookies():
            session_manager = await self._get_session_manager()
            session = await session_manager.get_session(self._session_id)
            if session:
                return await session.context.cookies()
            return []

        try:
            cookies = self._run_async(_get_cookies())
            
            if domain:
                cookies = [c for c in cookies if domain in c.get("domain", "")]
                cookie_file = os.path.join(self._cookies_domain_dir, f"{domain}.json")
            else:
                cookie_file = os.path.join(self._cookies_dir, "global_cookies.json")
            
            cookie_data = {
                "cookies": cookies,
                "saved_at": datetime.now().isoformat(),
                "domain": domain
            }
            
            with open(cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookie_data, f, ensure_ascii=False, indent=2)
            
            return {"success": True, "count": len(cookies), "file": cookie_file}
        except Exception as e:
            return {"success": False, "error": "save_cookies_failed", "message": str(e)}

    def load_cookies(self, domain: str = None) -> dict:
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
                session_manager = await self._get_session_manager()
                session = await session_manager.get_session(self._session_id)
                if session:
                    await session.context.add_cookies(cookies)
                    return True
                return False

            self._run_async(_add_cookies())
            return {"success": True, "count": len(cookies), "loaded_from": cookie_file}
        except Exception as e:
            return {"success": False, "error": "load_cookies_failed", "message": str(e)}

    def clear_cookies(self, domain: str = None) -> dict:
        try:
            if domain:
                cookie_file = os.path.join(self._cookies_domain_dir, f"{domain}.json")
            else:
                cookie_file = os.path.join(self._cookies_dir, "global_cookies.json")
            
            if os.path.exists(cookie_file):
                os.remove(cookie_file)
                return {"success": True, "message": f"Deleted {cookie_file}"}
            return {"success": True, "message": "No cookies file to delete"}
        except Exception as e:
            return {"success": False, "error": "clear_cookies_failed", "message": str(e)}

    def list_saved_cookies(self) -> dict:
        try:
            result = {"global": None, "domains": []}
            
            global_file = os.path.join(self._cookies_dir, "global_cookies.json")
            if os.path.exists(global_file):
                with open(global_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                result["global"] = {
                    "count": len(data.get("cookies", [])),
                    "saved_at": data.get("saved_at")
                }
            
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
            agent = await self._get_web_agent()
            if agent is None:
                return {"success": False, "error": "agent_not_available"}
            
            result = await agent.login(
                username_selector, password_selector, submit_selector,
                username, password
            )
            return {"success": not bool(result.get("error")), "error": result.get("error")}

        try:
            return self._run_async(_login())
        except Exception as e:
            return {"success": False, "error": "login_failed", "message": str(e)}

    def login_with_cookies(self, cookies: List[dict], url: str) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _login():
            agent = await self._get_web_agent()
            if agent is None:
                return {"success": False, "error": "agent_not_available"}
            
            result = await agent.login_with_cookies(cookies)
            return {"success": not bool(result.get("error")), "error": result.get("error")}

        try:
            return self._run_async(_login())
        except Exception as e:
            return {"success": False, "error": "login_failed", "message": str(e)}

    def get_qr_code(self, selector: str) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _get_qr():
            agent = await self._get_web_agent()
            if agent is None:
                return {"success": False, "error": "agent_not_available"}
            
            result = await agent.scan_login(selector)
            if result.get("qr_path"):
                with open(result["qr_path"], "rb") as f:
                    data = f.read()
                os.remove(result["qr_path"])
                return {"success": True, "data": base64.b64encode(data).decode("utf-8")}
            return {"success": False, "error": result.get("error", "qr_code_not_found")}

        try:
            return self._run_async(_get_qr())
        except Exception as e:
            return {"success": False, "error": "get_qr_failed", "message": str(e)}

    def wait_for_navigation(self, timeout: int = 30000) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _wait():
            session_manager = await self._get_session_manager()
            session = await session_manager.get_session(self._session_id)
            if session and session.page:
                await session.page.wait_for_load_state("networkidle", timeout=timeout)
                return {
                    "success": True,
                    "url": session.page.url,
                    "title": await session.page.title()
                }
            return {"success": False, "error": "session_not_found"}

        try:
            return self._run_async(_wait())
        except Exception as e:
            return {"success": False, "error": "timeout", "message": str(e)}

    def wait_for_selector(self, selector: str, timeout: int = 10000) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _wait():
            agent = await self._get_web_agent()
            if agent is None:
                return {"success": False, "error": "agent_not_available"}
            
            result = await agent.wait_for_selector(selector, timeout)
            return {"success": not bool(result.get("error")), "error": result.get("error")}

        try:
            return self._run_async(_wait())
        except Exception as e:
            return {"success": False, "error": "timeout", "message": str(e)}

    def evaluate(self, script: str) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _eval():
            session_manager = await self._get_session_manager()
            session = await session_manager.get_session(self._session_id)
            if session and session.page:
                result = await session.page.evaluate(script)
                return {"success": True, "result": result}
            return {"success": False, "error": "session_not_found"}

        try:
            return self._run_async(_eval())
        except Exception as e:
            return {"success": False, "error": "evaluate_failed", "message": str(e)}

    def press(self, key: str) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _press():
            session_manager = await self._get_session_manager()
            session = await session_manager.get_session(self._session_id)
            if session and session.page:
                await session.page.keyboard.press(key)
                return {"success": True}
            return {"success": False, "error": "session_not_found"}

        try:
            return self._run_async(_press())
        except Exception as e:
            return {"success": False, "error": "press_failed", "message": str(e)}

    def type_text(self, text: str, delay: int = 50) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _type():
            session_manager = await self._get_session_manager()
            session = await session_manager.get_session(self._session_id)
            if session and session.page:
                await session.page.keyboard.type(text, delay=delay)
                return {"success": True}
            return {"success": False, "error": "session_not_found"}

        try:
            return self._run_async(_type())
        except Exception as e:
            return {"success": False, "error": "type_failed", "message": str(e)}

    def go_back(self) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _back():
            session_manager = await self._get_session_manager()
            session = await session_manager.get_session(self._session_id)
            if session and session.page:
                await session.page.go_back()
                await session.page.wait_for_load_state("networkidle", timeout=10000)
                return {
                    "success": True,
                    "url": session.page.url,
                    "title": await session.page.title()
                }
            return {"success": False, "error": "session_not_found"}

        try:
            return self._run_async(_back())
        except Exception as e:
            return {"success": False, "error": "navigation_failed", "message": str(e)}

    def go_forward(self) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _forward():
            session_manager = await self._get_session_manager()
            session = await session_manager.get_session(self._session_id)
            if session and session.page:
                await session.page.go_forward()
                await session.page.wait_for_load_state("networkidle", timeout=10000)
                return {
                    "success": True,
                    "url": session.page.url,
                    "title": await session.page.title()
                }
            return {"success": False, "error": "session_not_found"}

        try:
            return self._run_async(_forward())
        except Exception as e:
            return {"success": False, "error": "navigation_failed", "message": str(e)}

    def refresh(self) -> dict:
        if not self.is_started:
            return {"success": False, "error": "browser_not_started"}

        async def _refresh():
            session_manager = await self._get_session_manager()
            session = await session_manager.get_session(self._session_id)
            if session and session.page:
                await session.page.reload()
                await session.page.wait_for_load_state("networkidle", timeout=10000)
                return {
                    "success": True,
                    "url": session.page.url,
                    "title": await session.page.title()
                }
            return {"success": False, "error": "session_not_found"}

        try:
            return self._run_async(_refresh())
        except Exception as e:
            return {"success": False, "error": "refresh_failed", "message": str(e)}
