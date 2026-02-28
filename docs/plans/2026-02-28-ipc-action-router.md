# IPC Action Router Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a layered action routing system that routes IPC requests by target_type to appropriate executors with fallback support.

**Architecture:** Add ActionRouter between IPCServer and executors. WebAgentExecutor wraps WebAgent with lazy initialization. Failed browser operations fallback to WindowsAutomation.

**Tech Stack:** Python, Playwright, pyautogui, asyncio

---

## Task 1: Extend IPC Message Protocol

**Files:**
- Modify: `ftk_claw_bot/bridge/protocol.py`

**Step 1: Read current protocol file**

Read: `ftk_claw_bot/bridge/protocol.py`

**Step 2: Add target_type field to IPCMessage**

Add `target_type` field to the payload structure. Default value is `generic` for backward compatibility.

```python
# In IPCMessage class or payload validation
# Add target_type with choices: "browser", "desktop", "generic"
# Default: "generic"
```

**Step 3: Add response fields**

Add `executor` and `fallback` fields to response payload structure.

```python
# Response payload should include:
# - executor: "webagent" | "automation"
# - fallback: bool
```

**Step 4: Commit**

```bash
git add ftk_claw_bot/bridge/protocol.py
git commit -m "feat: add target_type and fallback fields to IPC protocol"
```

---

## Task 2: Create WebAgentExecutor

**Files:**
- Create: `ftk_claw_bot/services/web_agent_executor.py`

**Step 1: Create the file with basic structure**

```python
import asyncio
import logging
from typing import Any, Optional
from pathlib import Path
import sys

logger = logging.getLogger(__name__)


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
        }
        
        handler = action_map.get(action)
        if handler:
            return await handler(params)
        
        # Generic action execution
        return await self._agent.execute_action(action, params)
    
    async def _click(self, params: dict) -> Optional[dict]:
        selector = params.get("selector")
        if not selector:
            return None
        await self._agent.click(selector)
        return {"success": True}
    
    async def _fill(self, params: dict) -> Optional[dict]:
        selector = params.get("selector")
        value = params.get("value")
        if not selector or value is None:
            return None
        await self._agent.fill(selector, value)
        return {"success": True}
    
    async def _navigate(self, params: dict) -> Optional[dict]:
        url = params.get("url")
        if not url:
            return None
        await self._agent.navigate(url)
        return {"success": True, "url": url}
    
    async def _scroll(self, params: dict) -> Optional[dict]:
        direction = params.get("direction", "down")
        amount = params.get("amount", 300)
        await self._agent.scroll(direction, amount)
        return {"success": True}
    
    async def _screenshot(self, params: dict) -> Optional[dict]:
        path = params.get("path")
        result = await self._agent.screenshot(path)
        return {"success": True, "path": path}
    
    async def _get_text(self, params: dict) -> Optional[dict]:
        selector = params.get("selector")
        text = await self._agent.page.locator(selector).inner_text() if selector else None
        return {"success": True, "text": text}
    
    async def _wait_for_selector(self, params: dict) -> Optional[dict]:
        selector = params.get("selector")
        timeout = params.get("timeout", self._timeout * 1000)
        await self._agent.page.wait_for_selector(selector, timeout=timeout)
        return {"success": True}
    
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
```

**Step 2: Commit**

```bash
git add ftk_claw_bot/services/web_agent_executor.py
git commit -m "feat: add WebAgentExecutor with lazy initialization"
```

---

## Task 3: Create ActionRouter

**Files:**
- Create: `ftk_claw_bot/services/action_router.py`

**Step 1: Create the ActionRouter class**

```python
import logging
from typing import Any, Callable, Optional
from enum import Enum

from .web_agent_executor import WebAgentExecutor

logger = logging.getLogger(__name__)


class TargetType(str, Enum):
    BROWSER = "browser"
    DESKTOP = "desktop"
    GENERIC = "generic"


class ExecutorType(str, Enum):
    WEBAGENT = "webagent"
    AUTOMATION = "automation"


class ActionRouter:
    """
    Routes IPC requests to appropriate executors with fallback support.
    """
    
    def __init__(
        self,
        automation_executor: Callable,
        web_agent_timeout: int = 10
    ):
        """
        Args:
            automation_executor: Function to execute automation actions
            web_agent_timeout: Timeout for WebAgent operations
        """
        self._automation_executor = automation_executor
        self._web_agent = WebAgentExecutor(timeout=web_agent_timeout)
    
    async def route(self, payload: dict) -> dict:
        """
        Route request to appropriate executor.
        
        Args:
            payload: IPC request payload with target_type, action, params
            
        Returns:
            Response dict with success, result, executor, fallback
        """
        target_type = payload.get("target_type", TargetType.GENERIC.value)
        action = payload.get("action")
        params = payload.get("params", {})
        
        if target_type == TargetType.BROWSER.value:
            return await self._handle_browser_action(action, params)
        elif target_type == TargetType.DESKTOP.value:
            # Future: DesktopAgent
            # For now, fallback to automation
            logger.info("Desktop agent not implemented, using automation")
            return await self._execute_automation(action, params, fallback=True)
        else:
            return await self._execute_automation(action, params, fallback=False)
    
    async def _handle_browser_action(self, action: str, params: dict) -> dict:
        """Handle browser action with fallback."""
        try:
            result = await self._web_agent.execute(action, params)
            
            if result is not None:
                return {
                    "success": True,
                    "result": result,
                    "executor": ExecutorType.WEBAGENT.value,
                    "fallback": False
                }
            
            # Empty result, fallback
            logger.warning(f"WebAgent returned None for action {action}, falling back")
        except Exception as e:
            logger.error(f"WebAgent exception: {e}, falling back")
        
        # Fallback to automation
        return await self._execute_automation(action, params, fallback=True)
    
    async def _execute_automation(
        self,
        action: str,
        params: dict,
        fallback: bool
    ) -> dict:
        """Execute using automation executor."""
        try:
            result = await self._automation_executor(action, params)
            return {
                "success": True,
                "result": result,
                "executor": ExecutorType.AUTOMATION.value,
                "fallback": fallback
            }
        except Exception as e:
            logger.error(f"Automation action {action} failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "executor": ExecutorType.AUTOMATION.value,
                "fallback": fallback
            }
    
    async def shutdown(self):
        """Shutdown all executors."""
        await self._web_agent.shutdown()
```

