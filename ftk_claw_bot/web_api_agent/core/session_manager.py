"""浏览器会话管理器"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
import uuid
import asyncio

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from ftk_claw_bot.web_api_agent.config import config


@dataclass
class Session:
    """浏览器会话数据类"""
    session_id: str
    browser: Browser
    context: BrowserContext
    page: Page
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)


class SessionManager:
    """会话管理器：管理多个浏览器会话"""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.playwright = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """初始化 Playwright"""
        if not self.playwright:
            self.playwright = await async_playwright().start()

    async def create_session(self) -> str:
        """创建新会话"""
        async with self._lock:
            if not self.playwright:
                await self.initialize()

            session_id = str(uuid.uuid4())
            browser = await self.playwright.chromium.launch(headless=config.HEADLESS)
            context = await browser.new_context()
            page = await context.new_page()

            self.sessions[session_id] = Session(
                session_id=session_id,
                browser=browser,
                context=context,
                page=page
            )
            return session_id

    async def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        async with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.last_active = datetime.now()
            return session

    async def close_session(self, session_id: str) -> bool:
        """关闭会话"""
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False

            try:
                await session.page.close()
                await session.context.close()
                await session.browser.close()
            except Exception:
                pass

            del self.sessions[session_id]
            return True

    async def list_sessions(self) -> list:
        """列出所有会话"""
        async with self._lock:
            return [
                {
                    "session_id": sid,
                    "created_at": s.created_at.isoformat(),
                    "last_active": s.last_active.isoformat(),
                    "url": s.page.url if s.page else ""
                }
                for sid, s in self.sessions.items()
            ]

    async def close_all_sessions(self):
        """关闭所有会话"""
        async with self._lock:
            for session in list(self.sessions.values()):
                try:
                    await session.page.close()
                    await session.context.close()
                    await session.browser.close()
                except Exception:
                    pass
            self.sessions.clear()

    async def shutdown(self):
        """关闭管理器"""
        await self.close_all_sessions()
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None


# 全局会话管理器实例
session_manager = SessionManager()
