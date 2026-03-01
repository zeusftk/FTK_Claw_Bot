# -*- coding: utf-8 -*-
import asyncio
import concurrent.futures
from typing import Any, Optional
from pathlib import Path
import sys

from loguru import logger


class WebAgentExecutor:
    """
    WebAgent executor with lazy initialization.
    Wraps WebAgent from web_api_agent for IPC integration.
    """
    
    def __init__(self, timeout: int = 10):
        self._timeout = timeout
        self._agent: Optional[Any] = None
        self._initialized = False
        self._lock = asyncio.Lock()
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    async def initialize(self) -> bool:
        """Lazy initialize WebAgent (Playwright browser)."""
        async with self._lock:
            if self._initialized:
                return True
            
            try:
                # Add web_api_agent to path
                project_root = Path(__file__).parent.parent.parent
                web_api_agent_path = project_root / "web_api_agent"
                if str(web_api_agent_path) not in sys.path:
                    sys.path.insert(0, str(web_api_agent_path))
                
                from core.web_agent import WebAgent
                
                self._agent = WebAgent()
                await self._agent.start()
                self._initialized = True
                logger.info("WebAgent initialized successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to initialize WebAgent: {e}")
                return False
    
    async def execute(self, action: str, params: dict) -> Optional[dict]:
        """
        Execute a browser action.
        
        Args:
            action: Action name (click, fill, navigate, etc.)
            params: Action parameters
            
        Returns:
            Result dict or None if failed
        """
        if not self._initialized:
            if not await self.initialize():
                return None
        
        try:
            result = await asyncio.wait_for(
                self._execute_action(action, params),
                timeout=params.get("timeout", self._timeout)
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"WebAgent action {action} timed out")
            return None
        except Exception as e:
            logger.error(f"WebAgent action {action} failed: {e}")
            return None
    
    def execute_sync(self, action: str, params: dict) -> Optional[dict]:
        """
        Synchronous wrapper for execute.
        
        Args:
            action: Action name (click, fill, navigate, etc.)
            params: Action parameters
            
        Returns:
            Result dict or None if failed
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.execute(action, params))
                    return future.result(timeout=params.get("timeout", self._timeout))
            else:
                return loop.run_until_complete(self.execute(action, params))
        except RuntimeError:
            return asyncio.run(self.execute(action, params))
    
    async def _execute_action(self, action: str, params: dict) -> Optional[dict]:
        """Internal action execution."""
        if self._agent is None:
            return None
        
        action_map = {
            "click": self._click,
            "fill": self._fill,
            "navigate": self._navigate,
            "scroll": self._scroll,
            "screenshot": self._screenshot,
            "get_text": self._get_text,
            "wait_for_selector": self._wait_for_selector,
            "get_page_content": self._get_page_content,
            "get_current_url": self._get_current_url,
            "extract_data": self._extract_data,
        }
        
        handler = action_map.get(action)
        if handler:
            return await handler(params)
        
        # Generic action execution via WebAgent.execute_action
        success = await self._agent.execute_action(action, params)
        return {"success": success}
    
    async def _click(self, params: dict) -> Optional[dict]:
        selector = params.get("selector")
        if not selector:
            return None
        success = await self._agent.click(selector)
        return {"success": success}
    
    async def _fill(self, params: dict) -> Optional[dict]:
        selector = params.get("selector")
        value = params.get("value")
        if not selector or value is None:
            return None
        success = await self._agent.fill(selector, value)
        return {"success": success}
    
    async def _navigate(self, params: dict) -> Optional[dict]:
        url = params.get("url")
        if not url:
            return None
        success = await self._agent.navigate(url)
        return {"success": success, "url": url}
    
    async def _scroll(self, params: dict) -> Optional[dict]:
        direction = params.get("direction", "down")
        amount = params.get("amount", 300)
        success = await self._agent.scroll(direction, amount)
        return {"success": success}
    
    async def _screenshot(self, params: dict) -> Optional[dict]:
        path = params.get("path")
        if not path:
            return None
        success = await self._agent.screenshot(path)
        return {"success": success, "path": path}
    
    async def _get_text(self, params: dict) -> Optional[dict]:
        selector = params.get("selector")
        if not selector:
            return None
        if not self._agent:
            logger.error("WebAgent not initialized")
            return {"success": False, "error": "WebAgent not initialized"}
        try:
            text = await self._agent.page.locator(selector).inner_text()
            return {"success": True, "text": text}
        except Exception as e:
            logger.error(f"Failed to get text: {e}")
            return {"success": False, "error": str(e)}
    
    async def _wait_for_selector(self, params: dict) -> Optional[dict]:
        selector = params.get("selector")
        if not selector:
            return None
        if not self._agent:
            logger.error("WebAgent not initialized")
            return {"success": False, "error": "WebAgent not initialized"}
        timeout = params.get("timeout", self._timeout * 1000)
        try:
            await self._agent.page.wait_for_selector(selector, timeout=timeout)
            return {"success": True}
        except Exception as e:
            logger.error(f"Wait for selector failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_page_content(self, params: dict) -> Optional[dict]:
        if not self._agent:
            logger.error("WebAgent not initialized")
            return {"success": False, "error": "WebAgent not initialized"}
        content = await self._agent.get_page_content()
        return {"success": True, "content": content}
    
    async def _get_current_url(self, params: dict) -> Optional[dict]:
        if not self._agent:
            logger.error("WebAgent not initialized")
            return {"success": False, "error": "WebAgent not initialized"}
        url = await self._agent.get_current_url()
        return {"success": True, "url": url}
    
    async def _extract_data(self, params: dict) -> Optional[dict]:
        if not self._agent:
            logger.error("WebAgent not initialized")
            return {"success": False, "error": "WebAgent not initialized"}
        selectors = params.get("selectors", [])
        data = await self._agent.extract_data(selectors)
        return {"success": True, "data": data}
    
    async def shutdown(self):
        """Shutdown WebAgent."""
        if self._agent:
            try:
                await self._agent.stop()
                logger.info("WebAgent shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down WebAgent: {e}")
            finally:
                self._agent = None
                self._initialized = False
    
    def shutdown_sync(self):
        """Synchronous wrapper for shutdown."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.shutdown())
                    future.result(timeout=10)
            else:
                loop.run_until_complete(self.shutdown())
        except RuntimeError:
            asyncio.run(self.shutdown())
