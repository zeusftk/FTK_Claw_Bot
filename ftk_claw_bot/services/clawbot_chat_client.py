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


def _get_thread_id() -> str:
    return f"T:{threading.current_thread().ident}:{threading.current_thread().name[:8]}"


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
        
        self._message_count = 0
        self._error_count = 0
        self._last_message_time = None
        
        logger.info(f"[ChatClient] 初始化完成, URL: {gateway_url}, 线程: {_get_thread_id()}")

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
            
        logger.info(f"[ChatClient] 状态变更: {old_status.value} -> {status.value}, "
                   f"线程: {_get_thread_id()}, "
                   f"消息数: {self._message_count}, 错误数: {self._error_count}")
        
        if self._on_status_changed:
            try:
                start_time = time.perf_counter()
                self._on_status_changed(status)
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.debug(f"[ChatClient] 状态回调执行完成, 耗时: {elapsed:.2f}ms")
            except Exception as e:
                self._error_count += 1
                logger.error(f"[ChatClient] 状态回调异常: {type(e).__name__}: {e}")
                logger.error(f"[ChatClient] 堆栈跟踪:\n{traceback.format_exc()}")

    def _get_connection_context(self) -> dict:
        return {
            "gateway_url": self._gateway_url,
            "status": self._status.value,
            "running": self._running,
            "websocket_exists": self._websocket is not None,
            "loop_exists": self._loop is not None,
            "loop_running": self._loop.is_running() if self._loop else False,
            "thread_alive": self._loop_thread.is_alive() if self._loop_thread else False,
            "send_queue_size": self._send_queue.qsize(),
            "message_count": self._message_count,
            "error_count": self._error_count,
            "reconnect_attempts": self._reconnect_attempts
        }

    def connect(self) -> bool:
        logger.info(f"[ChatClient] ========== 开始连接 ==========")
        logger.info(f"[ChatClient] 连接参数: URL={self._gateway_url}, reconnect={self._reconnect}, "
                   f"max_attempts={self._max_reconnect_attempts}")
        logger.debug(f"[ChatClient] 调用线程: {_get_thread_id()}")
        
        if not WEBSOCKETS_AVAILABLE:
            logger.error("[ChatClient] websockets library not available")
            return False

        with self._lock:
            current_status = self._status
            logger.debug(f"[ChatClient] 当前状态: {current_status.value}")
            
            if current_status == ConnectionStatus.CONNECTED:
                logger.warning("[ChatClient] 已经是连接状态，跳过连接")
                return True

        self._set_status(ConnectionStatus.CONNECTING)
        self._running = True

        try:
            logger.debug(f"[ChatClient] 创建新事件循环, 当前线程: {_get_thread_id()}")
            self._loop = asyncio.new_event_loop()
            
            self._loop_thread = threading.Thread(
                target=self._run_event_loop,
                daemon=True,
                name=f"ChatClient-{self._gateway_url.split('//')[1].split('/')[0]}"
            )
            
            logger.debug(f"[ChatClient] 启动事件循环线程: {self._loop_thread.name}")
            self._loop_thread.start()
            
            logger.debug(f"[ChatClient] 等待事件循环线程就绪...")
            time.sleep(0.1)
            
            if not self._loop_thread.is_alive():
                logger.error("[ChatClient] 事件循环线程启动失败")
                self._set_status(ConnectionStatus.ERROR)
                self._running = False
                return False
            
            logger.debug(f"[ChatClient] 开始异步连接...")
            future = asyncio.run_coroutine_threadsafe(
                self._async_connect(),
                self._loop
            )
            
            success = future.result(timeout=30)
            logger.info(f"[ChatClient] 连接完成，结果: {success}, 上下文: {self._get_connection_context()}")
            return success
            
        except TimeoutError as e:
            self._error_count += 1
            logger.error(f"[ChatClient] 连接超时: {e}")
            logger.error(f"[ChatClient] 上下文: {self._get_connection_context()}")
            self._set_status(ConnectionStatus.ERROR)
            self._running = False
            return False
        except Exception as e:
            self._error_count += 1
            logger.error(f"[ChatClient] 连接失败: {type(e).__name__}: {e}")
            logger.error(f"[ChatClient] 堆栈跟踪:\n{traceback.format_exc()}")
            logger.error(f"[ChatClient] 上下文: {self._get_connection_context()}")
            self._set_status(ConnectionStatus.ERROR)
            self._running = False
            return False

    def _run_event_loop(self):
        thread_id = _get_thread_id()
        logger.debug(f"[ChatClient.EventLoop] 事件循环线程启动: {thread_id}")
        
        asyncio.set_event_loop(self._loop)
        
        iteration = 0
        while self._running:
            iteration += 1
            try:
                logger.debug(f"[ChatClient.EventLoop] 开始运行事件循环 (迭代: {iteration})")
                self._loop.run_forever()
                logger.debug(f"[ChatClient.EventLoop] 事件循环正常退出 (迭代: {iteration})")
            except Exception as e:
                self._error_count += 1
                logger.error(f"[ChatClient.EventLoop] 事件循环异常 (迭代: {iteration}): {type(e).__name__}: {e}")
                logger.error(f"[ChatClient.EventLoop] 堆栈跟踪:\n{traceback.format_exc()}")
                
                if self._running:
                    logger.info("[ChatClient.EventLoop] 尝试恢复事件循环...")
                    time.sleep(1)
                    
        logger.debug(f"[ChatClient.EventLoop] 事件循环线程结束: {thread_id}")

    async def _async_connect(self) -> bool:
        logger.info(f"[ChatClient.Async] 开始异步连接到: {self._gateway_url}")
        logger.debug(f"[ChatClient.Async] 连接参数: ping_interval={self.PING_INTERVAL}, "
                    f"ping_timeout=10, open_timeout=10")
        logger.debug(f"[ChatClient.Async] 当前线程: {_get_thread_id()}")
        
        try:
            logger.debug("[ChatClient.Async] 正在建立 WebSocket 连接...")
            connect_start = time.perf_counter()
            
            self._websocket = await websockets.connect(
                self._gateway_url,
                ping_interval=self.PING_INTERVAL,
                ping_timeout=10,
                open_timeout=10
            )
            
            connect_elapsed = (time.perf_counter() - connect_start) * 1000
            logger.info(f"[ChatClient.Async] ✅ WebSocket 连接建立成功！耗时: {connect_elapsed:.2f}ms")
            logger.debug(f"[ChatClient.Async] WebSocket 信息: "
                        f"local={self._websocket.local_address if hasattr(self._websocket, 'local_address') else 'N/A'}, "
                        f"remote={self._websocket.remote_address if hasattr(self._websocket, 'remote_address') else 'N/A'}")
            
            self._set_status(ConnectionStatus.CONNECTED)
            self._reconnect_attempts = 0

            receive_task = asyncio.create_task(self._receive_loop())
            send_task = asyncio.create_task(self._send_loop())
            ping_task = asyncio.create_task(self._ping_loop())
            
            logger.debug(f"[ChatClient.Async] 已启动任务: receive={receive_task.get_name()}, "
                        f"send={send_task.get_name()}, ping={ping_task.get_name()}")

            logger.info(f"[ChatClient.Async] 成功连接到 {self._gateway_url}")
            return True

        except ConnectionRefusedError as e:
            self._error_count += 1
            logger.error(f"[ChatClient.Async] ❌ 连接被拒绝: {e}")
            logger.error(f"[ChatClient.Async] 请确认 clawbot gateway 是否正在运行，端口是否正确")
            logger.error(f"[ChatClient.Async] 上下文: {self._get_connection_context()}")
            self._set_status(ConnectionStatus.ERROR)
            if self._reconnect and self._reconnect_attempts < self._max_reconnect_attempts:
                asyncio.create_task(self._schedule_reconnect())
            return False
        except asyncio.TimeoutError as e:
            self._error_count += 1
            logger.error(f"[ChatClient.Async] ❌ 连接超时: {e}")
            logger.error(f"[ChatClient.Async] 上下文: {self._get_connection_context()}")
            self._set_status(ConnectionStatus.ERROR)
            if self._reconnect and self._reconnect_attempts < self._max_reconnect_attempts:
                asyncio.create_task(self._schedule_reconnect())
            return False
        except Exception as e:
            self._error_count += 1
            logger.error(f"[ChatClient.Async] ❌ WebSocket 连接失败: {type(e).__name__}: {e}")
            logger.error(f"[ChatClient.Async] 堆栈跟踪:\n{traceback.format_exc()}")
            logger.error(f"[ChatClient.Async] 上下文: {self._get_connection_context()}")
            self._set_status(ConnectionStatus.ERROR)
            if self._reconnect and self._reconnect_attempts < self._max_reconnect_attempts:
                asyncio.create_task(self._schedule_reconnect())
            return False

    async def _receive_loop(self):
        logger.debug(f"[ChatClient.RX] 接收循环已启动, 线程: {_get_thread_id()}")
        consecutive_errors = 0
        max_consecutive_errors = 5
        message_count = 0
        
        while self._running and self._websocket:
            try:
                receive_start = time.perf_counter()
                message = await asyncio.wait_for(
                    self._websocket.recv(),
                    timeout=self.MESSAGE_TIMEOUT
                )
                receive_elapsed = (time.perf_counter() - receive_start) * 1000
                consecutive_errors = 0
                message_count += 1
                self._message_count += 1
                self._last_message_time = datetime.now() if 'datetime' in dir() else time.time()
                
                logger.debug(f"[ChatClient.RX] 收到消息 #{message_count} "
                           f"(长度: {len(message)}, 接收耗时: {receive_elapsed:.2f}ms)")

                if message and self._on_message:
                    callback_start = time.perf_counter()
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        
                        if msg_type == "ping":
                            logger.debug("[ChatClient.RX] 收到 ping 消息，忽略")
                            continue
                        
                        content = data.get("content", data.get("message", str(message)))
                        content_preview = content[:100] + "..." if len(content) > 100 else content
                        logger.debug(f"[ChatClient.RX] 提取内容 (类型: {msg_type}, "
                                   f"长度: {len(content)}, 预览: {content_preview})")
                        
                        try:
                            self._on_message(content)
                            callback_elapsed = (time.perf_counter() - callback_start) * 1000
                            logger.debug(f"[ChatClient.RX] 消息回调完成, 耗时: {callback_elapsed:.2f}ms")
                        except Exception as callback_error:
                            self._error_count += 1
                            logger.error(f"[ChatClient.RX] 消息回调异常: {type(callback_error).__name__}: {callback_error}")
                            logger.error(f"[ChatClient.RX] 消息内容预览: {content_preview}")
                            logger.error(f"[ChatClient.RX] 堆栈跟踪:\n{traceback.format_exc()}")
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"[ChatClient.RX] JSON 解析失败: {e}, "
                                     f"原始消息前100字符: {message[:100]}")
                        if self._on_message:
                            try:
                                self._on_message(str(message))
                            except Exception as callback_error:
                                self._error_count += 1
                                logger.error(f"[ChatClient.RX] 原始消息回调异常: {callback_error}")

            except asyncio.TimeoutError:
                logger.debug("[ChatClient.RX] 接收超时，继续等待...")
                continue
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"[ChatClient.RX] WebSocket 连接已关闭: code={e.code}, "
                             f"reason={e.reason}, rcvd={e.rcvd}")
                break
            except Exception as e:
                consecutive_errors += 1
                self._error_count += 1
                
                if hasattr(e, 'code'):
                    logger.warning(f"[ChatClient.RX] WebSocket 关闭: code={e.code}, "
                                 f"reason={getattr(e, 'reason', 'unknown')}")
                    break
                else:
                    logger.error(f"[ChatClient.RX] 接收错误 ({consecutive_errors}/{max_consecutive_errors}): "
                               f"{type(e).__name__}: {e}")
                    logger.error(f"[ChatClient.RX] 堆栈跟踪:\n{traceback.format_exc()}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("[ChatClient.RX] 连续错误次数过多，退出接收循环")
                        break
                        
                    if self._running:
                        await asyncio.sleep(1)
                        continue
                break

        logger.debug(f"[ChatClient.RX] 接收循环结束, 共处理 {message_count} 条消息, "
                   f"线程: {_get_thread_id()}")
        if self._running and self._reconnect:
            logger.info("[ChatClient.RX] 触发重连...")
            asyncio.create_task(self._schedule_reconnect())

    async def _send_loop(self):
        logger.debug(f"[ChatClient.TX] 发送循环已启动, 线程: {_get_thread_id()}")
        sent_count = 0
        
        while self._running:
            try:
                if not self._websocket:
                    logger.warning("[ChatClient.TX] WebSocket 已断开，退出发送循环")
                    break
                    
                if not self._send_queue.empty():
                    queue_size = self._send_queue.qsize()
                    message = self._send_queue.get_nowait()
                    
                    send_start = time.perf_counter()
                    try:
                        await self._websocket.send(message)
                        send_elapsed = (time.perf_counter() - send_start) * 1000
                        sent_count += 1
                        
                        logger.debug(f"[ChatClient.TX] 消息已发送 #{sent_count} "
                                   f"(长度: {len(message)}, 耗时: {send_elapsed:.2f}ms, "
                                   f"队列剩余: {queue_size - 1})")
                    except websockets.exceptions.ConnectionClosed as e:
                        logger.warning(f"[ChatClient.TX] 发送时连接已关闭: code={e.code}")
                        self._send_queue.put(message)
                        break
                    except Exception as send_error:
                        self._error_count += 1
                        if hasattr(send_error, 'code'):
                            logger.warning(f"[ChatClient.TX] 发送时连接已关闭: code={send_error.code}")
                        else:
                            logger.error(f"[ChatClient.TX] 发送失败: {type(send_error).__name__}: {send_error}")
                            logger.error(f"[ChatClient.TX] 堆栈跟踪:\n{traceback.format_exc()}")
                        self._send_queue.put(message)
                        break
                else:
                    await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                logger.debug("[ChatClient.TX] 发送循环被取消")
                break
            except Exception as e:
                self._error_count += 1
                logger.error(f"[ChatClient.TX] 发送循环异常: {type(e).__name__}: {e}")
                logger.error(f"[ChatClient.TX] 堆栈跟踪:\n{traceback.format_exc()}")
                break

        logger.debug(f"[ChatClient.TX] 发送循环结束, 共发送 {sent_count} 条消息, "
                   f"线程: {_get_thread_id()}")

    async def _ping_loop(self):
        logger.debug(f"[ChatClient.Ping] ping 循环已启动, 间隔: {self.PING_INTERVAL}s")
        ping_count = 0
        
        while self._running and self._websocket:
            try:
                await asyncio.sleep(self.PING_INTERVAL)
                if self._websocket and self._running:
                    ping_start = time.perf_counter()
                    await self._websocket.ping()
                    ping_elapsed = (time.perf_counter() - ping_start) * 1000
                    ping_count += 1
                    logger.debug(f"[ChatClient.Ping] ping #{ping_count} 完成, 耗时: {ping_elapsed:.2f}ms")
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"[ChatClient.Ping] ping 时连接已关闭: code={e.code}")
                break
            except asyncio.CancelledError:
                logger.debug("[ChatClient.Ping] ping 循环被取消")
                break
            except Exception as e:
                self._error_count += 1
                logger.error(f"[ChatClient.Ping] ping 异常: {type(e).__name__}: {e}")
                break
                
        logger.debug(f"[ChatClient.Ping] ping 循环结束, 共发送 {ping_count} 次")

    async def _schedule_reconnect(self):
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error(f"[ChatClient.Reconnect] 达到最大重连次数 {self._max_reconnect_attempts}")
            self._set_status(ConnectionStatus.ERROR)
            return

        self._set_status(ConnectionStatus.RECONNECTING)
        self._reconnect_attempts += 1

        delay = min(
            self.DEFAULT_RECONNECT_DELAY * (2 ** (self._reconnect_attempts - 1)),
            self.MAX_RECONNECT_DELAY
        )

        logger.info(f"[ChatClient.Reconnect] 计划重连 (尝试 {self._reconnect_attempts}/{self._max_reconnect_attempts}), "
                   f"延迟: {delay}s, 上下文: {self._get_connection_context()}")

        await asyncio.sleep(delay)
        await self._async_connect()

    def send_message(self, message: str) -> bool:
        logger.debug(f"[ChatClient.TX] 发送消息请求 (长度: {len(message)}), 线程: {_get_thread_id()}")
        
        with self._lock:
            current_status = self._status
            websocket_exists = self._websocket is not None
        
        if not websocket_exists or current_status != ConnectionStatus.CONNECTED:
            logger.warning(f"[ChatClient.TX] 未连接，无法发送消息 (status={current_status.value}, "
                         f"websocket={websocket_exists})")
            return False

        try:
            payload = {
                "type": "message",
                "id": str(uuid.uuid4()),
                "content": message,
                "timestamp": time.time()
            }
            
            message_json = json.dumps(payload)
            queue_size = self._send_queue.qsize()
            self._send_queue.put(message_json)
            
            logger.debug(f"[ChatClient.TX] 消息已加入发送队列 (ID: {payload['id']}, "
                        f"队列大小: {queue_size + 1})")
            return True

        except Exception as e:
            self._error_count += 1
            logger.error(f"[ChatClient.TX] 构造消息失败: {type(e).__name__}: {e}")
            logger.error(f"[ChatClient.TX] 堆栈跟踪:\n{traceback.format_exc()}")
            return False

    def disconnect(self):
        logger.info(f"[ChatClient] ========== 开始断开连接 ==========")
        logger.debug(f"[ChatClient] 调用来源: {''.join(traceback.format_stack()[-3:-1]).strip()}")
        logger.debug(f"[ChatClient] 当前线程: {_get_thread_id()}")
        logger.debug(f"[ChatClient] 断开前上下文: {self._get_connection_context()}")
        
        self._running = False
        self._reconnect = False

        if self._loop and self._loop.is_running():
            try:
                logger.debug("[ChatClient] 正在关闭 WebSocket...")
                future = asyncio.run_coroutine_threadsafe(
                    self._async_disconnect(),
                    self._loop
                )
                future.result(timeout=5)
                logger.debug("[ChatClient] WebSocket 已关闭")
            except Exception as e:
                logger.error(f"[ChatClient] 关闭 WebSocket 异常: {type(e).__name__}: {e}")
            
            logger.debug("[ChatClient] 正在停止事件循环...")
            self._loop.call_soon_threadsafe(self._loop.stop)
            
        if self._loop_thread and self._loop_thread.is_alive():
            logger.debug(f"[ChatClient] 等待事件循环线程结束 (线程: {self._loop_thread.name})...")
            self._loop_thread.join(timeout=3)
            if self._loop_thread.is_alive():
                logger.warning("[ChatClient] 事件循环线程未能在超时内结束")
            else:
                logger.debug("[ChatClient] 事件循环线程已结束")

        self._set_status(ConnectionStatus.DISCONNECTED)
        self._websocket = None
        
        logger.info(f"[ChatClient] 断开连接完成, 最终统计: 消息数={self._message_count}, "
                   f"错误数={self._error_count}")

    async def _async_disconnect(self):
        if self._websocket:
            try:
                await self._websocket.close()
                logger.debug("[ChatClient.Async] WebSocket 关闭成功")
            except Exception as e:
                logger.debug(f"[ChatClient.Async] WebSocket 关闭异常 (可忽略): {type(e).__name__}")
        self._websocket = None

    def set_on_message(self, callback: Callable[[str], None]):
        logger.debug(f"[ChatClient] 设置消息回调: {callback.__name__ if hasattr(callback, '__name__') else 'lambda'}")
        self._on_message = callback

    def set_on_status_changed(self, callback: Callable[[ConnectionStatus], None]):
        logger.debug(f"[ChatClient] 设置状态回调: {callback.__name__ if hasattr(callback, '__name__') else 'lambda'}")
        self._on_status_changed = callback
        
    def get_stats(self) -> dict:
        return {
            "gateway_url": self._gateway_url,
            "status": self._status.value,
            "message_count": self._message_count,
            "error_count": self._error_count,
            "last_message_time": self._last_message_time,
            "reconnect_attempts": self._reconnect_attempts,
            "send_queue_size": self._send_queue.qsize()
        }