**Step 2: Commit**

```bash
git add ftk_claw_bot/services/action_router.py
git commit -m "feat: add ActionRouter with fallback support"
```

---

## Task 4: Integrate ActionRouter into WindowsBridge

**Files:**
- Modify: `ftk_claw_bot/services/windows_bridge.py`

**Step 1: Read current windows_bridge.py**

Read: `ftk_claw_bot/services/windows_bridge.py`

**Step 2: Import ActionRouter**

Add import at top of file:

```python
from .action_router import ActionRouter
```

**Step 3: Initialize ActionRouter in WindowsBridge class**

In `__init__` method, after creating WindowsAutomation:

```python
self._action_router: Optional[ActionRouter] = None
```

**Step 4: Create ActionRouter initialization method**

```python
def _init_action_router(self):
    """Initialize ActionRouter with automation executor."""
    if self._action_router is None:
        self._action_router = ActionRouter(
            automation_executor=self._execute_automation_action
        )
    return self._action_router
```

**Step 5: Add automation action wrapper**

```python
async def _execute_automation_action(self, action: str, params: dict) -> dict:
    """Wrapper for automation actions to be used by ActionRouter."""
    return self._automation.execute(action, params)
```

**Step 6: Modify IPC message handler to use ActionRouter**

In the message handling method, route requests through ActionRouter:

```python
async def _handle_request(self, message: dict) -> dict:
    payload = message.get("payload", {})
    target_type = payload.get("target_type", "generic")
    
    if target_type in ("browser", "desktop"):
        router = self._init_action_router()
        return await router.route(payload)
    else:
        # Direct automation for generic requests
        action = payload.get("action")
        params = payload.get("params", {})
        result = self._automation.execute(action, params)
        return {
            "success": True,
            "result": result,
            "executor": "automation",
            "fallback": False
        }
```

**Step 7: Add shutdown cleanup**

In shutdown method:

```python
if self._action_router:
    await self._action_router.shutdown()
```

**Step 8: Commit**

```bash
git add ftk_claw_bot/services/windows_bridge.py
git commit -m "feat: integrate ActionRouter into WindowsBridge"
```

---

## Task 5: Update Services __init__.py

**Files:**
- Modify: `ftk_claw_bot/services/__init__.py`

**Step 1: Read current __init__.py**

Read: `ftk_claw_bot/services/__init__.py`

**Step 2: Add new exports**

```python
from .action_router import ActionRouter, TargetType, ExecutorType
from .web_agent_executor import WebAgentExecutor
```

**Step 3: Commit**

```bash
git add ftk_claw_bot/services/__init__.py
git commit -m "feat: export ActionRouter and WebAgentExecutor"
```

---

## Task 6: Test Integration

**Files:**
- Test manually via IPC client

**Step 1: Start the application**

Run the FTK_Claw_Bot application and ensure WindowsBridge starts.

**Step 2: Send test IPC request (generic)**

```python
# Test generic action (should use automation directly)
{
    "version": "1.0",
    "type": "request",
    "id": "test-001",
    "payload": {
        "target_type": "generic",
        "action": "screenshot",
        "params": {}
    }
}
```

**Step 3: Send test IPC request (browser)**

```python
# Test browser action (should use WebAgent)
{
    "version": "1.0",
    "type": "request",
    "id": "test-002",
    "payload": {
        "target_type": "browser",
        "action": "navigate",
        "params": {
            "url": "https://example.com"
        }
    }
}
```

**Step 4: Verify fallback works**

Send a browser action with invalid selector, verify it falls back to automation.

**Step 5: Commit final**

```bash
git add -A
git commit -m "feat: complete IPC action router implementation"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Extend IPC protocol with target_type |
| 2 | Create WebAgentExecutor with lazy init |
| 3 | Create ActionRouter with fallback |
| 4 | Integrate into WindowsBridge |
| 5 | Update exports |
| 6 | Test integration |
