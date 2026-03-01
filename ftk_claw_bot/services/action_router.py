# -*- coding: utf-8 -*-
from typing import Callable

from loguru import logger

from .web_agent_executor import WebAgentExecutor
from ..bridge.protocol import TargetType, ExecutorType


class ActionRouter:
    """
    Routes IPC requests to appropriate executors with fallback support.
    Synchronous version for IPC compatibility.
    """

    def __init__(
        self,
        automation_executor: Callable[[str, dict], dict],  # Sync callable
        web_agent_timeout: int = 10
    ):
        """
        Args:
            automation_executor: Sync function to execute automation actions
            web_agent_timeout: Timeout for WebAgent operations
        """
        self._automation_executor = automation_executor
        self._web_agent = WebAgentExecutor(timeout=web_agent_timeout)

    def route(self, payload: dict) -> dict:
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
            return self._handle_browser_action(action, params)
        elif target_type == TargetType.DESKTOP.value:
            # Future: DesktopAgent
            # For now, fallback to automation
            logger.info("Desktop agent not implemented, using automation")
            return self._execute_automation(action, params, fallback=True)
        else:
            return self._execute_automation(action, params, fallback=False)

    def _handle_browser_action(self, action: str, params: dict) -> dict:
        """Handle browser action with fallback."""
        try:
            result = self._web_agent.execute_sync(action, params)

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
        return self._execute_automation(action, params, fallback=True)

    def _execute_automation(
        self,
        action: str,
        params: dict,
        fallback: bool
    ) -> dict:
        """Execute using automation executor."""
        try:
            result = self._automation_executor(action, params)
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

    def shutdown(self):
        """Shutdown all executors."""
        self._web_agent.shutdown_sync()
