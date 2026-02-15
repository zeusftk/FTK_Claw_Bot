from datetime import datetime
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QTextCursor, QTextCharFormat


class ChatMessage:
    def __init__(self, role: str, content: str, timestamp: Optional[str] = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now().strftime("%H:%M")


class ChatPanel(QWidget):
    message_sent = pyqtSignal(str)
    connect_clicked = pyqtSignal()
    disconnect_clicked = pyqtSignal()
    clear_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._messages: List[ChatMessage] = []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        title = QLabel("聊天")
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        header_layout.addWidget(title)

        self.status_label = QLabel("未连接")
        self.status_label.setObjectName("statusLabel")
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()

        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        self.disconnect_btn = QPushButton("断开")
        self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self.disconnect_btn.setEnabled(False)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._on_clear_clicked)

        header_layout.addWidget(self.connect_btn)
        header_layout.addWidget(self.disconnect_btn)
        header_layout.addWidget(clear_btn)

        layout.addLayout(header_layout)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        self.chat_text = QTextEdit()
        self.chat_text.setReadOnly(True)
        self.chat_text.setFont(QFont("Microsoft YaHei UI", 10))
        self.chat_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.chat_text, 1)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("输入消息...")
        self.message_input.setFont(QFont("Microsoft YaHei UI", 10))
        self.message_input.returnPressed.connect(self._on_send_message)

        send_btn = QPushButton("发送")
        send_btn.clicked.connect(self._on_send_message)

        input_layout.addWidget(self.message_input, 1)
        input_layout.addWidget(send_btn)

        layout.addLayout(input_layout)

    def _on_connect_clicked(self):
        self.connect_clicked.emit()

    def _on_disconnect_clicked(self):
        self.disconnect_clicked.emit()

    def _on_clear_clicked(self):
        self.clear_clicked.emit()
        self._messages.clear()
        self.chat_text.clear()

    def _on_send_message(self):
        text = self.message_input.text().strip()
        if not text:
            return

        self.message_input.clear()

        self.add_message("user", text)
        self.message_sent.emit(text)

    def add_message(self, role: str, content: str):
        message = ChatMessage(role, content)
        self._messages.append(message)
        self._append_message(message)

    def _append_message(self, message: ChatMessage):
        cursor = self.chat_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        if message.role == "user":
            role_text = "你"
            role_color = QColor("#58a6ff")
            bg_color = QColor("#1f3a5f")
        elif message.role == "assistant":
            role_text = "AI"
            role_color = QColor("#3fb950")
            bg_color = QColor("#1a3a2f")
        else:
            role_text = message.role
            role_color = QColor("#8b949e")
            bg_color = QColor("#2d333b")

        format_text = QTextCharFormat()
        format_text.setBackground(bg_color)
        format_text.setForeground(role_color)
        cursor.insertText(f"[{role_text}] ", format_text)

        format_time = QTextCharFormat()
        format_time.setForeground(QColor("#8b949e"))
        format_time.setFontPointSize(9)
        cursor.insertText(f"{message.timestamp}\n", format_time)

        format_content = QTextCharFormat()
        format_content.setForeground(QColor("#c9d1d9"))
        cursor.insertText(f"{message.content}\n\n", format_content)

        scrollbar = self.chat_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def set_connection_status(self, connected: bool, status_text: str = ""):
        if connected:
            self.status_label.setText(f"已连接: {status_text}" if status_text else "已连接")
            self.status_label.setStyleSheet("color: #3fb950;")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.message_input.setEnabled(True)
        else:
            self.status_label.setText(status_text or "未连接")
            self.status_label.setStyleSheet("color: #8b949e;")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.message_input.setEnabled(False)

    def set_connecting(self):
        self.status_label.setText("连接中...")
        self.status_label.setStyleSheet("color: #d29922;")
        self.connect_btn.setEnabled(False)
        self.message_input.setEnabled(False)

    def show_error(self, message: str):
        self.status_label.setText(f"错误: {message}")
        self.status_label.setStyleSheet("color: #f85149;")

    def clear_messages(self):
        self._messages.clear()
        self.chat_text.clear()
