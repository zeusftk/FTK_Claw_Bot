"""Web 自动化代理"""
from playwright.async_api import Page
from typing import Optional, Dict, Any
import asyncio
import random
import time
import uuid

from ftk_claw_bot.web_api_agent.config import config
from ftk_claw_bot.web_api_agent.core.data_extractor import DataExtractor


def empty_result(url: str = "", title: str = "", error: str = None) -> Dict[str, Any]:
    """生成空结果"""
    return {
        'url': url,
        'title': title,
        'elements': [],
        'forms': [],
        'summary': {'total': 0, 'interactive': 0, 'unique_text': 0, 'form_count': 0},
        'error': error
    }


class WebAgent:
    """Web 自动化代理：执行浏览器操作"""

    def __init__(self, page: Page):
        self.page = page
        self.action_count = 0
        self.last_action_time = 0
        self.max_actions_per_minute = config.MAX_ACTIONS_PER_MINUTE

    async def navigate(self, url: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """导航到指定 URL"""
        try:
            await self.page.goto(url, wait_until="networkidle", timeout=30000)
            await self.page.wait_for_load_state("domcontentloaded")
            return await DataExtractor.extract_page_structure(self.page, config)
        except Exception as e:
            return empty_result(self.page.url, '', str(e))

    async def click(self, selector: str, retries: int = 3, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """点击元素"""
        for attempt in range(retries):
            try:
                await self.page.click(selector)
                await self.page.wait_for_load_state("networkidle", timeout=10000)
                return await DataExtractor.extract_page_structure(self.page, config)
            except Exception:
                if attempt == retries - 1:
                    return empty_result(self.page.url, await self.page.title(), f'点击失败: {selector}')
                await asyncio.sleep(1)
        return await DataExtractor.extract_page_structure(self.page, config)

    async def fill(self, selector: str, value: str, retries: int = 3, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """填充输入框"""
        for attempt in range(retries):
            try:
                await self.page.fill(selector, value)
                return await DataExtractor.extract_page_structure(self.page, config)
            except Exception:
                if attempt == retries - 1:
                    return empty_result(self.page.url, await self.page.title(), f'填充失败: {selector}')
                await asyncio.sleep(1)
        return await DataExtractor.extract_page_structure(self.page, config)

    async def scroll(self, direction: str = "down", amount: int = 500, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """滚动页面"""
        try:
            scroll_amount = amount if direction == "down" else -amount
            await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(0.5)
            return await DataExtractor.extract_page_structure(self.page, config)
        except Exception as e:
            return empty_result(self.page.url, await self.page.title(), str(e))

    async def screenshot(self, path: str) -> bool:
        """截取屏幕"""
        try:
            await self.page.screenshot(path=path)
            return True
        except Exception:
            return False

    async def wait_for_selector(self, selector: str, timeout: int = 30000, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """等待元素出现"""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return await DataExtractor.extract_page_structure(self.page, config)
        except Exception:
            return empty_result(self.page.url, await self.page.title(), f'元素未找到: {selector}')

    async def check_rate_limit(self) -> bool:
        """检查速率限制"""
        current_time = time.time()
        if current_time - self.last_action_time > 60:
            self.action_count = 0
            self.last_action_time = current_time

        if self.action_count >= self.max_actions_per_minute:
            await asyncio.sleep(60 - (current_time - self.last_action_time))
            self.action_count = 0
            self.last_action_time = time.time()

        self.action_count += 1
        return True

    async def execute_action(self, action: str, params: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行操作"""
        if not await self.check_rate_limit():
            return empty_result(self.page.url, await self.page.title(), '操作频率超限')

        await self.emulate_human_behavior()

        action_map = {
            "click": lambda: self.click(params.get("selector"), config=config),
            "fill": lambda: self.fill(params.get("selector"), params.get("value"), config=config),
            "scroll": lambda: self.scroll(params.get("direction", "down"), params.get("amount", 500), config=config),
            "submit": lambda: self.click(params.get("selector"), config=config),
            "wait": lambda: self.wait_for_selector(params.get("selector"), params.get("timeout", 30000), config=config),
        }

        if action in action_map:
            return await action_map[action]()
        return empty_result(self.page.url, await self.page.title(), f'未知操作: {action}')

    async def login(self, username_selector: str, password_selector: str, submit_selector: str,
                    username: str, password: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """表单登录"""
        try:
            if not await self.check_rate_limit():
                return empty_result(self.page.url, await self.page.title(), '操作频率超限')

            await self.emulate_human_behavior()

            # 填充用户名
            result = await self.fill(username_selector, username, config=config)
            if result.get('error'):
                return result

            await self.emulate_human_behavior()

            # 填充密码
            result = await self.fill(password_selector, password, config=config)
            if result.get('error'):
                return result

            await self.emulate_human_behavior()

            # 点击提交
            return await self.click(submit_selector, config=config)
        except Exception as e:
            return empty_result(self.page.url, await self.page.title(), str(e))

    async def login_with_cookies(self, cookies: list, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """使用 Cookie 登录"""
        try:
            await self.page.context.add_cookies(cookies)
            await self.page.reload()
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            return await DataExtractor.extract_page_structure(self.page, config)
        except Exception as e:
            return empty_result(self.page.url, await self.page.title(), str(e))

    async def emulate_human_behavior(self):
        """模拟人类行为（鼠标移动、随机滚动）"""
        try:
            await self.page.mouse.move(random.randint(100, 200), random.randint(100, 200))
            await asyncio.sleep(random.uniform(0.5, 1.5))

            if random.random() > 0.5:
                await self.scroll("down", random.randint(100, 300))
                await asyncio.sleep(random.uniform(0.5, 1.5))
                await self.scroll("up", random.randint(50, 150))
                await asyncio.sleep(random.uniform(0.5, 1.5))
        except Exception:
            pass

    async def scan_login(self, qr_selector: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """扫码登录"""
        try:
            qr_element = await self.page.query_selector(qr_selector)
            if not qr_element:
                return empty_result(self.page.url, await self.page.title(), "未找到二维码")

            qr_path = f"qr_code_{uuid.uuid4()}.png"
            await qr_element.screenshot(path=qr_path)
            result = await DataExtractor.extract_page_structure(self.page, config)
            result['qr_path'] = qr_path
            result['message'] = "请扫描二维码"
            return result
        except Exception as e:
            return empty_result(self.page.url, await self.page.title(), str(e))

    async def check_login_status(self) -> bool:
        """检查登录状态"""
        return True

    async def extract_data(self, selectors: list) -> Dict[str, Any]:
        """提取数据"""
        return await DataExtractor.extract_by_selectors(self.page, selectors)

    async def get_page_content(self) -> str:
        """获取页面内容"""
        try:
            return await self.page.content()
        except Exception:
            return ""

    async def get_current_url(self) -> str:
        """获取当前 URL"""
        try:
            return self.page.url
        except Exception:
            return ""

    async def get_page_structure(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取页面结构"""
        return await DataExtractor.extract_page_structure(self.page, config)
