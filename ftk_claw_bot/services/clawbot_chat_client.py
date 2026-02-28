# -*- coding: utf-8 -*-
import asyncio
import json
import threading
import uuid
import time
import traceback
from typing import Optional, Callable
from enum import Enum
from queue import Queue

from loguru import logger

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logger.warning("websockets library not installed. Chat functionality will be limited.")


class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class ClawbotChatClient:
    DEFAULT_RECONNECT_DELAY = 5
    MAX_RECONNECT_DELAY = 60
    PING_INTERVAL = 30
    MESSAGE_TIMEOUT = 30

    def __init__(
        self,
        gateway_url: str,
        on_message: Optional[Callable[[str], None]] = None,
        on_status_changed: Optional[Callable[[ConnectionStatus], None]] = None,
        reconnect: bool = True,
        max_reconnect_attempts: int = 3
    ):
        self._gateway_url = gateway_url
        self._on_message = on_message
        self._on_status_changed = on_status_changed
        self._reconnect = reconnect
        self._max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_attempts = 0

        self._status = ConnectionStatus.DISCONNECTED
        self._websocket: Optional[WebSocketClientProtocol] = None
        self._running = False
        
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        
        self._send_queue = Queue()
        
        self._lock = threading.Lock()

    @property
    def status(self) -> ConnectionStatus:
        with self._lock:
            return self._status

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._status == ConnectionStatus.CONNECTED

    def _set_status(self, status: ConnectionStatus):
        with self._lock:
            old_status = self._status
            self._status = status
        logger.info(f"[ChatClient] 状态变更: {old_status.value} -> {status.value}")
        if self._on_status_changed:
            try:
                self._on_status_changed(status)
            except Exception as e:
                logger.error(f"[ChatClient] 状态回调异常: {type(e).__name__}: {e}")
                logger.error(f"[ChatClient] 堆栈跟踪:\n{traceback.format_exc()}")

    def connect(self) -> bool:
        logger.info(f"[ChatClient] 开始连接到: {self._gateway_url}")
        
        if not WEBSOCKETS_AVAILABLE:
            logger.error("[ChatClient] websockets library not available")
            return False

        if self._status == ConnectionStatus.CONNECTED:
            logger.warning("[ChatClient] 已经是连接状态")
            return True

        self._set_status(ConnectionStatus.CONNECTING)
        self._running = True

        try:
            logger.debug("[ChatClient] 启动事件循环线程")
            self._loop = asyncio.new_event_loop()
            
            self._loop_thread = threading.Thread(
                target=self._run_event_loop,
                daemon=True
            )
            self._loop_thread.start()
            
            future = asyncio.run_coroutine_threadsafe(
                self._async_connect(),
                self._loop
            )
            
            success = future.result(timeout=30)
            logger.info(f"[ChatClient] 连接完成，结果: {success}")
            return success
            
        except Exception as e:
            logger.error(f"[ChatClient] 连接失败: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[ChatClient] 堆栈跟踪:\n{traceback.format_exc()}")
            self._set_status(ConnectionStatus.ERROR)
            self._running = False
            return False

    def _run_event_loop(self):
        logger.debug("[ChatClient] 事件循环线程启动")
        asyncio.set_event_loop(self._loop)
        while self._running:
            try:
                self._loop.run_forever()
            except Exception as e:
                logger.error(f"[ChatClient] 事件循环异常: {type(e).__name__}: {e}")
                logger.error(f"[ChatClient] 堆栈跟踪:\n{traceback.format_exc()}")
                if self._running:
                    logger.info("[ChatClient] 尝试恢复事件循环...")
                    time.sleep(1)
        logger.debug("[ChatClient] 事件循环线程结束")

    async def _async_connect(self) -> bool:
        logger.info(f"[ChatClient] 异步连接到: {self._gateway_url}")
        logger.debug(f"[ChatClient] 连接参数: ping_interval={self.PING_INTERVAL}, ping_timeout=10, open_timeout=10")
        
        try:
            logger.debug("[ChatClient] 正在建立 WebSocket 连接...")
            self._websocket = await websockets.connect(
                self._gateway_url,
                ping_interval=self.PING_INTERVAL,
                ping_timeout=10,
                open_timeout=10
            )
            logger.info("[ChatClient] ✅ WebSocket 连接建立成功！")
            
            self._set_status(ConnectionStatus.CONNECTED)
            self._reconnect_attempts = 0

            asyncio.create_task(self._receive_loop())
            asyncio.create_task(self._send_loop())
            asyncio.create_task(self._ping_loop())

            logger.info(f"[ChatClient] 成功连接到 {self._gateway_url}")
            return True

        except ConnectionRefusedError as e:
            logger.error(f"[ChatClient] ❌ 连接被拒绝: {e}")
            logger.error(f"[ChatClient] 请确认 clawbot gateway 是否正在运行，端口是否正确")
            self._set_status(ConnectionStatus.ERROR)
            if self._reconnect and self._reconnect_attempts < self._max_reconnect_attempts:
                asyncio.create_task(self._schedule_reconnect())
            return False
        except Exception as e:
            logger.error(f"[ChatClient] ❌ WebSocket 连接失败: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[ChatClient] 堆栈跟踪:\n{traceback.format_exc()}")
            self._set_status(ConnectionStatus.ERROR)
            if self._reconnect and self._reconnect_attempts < self._max_reconnect_attempts:
                asyncio.create_task(self._schedule_reconnect())
            return False

    async def _receive_loop(self):
        logger.debug("[ChatClient.RX] 接收循环已启动")
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self._running and self._websocket:
            try:
                message = await asyncio.wait_for(
                    self._websocket.recv(),
                    timeout=self.MESSAGE_TIMEOUT
                )
                consecutive_errors = 0
                
                logger.debug(f"[ChatClient.RX] 收到原始消息 (长度: {len(message)})")

                if message and self._on_message:
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        
                        if msg_type == "ping":
                            logger.debug("[ChatClient.RX] 收到 ping 消息，忽略")
                            continue
                        
                        content = data.get("content", data.get("message", str(message)))
                        logger.debug(f"[ChatClient.RX] 提取内容 (长度: {len(content)})")
                        
                        try:
                            self._on_message(content)
                        except Exception as callback_error:
                            logger.error(f"[ChatClient.RX] 消息回调异常: {callback_error}")
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"[ChatClient.RX] JSON 解析失败: {e}, 原始消息前100字符: {message[:100]}")
                        if self._on_message:
                            try:
                                self._on_message(str(message))
                            except Exception as callback_error:
                                logger.error(f"[ChatClient.RX] 原始消息回调异常: {callback_error}")

            except asyncio.TimeoutError:
                logger.debug("[ChatClient.RX] 接收超时，继续等待...")
                continue
            except Exception as e:
                if hasattr(e, 'code'):
                    logger.warning(f"[ChatClient.RX] WebSocket 连接已关闭: code={e.code}, reason={getattr(e, 'reason', 'unknown')}")
                else:
                    consecutive_errors += 1
                    logger.error(f"[ChatClient.RX] 接收错误 ({consecutive_errors}/{max_consecutive_errors}): {type(e).__name__}: {e}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("[ChatClient.RX] 连续错误次数过多，退出接收循环")
                        break
                        
                    if self._running:
                        await asyncio.sleep(1)
                        continue
                break

        logger.debug("[ChatClient.RX] 接收循环结束")
        if self._running and self._reconnect:
            logger.info("[ChatClient.RX] 触发重连...")
            asyncio.create_task(self._schedule_reconnect())

    async def _send_loop(self):
        logger.debug("[ChatClient.TX] 发送循环已启动")
        while self._running:
            try:
                if not self._websocket:
                    logger.warning("[ChatClient.TX] WebSocket 已断开，退出发送循环")
                    break
                    
                if not self._send_queue.empty():
                    message = self._send_queue.get_nowait()
                    try:
                        await self._websocket.send(message)
                        logger.debug(f"[ChatClient.TX] 消息已发送 (长度: {len(message)})")
                    except Exception as send_error:
                        if hasattr(send_error, 'code'):
                            logger.warning(f"[ChatClient.TX] 发送时连接已关闭: code={send_error.code}")
                        else:
                            logger.error(f"[ChatClient.TX] 发送失败: {send_error}")
                        self._send_queue.put(message)
                        break
                else:
                    await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"[ChatClient.TX] 发送循环异常: {type(e).__name__}: {e}")
                break

        logger.debug("[ChatClient.TX] 发送循环结束")

    async def _ping_loop(self):
        logger.debug("[ChatClient] ping 循环已启动")
        while self._running and self._websocket:
            try:
                await asyncio.sleep(self.PING_INTERVAL)
                if self._websocket and self._running:
                    await self._websocket.ping()
            except Exception:
                break

    async def _schedule_reconnect(self):
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error("Max reconnect attempts reached")
            self._set_status(ConnectionStatus.ERROR)
            return

        self._set_status(ConnectionStatus.RECONNECTING)
        self._reconnect_attempts += 1

        delay = min(
            self.DEFAULT_RECONNECT_DELAY * (2 ** (self._reconnect_attempts - 1)),
            self.MAX_RECONNECT_DELAY
        )

        logger.info(f"Reconnecting in {delay}s (attempt {self._reconnect_attempts})")

        await asyncio.sleep(delay)
        await self._async_connect()

    def send_message(self, message: str) -> bool:
        logger.info(f"[ChatClient.TX] 发送消息请求 (长度: {len(message)})")
        
        with self._lock:
            current_status = self._status
            websocket_exists = self._websocket is not None
        
        if not websocket_exists or current_status != ConnectionStatus.CONNECTED:
            logger.warning(f"[ChatClient.TX] 未连接，无法发送消息 (status={current_status.value})")
            return False

        try:
            payload = {
                "type": "message",
                "id": str(uuid.uuid4()),
                "content": message,
                "timestamp": time.time()
            }
            
            message_json = json.dumps(payload)
            self._send_queue.put(message_json)
            logger.debug(f"[ChatClient.TX] 消息已加入发送队列")
            return True

        except Exception as e:
            logger.error(f"[ChatClient.TX] 构造消息失败: {type(e).__name__}: {e}")
            logger.error(f"[ChatClient.TX] 堆栈跟踪:\n{traceback.format_exc()}")
            return False

    def disconnect(self):
        logger.info("[ChatClient] 开始断开连接")
        logger.debug(f"[ChatClient] 调用来源: {''.join(traceback.format_stack()[-3:-1]).strip()}")
        self._running = False
        self._reconnect = False

        if self._loop and self._loop.is_running():
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._async_disconnect(),
                    self._loop
                )
                future.result(timeout=5)
                logger.debug("[ChatClient] WebSocket 已关闭")
            except Exception as e:
                logger.error(f"[ChatClient] 关闭 WebSocket 异常: {e}")
            
            self._loop.call_soon_threadsafe(self._loop.stop)
            
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=3)
            if self._loop_thread.is_alive():
                logger.warning("[ChatClient] 事件循环线程未能在超时内结束")

        self._set_status(ConnectionStatus.DISCONNECTED)
        self._websocket = None
        logger.info("[ChatClient] 断开连接完成")

    async def _async_disconnect(self):
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception:
                pass
        self._websocket = None

    def set_on_message(self, callback: Callable[[str], None]):
        self._on_message = callback

    def set_on_status_changed(self, callback: Callable[[ConnectionStatus], None]):
        self._on_status_changed = callback
