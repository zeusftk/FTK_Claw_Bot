# -*- coding: utf-8 -*-
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from loguru import logger


@dataclass
class BotChatState:
    """单个 Bot 的群聊状态"""
    bot_name: str
    timer: QTimer = field(default=None)
    message_buffer: List[Dict] = field(default_factory=list)
    last_speak_time: Optional[float] = None
    
    def __post_init__(self):
        if self.timer is None:
            self.timer = QTimer()
            self.timer.setSingleShot(True)


class GroupChatManager(QObject):
    """群聊管理器 - 管理多个 Bot 的独立计时器和消息缓冲"""
    
    # 信号
    message_to_bot = pyqtSignal(str, str, list)  # bot_name, trigger_reason, messages
    bot_reply_received = pyqtSignal(str, str)     # bot_name, content
    
    MAX_BUFFER_SIZE = 50
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bot_states: Dict[str, BotChatState] = {}
        self._message_history: List[Dict] = []
        self._interval_seconds: int = 5
        self._connected_bots: Set[str] = set()
    
    def set_interval(self, seconds: int):
        """设置转发间隔（秒）"""
        self._interval_seconds = max(1, min(60, seconds))
    
    def register_bot(self, bot_name: str):
        """注册一个 Bot"""
        if bot_name not in self._bot_states:
            state = BotChatState(bot_name=bot_name)
            state.timer.timeout.connect(lambda: self._on_bot_timer(bot_name))
            self._bot_states[bot_name] = state
            self._connected_bots.add(bot_name)
            logger.info(f"[GroupChat] 注册 Bot: {bot_name}")
    
    def unregister_bot(self, bot_name: str):
        """注销一个 Bot"""
        if bot_name in self._bot_states:
            state = self._bot_states.pop(bot_name)
            state.timer.stop()
            logger.info(f"[GroupChat] 注销 Bot: {bot_name}")
        self._connected_bots.discard(bot_name)
    
    def get_connected_bots(self) -> Set[str]:
        """获取已连接的 Bot 列表"""
        return self._connected_bots.copy()
    
    def _on_bot_timer(self, bot_name: str):
        """Bot 计时器到期处理"""
        if bot_name not in self._bot_states:
            return
        
        state = self._bot_states[bot_name]
        
        if not state.message_buffer:
            logger.debug(f"[GroupChat] {bot_name} 计时器到期，但缓冲区为空")
            return
        
        messages = state.message_buffer.copy()
        state.message_buffer.clear()
        
        logger.info(f"[GroupChat] {bot_name} 计时器到期，发送 {len(messages)} 条消息")
        self.message_to_bot.emit(bot_name, "timer_expired", messages)
    
    def parse_mentions(self, content: str) -> Set[str]:
        """解析消息中的 @ 提及"""
        pattern = r'@(\w+)'
        matches = re.findall(pattern, content)
        return {m for m in matches if m in self._connected_bots}
    
    def handle_user_message(self, content: str) -> Dict[str, str]:
        """
        处理用户消息
        返回: {bot_name: trigger_type} trigger_type 为 "mentioned" 或 "timer_started"
        """
        mentions = self.parse_mentions(content)
        
        message_entry = {
            "role": "user",
            "content": content,
            "name": "user",
            "timestamp": time.time()
        }
        self._message_history.append(message_entry)
        
        result = {}
        
        if mentions:
            # 有 @ 提及，只发给被 @ 的 Bot
            for bot_name in mentions:
                if bot_name in self._bot_states:
                    state = self._bot_states[bot_name]
                    state.message_buffer.append(message_entry)
                    state.timer.stop()
                    result[bot_name] = "mentioned"
                    logger.info(f"[GroupChat] 用户消息 @ {bot_name}，立即触发")
                    # 立即发送
                    messages = state.message_buffer.copy()
                    state.message_buffer.clear()
                    self.message_to_bot.emit(bot_name, "mentioned", messages)
        else:
            # 无 @ 提及，发给所有 Bot 开始计时
            for bot_name, state in self._bot_states.items():
                state.message_buffer.append(message_entry)
                state.timer.start(self._interval_seconds * 1000)
                result[bot_name] = "timer_started"
            logger.info(f"[GroupChat] 用户消息广播给所有 Bot，开始计时")
        
        return result
    
    def handle_bot_message(self, bot_name: str, content: str):
        """处理 Bot 消息"""
        if bot_name not in self._bot_states:
            logger.warning(f"[GroupChat] 未知 Bot: {bot_name}")
            return
        
        state = self._bot_states[bot_name]
        state.last_speak_time = time.time()
        state.timer.stop()
        
        message_entry = {
            "role": "assistant",
            "content": content,
            "name": bot_name,
            "timestamp": time.time()
        }
        self._message_history.append(message_entry)
        
        # 解析 Bot 消息中的 @ 提及
        mentions = self.parse_mentions(content)
        
        # 将消息加入其他 Bot 的缓冲区
        for other_name, other_state in self._bot_states.items():
            if other_name == bot_name:
                continue
            
            other_state.message_buffer.append(message_entry)
            
            # 限制缓冲区大小
            if len(other_state.message_buffer) > self.MAX_BUFFER_SIZE:
                other_state.message_buffer = other_state.message_buffer[-self.MAX_BUFFER_SIZE:]
            
            # 如果被 @ 则立即触发
            if other_name in mentions:
                other_state.timer.stop()
                messages = other_state.message_buffer.copy()
                other_state.message_buffer.clear()
                logger.info(f"[GroupChat] {bot_name} @ {other_name}，立即触发")
                self.message_to_bot.emit(other_name, "mentioned", messages)
            else:
                # 否则开始/重置计时器
                other_state.timer.start(self._interval_seconds * 1000)
        
        self.bot_reply_received.emit(bot_name, content)
    
    def get_messages_since(self, bot_name: str) -> List[Dict]:
        """获取 Bot 缓冲区中的消息"""
        if bot_name not in self._bot_states:
            return []
        
        state = self._bot_states[bot_name]
        return state.message_buffer.copy()
    
    def clear_all(self):
        """清空所有状态"""
        for state in self._bot_states.values():
            state.timer.stop()
            state.message_buffer.clear()
        self._message_history.clear()
        logger.info("[GroupChat] 清空所有状态")
    
    def stop_all_timers(self):
        """停止所有计时器"""
        for state in self._bot_states.values():
            state.timer.stop()
        logger.info("[GroupChat] 停止所有计时器")
