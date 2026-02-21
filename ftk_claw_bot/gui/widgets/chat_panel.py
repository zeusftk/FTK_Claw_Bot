from datetime import datetime
from typing import List, Optional, Set, Dict

from loguru import logger

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QFrame, QListWidget, QListWidgetItem,
    QToolButton, QSizePolicy, QSpacerItem, QCheckBox, QSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QEvent
from PyQt6.QtGui import QFont, QColor, QTextCursor, QTextCharFormat, QCursor

from ..mixins import WSLStateAwareMixin
from ...utils.async_ops import AsyncOperation, AsyncResult
from ...utils.i18n import tr


class ChatMessage:
    def __init__(self, role: str, content: str, nanobot_name: Optional[str] = None, 
                 timestamp: Optional[str] = None, message_type: str = "text"):
        self.role = role
        self.content = content
        self.nanobot_name = nanobot_name
        self.timestamp = timestamp or datetime.now().strftime("%H:%M")
        self.message_type = message_type


class SelectedNanobotTag(QWidget):
    removed = pyqtSignal(str)
    
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        self.setStyleSheet("""
            SelectedNanobotTag {
                background-color: #238636;
                border-radius: 12px;
            }
        """)
        
        name_label = QLabel(self.name)
        name_label.setStyleSheet("color: #f0f6fc; font-weight: 500;")
        layout.addWidget(name_label)
        
        remove_btn = QToolButton()
        remove_btn.setText("✕")
        remove_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                color: #c9d1d9;
                border: none;
                font-size: 12px;
                font-weight: bold;
            }
            QToolButton:hover {
                color: #f0f6fc;
            }
        """)
        remove_btn.setFixedSize(16, 16)
        remove_btn.clicked.connect(lambda: self.removed.emit(self.name))
        layout.addWidget(remove_btn)


class ConnectedBotTag(QFrame):
    disconnect_clicked = pyqtSignal(str)
    
    def __init__(self, bot_name: str, address: str, parent=None):
        super().__init__(parent)
        self.bot_name = bot_name
        self.address = address
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            ConnectedBotTag {
                background-color: #1a3a2f;
                border: 1px solid #3fb950;
                border-radius: 6px;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        
        status_dot = QLabel("✓")
        status_dot.setStyleSheet("color: #3fb950; font-weight: bold;")
        layout.addWidget(status_dot)
        
        name_label = QLabel(self.bot_name)
        name_label.setStyleSheet("color: #f0f6fc; font-weight: 600; font-size: 11px;")
        layout.addWidget(name_label)
        
        addr_label = QLabel(f"({self.address})")
        addr_label.setStyleSheet("color: #8b949e; font-size: 10px;")
        layout.addWidget(addr_label)
        
        disconnect_btn = QToolButton()
        disconnect_btn.setText("✕")
        disconnect_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                color: #f85149;
                border: none;
                font-size: 12px;
                font-weight: bold;
            }
            QToolButton:hover {
                color: #da3633;
            }
        """)
        disconnect_btn.setFixedSize(16, 16)
        disconnect_btn.clicked.connect(lambda: self.disconnect_clicked.emit(self.bot_name))
        layout.addWidget(disconnect_btn)


class NanobotCard(QFrame):
    clicked = pyqtSignal(str)
    connect_clicked = pyqtSignal(str)
    disconnect_clicked = pyqtSignal(str)
    
    def __init__(self, config_name: str, config=None, parent=None):
        super().__init__(parent)
        self.config_name = config_name
        self.config = config
        self.is_selected = False
        self.wsl_status = "stopped"
        self.nanobot_status = "stopped"
        self.connection_status = "disconnected"
        self._init_ui()
    
    def _init_ui(self):
        self.setObjectName("nanobotCard")
        self.setFixedHeight(130)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(12)
        
        status_layout = QVBoxLayout()
        status_layout.setSpacing(4)
        
        self.wsl_status_dot = QLabel("⚪")
        self.wsl_status_dot.setFixedSize(24, 24)
        self.wsl_status_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.wsl_status_dot.setStyleSheet("font-size: 18px;")
        status_layout.addWidget(self.wsl_status_dot)
        
        self.nanobot_status_dot = QLabel("⚪")
        self.nanobot_status_dot.setFixedSize(24, 24)
        self.nanobot_status_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nanobot_status_dot.setStyleSheet("font-size: 18px;")
        status_layout.addWidget(self.nanobot_status_dot)
        
        main_layout.addLayout(status_layout)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        
        self.name_label = QLabel(self.config_name)
        self.name_label.setStyleSheet("color: #c9d1d9; font-size: 14px; font-weight: 600;")
        info_layout.addWidget(self.name_label)
        
        status_text_layout = QVBoxLayout()
        status_text_layout.setSpacing(2)
        
        self.wsl_status_text = QLabel(tr("chat.status.wsl_stopped", "WSL: 已停止"))
        self.wsl_status_text.setStyleSheet("color: #8b949e; font-size: 10px;")
        status_text_layout.addWidget(self.wsl_status_text)
        
        self.nanobot_status_text = QLabel(tr("chat.status.bot_stopped", "Bot: 已停止"))
        self.nanobot_status_text.setStyleSheet("color: #8b949e; font-size: 10px;")
        status_text_layout.addWidget(self.nanobot_status_text)
        
        self.model_text = QLabel(tr("chat.status.model_none", "模型: --"))
        self.model_text.setStyleSheet("color: #8b949e; font-size: 10px;")
        status_text_layout.addWidget(self.model_text)
        
        info_layout.addLayout(status_text_layout)
        
        action_layout = QHBoxLayout()
        action_layout.setSpacing(6)
        
        self.connect_btn = QPushButton(tr("chat.btn.connect", "连接"))
        self.connect_btn.setFixedSize(60, 28)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                border: 1px solid #2ea043;
                border-radius: 4px;
                color: #ffffff;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
            QPushButton:pressed {
                background-color: #196c2e;
            }
            QPushButton:disabled {
                background-color: #484f58;
                border-color: #30363d;
                color: #8b949e;
            }
        """)
        self.connect_btn.clicked.connect(lambda: self._on_connect_clicked())
        action_layout.addWidget(self.connect_btn)
        
        self.view_log_btn = QPushButton(tr("chat.log", "日志"))
        self.view_log_btn.setFixedSize(50, 28)
        self.view_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 4px;
                color: #c9d1d9;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #484f58;
            }
        """)
        action_layout.addWidget(self.view_log_btn)
        
        action_layout.addStretch()
        info_layout.addLayout(action_layout)
        
        main_layout.addLayout(info_layout, 1)
        main_layout.addStretch()
        
        if self.config:
            self.set_model(self.config.model, self.config.provider)
        
        self._update_style()
    
    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._update_style()
    
    def set_wsl_status(self, status: str):
        self.wsl_status = status
        status_lower = status.lower()
        if "running" in status_lower:
            self.wsl_status_dot.setText("🟢")
            self.wsl_status_text.setText(tr("chat.status.wsl_running", "WSL: 运行中"))
            self.wsl_status_text.setStyleSheet("color: #3fb950; font-size: 10px;")
        elif "stopped" in status_lower:
            self.wsl_status_dot.setText("⚪")
            self.wsl_status_text.setText(tr("chat.status.wsl_stopped", "WSL: 已停止"))
            self.wsl_status_text.setStyleSheet("color: #8b949e; font-size: 10px;")
        else:
            self.wsl_status_dot.setText("⚪")
            self.wsl_status_text.setText(f"WSL: {status}")
            self.wsl_status_text.setStyleSheet("color: #8b949e; font-size: 10px;")
    
    def set_nanobot_status(self, status: str):
        self.nanobot_status = status
        if status == "running":
            self.nanobot_status_dot.setText("🟢")
            self.nanobot_status_text.setText(tr("chat.status.bot_running", "Bot: 运行中"))
            self.nanobot_status_text.setStyleSheet("color: #3fb950; font-size: 10px;")
        elif status == "starting":
            self.nanobot_status_dot.setText("🟡")
            self.nanobot_status_text.setText(tr("chat.status.bot_starting", "Bot: 启动中"))
            self.nanobot_status_text.setStyleSheet("color: #d29922; font-size: 10px;")
        elif status == "error":
            self.nanobot_status_dot.setText("🔴")
            self.nanobot_status_text.setText(tr("chat.status.bot_error", "Bot: 错误"))
            self.nanobot_status_text.setStyleSheet("color: #f85149; font-size: 10px;")
        else:
            self.nanobot_status_dot.setText("⚪")
            self.nanobot_status_text.setText(tr("chat.status.bot_stopped", "Bot: 已停止"))
            self.nanobot_status_text.setStyleSheet("color: #8b949e; font-size: 10px;")
    
    def set_model(self, model: str, provider: str = None):
        if model:
            short_model = model.split("/")[-1] if "/" in model else model
            display_text = tr("chat.status.model", "模型: {}").format(model=short_model)
        else:
            display_text = tr("chat.status.model_none", "模型: --")
        self.model_text.setText(display_text)
    
    def set_connection_status(self, status: str):
        self.connection_status = status
        if status == "connected":
            self.connect_btn.setText(tr("chat.btn.disconnect", "断开"))
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #da3633;
                    border: 1px solid #f85149;
                    border-radius: 4px;
                    color: #ffffff;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #f85149;
                }
                QPushButton:pressed {
                    background-color: #b62324;
                }
            """)
            self.connect_btn.setEnabled(True)
        elif status == "connecting":
            self.connect_btn.setText(tr("chat.btn.connecting", "连接中..."))
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #484f58;
                    border: 1px solid #30363d;
                    border-radius: 4px;
                    color: #8b949e;
                    font-size: 11px;
                }
            """)
            self.connect_btn.setEnabled(False)
        else:
            self.connect_btn.setText(tr("chat.btn.connect", "连接"))
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #238636;
                    border: 1px solid #2ea043;
                    border-radius: 4px;
                    color: #ffffff;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #2ea043;
                }
                QPushButton:pressed {
                    background-color: #196c2e;
                }
            """)
            self.connect_btn.setEnabled(True)
    
    def _on_connect_clicked(self):
        if self.connection_status == "connected":
            self.disconnect_clicked.emit(self.config_name)
        else:
            self.connect_clicked.emit(self.config_name)
    
    def _update_style(self):
        if self.is_selected:
            self.setStyleSheet("""
                QFrame#nanobotCard {
                    background-color: rgba(88, 166, 255, 0.15);
                    border: 2px solid #58a6ff;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#nanobotCard {
                    background-color: #21262d;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                }
                QFrame#nanobotCard:hover {
                    background-color: #30363d;
                    border-color: #484f58;
                }
            """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.config_name)
        super().mousePressEvent(event)


class ChatPanel(QWidget, WSLStateAwareMixin):
    message_sent = pyqtSignal(str, list)
    connect_clicked = pyqtSignal(str)
    disconnect_clicked = pyqtSignal(str)
    clear_clicked = pyqtSignal()
    nanobot_selected = pyqtSignal(list)
    nanobot_connect_requested = pyqtSignal(str)
    nanobot_disconnect_requested = pyqtSignal(str)
    
    _BOT_COLORS = [
        ("#3fb950", "#1a3a2f"),
        ("#58a6ff", "#1f3a5f"),
        ("#d29922", "#3a3a1a"),
        ("#f85149", "#3a1a1a"),
        ("#a371f7", "#2a1a3a"),
    ]
    
    def __init__(self, config_manager=None, nanobot_controller=None, wsl_manager=None, parent=None):
        super().__init__(parent)
        WSLStateAwareMixin._init_wsl_state_aware(self)
        self._config_manager = config_manager
        self._nanobot_controller = nanobot_controller
        self._wsl_manager = wsl_manager
        self._messages: List[ChatMessage] = []
        self._nanobot_cards = {}
        self._selected_nanobots: Set[str] = set()
        self._tag_widgets = {}
        self._connection_status = {}
        self._connected_bot_info = {}
        self._bot_color_map = {}
        self._group_chat_enabled = False
        
        self._init_ui()
        self._start_timer()
        self._load_nanobots()
    
    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel)
        
        right_panel = self._create_right_panel()
        main_layout.addWidget(right_panel, 1)
    
    def _create_left_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setFixedWidth(300)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        header = QHBoxLayout()
        title = QLabel(tr("chat.title", "Clawbot 选择"))
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("color: #f0f6fc;")
        header.addWidget(title)
        header.addStretch()
        
        refresh_btn = QToolButton()
        refresh_btn.setText("🔄")
        refresh_btn.setObjectName("smallButton")
        refresh_btn.setFixedSize(32, 32)
        refresh_btn.setStyleSheet("""
            QToolButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                color: #c9d1d9;
                font-size: 14px;
            }
            QToolButton:hover {
                background-color: #30363d;
                border-color: #484f58;
            }
        """)
        refresh_btn.clicked.connect(self._refresh_nanobots)
        header.addWidget(refresh_btn)
        
        layout.addLayout(header)
        
        action_layout = QHBoxLayout()
        self.select_all_btn = QPushButton(tr("chat.select_all", "全选"))
        self.select_all_btn.setObjectName("smallButton")
        self.select_all_btn.clicked.connect(self._select_all)
        self.deselect_all_btn = QPushButton(tr("chat.deselect_all", "取消全选"))
        self.deselect_all_btn.setObjectName("smallButton")
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        action_layout.addWidget(self.select_all_btn)
        action_layout.addWidget(self.deselect_all_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        self.nanobot_list = QListWidget()
        self.nanobot_list.setObjectName("nanobotList")
        self.nanobot_list.setStyleSheet("""
            QListWidget#nanobotList {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget#nanobotList::item {
                padding: 0px;
                margin: 4px 0px;
            }
        """)
        self.nanobot_list.setSpacing(8)
        layout.addWidget(self.nanobot_list, 1)
        
        return panel
    
    def _create_right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("rightPanel")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        header_layout = QHBoxLayout()
        title = QLabel(tr("chat.chat_title", "聊天"))
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("color: #f0f6fc;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
        
        self._connection_status_container = QWidget()
        self._connection_status_layout = QHBoxLayout(self._connection_status_container)
        self._connection_status_layout.setContentsMargins(0, 0, 0, 0)
        self._connection_status_layout.setSpacing(8)
        self._connection_status_layout.addStretch()
        
        status_layout.addWidget(self._connection_status_container)
        
        self._connect_btn = QPushButton(tr("chat.connect_all", "连接全部"))
        self._connect_btn.setObjectName("smallButton")
        self._connect_btn.clicked.connect(self._on_connect_all_clicked)
        status_layout.addWidget(self._connect_btn)
        
        header_layout.addLayout(status_layout)
        
        clear_btn = QPushButton(tr("btn.clear", "清空"))
        clear_btn.setObjectName("smallButton")
        clear_btn.clicked.connect(self._clear_clicked)
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        self.tags_container = QWidget()
        tags_layout = QHBoxLayout(self.tags_container)
        tags_layout.setContentsMargins(0, 0, 0, 0)
        tags_layout.setSpacing(8)
        
        self.tags_label = QLabel(tr("chat.selected_none", "已选: 无"))
        self.tags_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        tags_layout.addWidget(self.tags_label)
        tags_layout.addStretch()
        
        self.tags_scroll = QScrollArea()
        self.tags_scroll.setWidget(self.tags_container)
        self.tags_scroll.setWidgetResizable(True)
        self.tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tags_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tags_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.tags_scroll.setFixedHeight(40)
        self.tags_scroll.setStyleSheet("background-color: #238636;")
        layout.addWidget(self.tags_scroll)
        
        self.chat_text = QTextEdit()
        self.chat_text.setReadOnly(True)
        self.chat_text.setFont(QFont("Microsoft YaHei UI", 10))
        self.chat_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.chat_text.setStyleSheet("""
            QTextEdit {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        layout.addWidget(self.chat_text, 1)
        
        input_layout = QVBoxLayout()
        input_layout.setSpacing(8)
        
        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(8)
        
        self.group_chat_checkbox = QCheckBox(tr("chat.group_mode", "群聊模式"))
        self.group_chat_checkbox.setToolTip(tr("chat.group_mode_hint", "开启后，Bot的回复会转发给其他选中的Bot进行持续对话"))
        self.group_chat_checkbox.setStyleSheet("""
            QCheckBox {
                color: #8b949e;
                font-size: 12px;
                spacing: 6px;
            }
            QCheckBox:checked {
                color: #58a6ff;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        self.group_chat_checkbox.stateChanged.connect(self._on_group_chat_toggled)
        tools_layout.addWidget(self.group_chat_checkbox)
        
        self.group_chat_interval_spin = QSpinBox()
        self.group_chat_interval_spin.setRange(1, 60)
        self.group_chat_interval_spin.setValue(5)
        self.group_chat_interval_spin.setSuffix(tr("chat.seconds", "秒"))
        self.group_chat_interval_spin.setToolTip(tr("chat.forward_interval", "群聊转发间隔"))
        self.group_chat_interval_spin.setStyleSheet("""
            QSpinBox {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 4px;
                color: #c9d1d9;
                font-size: 11px;
                padding: 2px 4px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
            }
        """)
        tools_layout.addWidget(self.group_chat_interval_spin)
        
        tools_layout.addStretch()
        
        attach_btn = QToolButton()
        attach_btn.setText("📎")
        attach_btn.setStyleSheet("""
            QToolButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                color: #c9d1d9;
                font-size: 16px;
                padding: 6px;
            }
            QToolButton:hover {
                background-color: #30363d;
                border-color: #484f58;
            }
        """)
        attach_btn.setFixedSize(36, 36)
        voice_btn = QToolButton()
        voice_btn.setText("🎤")
        voice_btn.setStyleSheet("""
            QToolButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                color: #c9d1d9;
                font-size: 16px;
                padding: 6px;
            }
            QToolButton:hover {
                background-color: #30363d;
                border-color: #484f58;
            }
        """)
        voice_btn.setFixedSize(36, 36)
        
        tools_layout.addWidget(attach_btn)
        tools_layout.addWidget(voice_btn)
        
        input_layout.addLayout(tools_layout)
        
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText(tr("chat.input_placeholder", "在此输入消息，按 Ctrl+Enter 发送，Enter 换行"))
        self.message_input.setFont(QFont("Microsoft YaHei UI", 10))
        self.message_input.setMaximumHeight(120)
        self.message_input.setAcceptRichText(False)
        self.message_input.setStyleSheet("""
            QTextEdit {
                background-color: #161b22;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 10px;
            }
            QTextEdit:focus {
                border: 2px solid #58a6ff;
            }
        """)
        
        input_buttons_layout = QHBoxLayout()
        input_buttons_layout.setSpacing(10)
        input_buttons_layout.addStretch()
        
        send_btn = QPushButton(tr("chat.send", "发送 (Ctrl+Enter)"))
        send_btn.setObjectName("primaryButton")
        send_btn.clicked.connect(self._on_send_message)
        
        input_buttons_layout.addWidget(send_btn)
        
        input_layout.addWidget(self.message_input)
        input_layout.addLayout(input_buttons_layout)
        
        layout.addLayout(input_layout)
        
        return panel
    
    def _start_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_nanobot_status_async)
        self._timer.start(3000)
    
    def _load_nanobots(self):
        if not self._config_manager:
            return
        
        self.nanobot_list.clear()
        self._nanobot_cards = {}
        
        valid_distro_names = set()
        if self._wsl_manager:
            distros = self._wsl_manager.list_distros()
            valid_distro_names = {d.name for d in distros}
        
        configs = self._config_manager.get_all()
        for name in sorted(configs.keys()):
            config = configs[name]
            if config.distro_name and config.distro_name in valid_distro_names:
                self._add_nanobot_card(name, config)
        
        self._refresh_nanobot_status()
    
    def _add_nanobot_card(self, config_name: str, config=None):
        item = QListWidgetItem(self.nanobot_list)
        card = NanobotCard(config_name, config)
        card.clicked.connect(self._on_card_clicked)
        card.connect_clicked.connect(self._on_nanobot_connect_requested)
        card.disconnect_clicked.connect(self._on_nanobot_disconnect_requested)
        self._nanobot_cards[config_name] = card
        item.setSizeHint(QSize(0, 140))
        self.nanobot_list.addItem(item)
        self.nanobot_list.setItemWidget(item, card)
    
    def _on_card_clicked(self, config_name: str):
        if config_name in self._selected_nanobots:
            self._selected_nanobots.remove(config_name)
            self._nanobot_cards[config_name].set_selected(False)
            self._remove_tag(config_name)
        else:
            self._selected_nanobots.add(config_name)
            self._nanobot_cards[config_name].set_selected(True)
            self._add_tag(config_name)
        
        self._update_tags_label()
        self.nanobot_selected.emit(list(self._selected_nanobots))
    
    def _add_tag(self, name: str):
        tag = SelectedNanobotTag(name)
        tag.removed.connect(self._on_tag_removed)
        self._tag_widgets[name] = tag
        
        layout = self.tags_container.layout()
        layout.insertWidget(layout.count() - 1, tag)
    
    def _remove_tag(self, name: str):
        if name in self._tag_widgets:
            tag = self._tag_widgets.pop(name)
            tag.deleteLater()
    
    def _on_tag_removed(self, name: str):
        if name in self._selected_nanobots:
            self._selected_nanobots.remove(name)
            if name in self._nanobot_cards:
                self._nanobot_cards[name].set_selected(False)
            self._remove_tag(name)
            self._update_tags_label()
            self.nanobot_selected.emit(list(self._selected_nanobots))
    
    def _update_tags_label(self):
        if not self._selected_nanobots:
            self.tags_label.show()
        else:
            self.tags_label.hide()
    
    def _on_group_chat_toggled(self, state):
        self._group_chat_enabled = state == Qt.CheckState.Checked.value
    
    def is_group_chat_enabled(self) -> bool:
        return self._group_chat_enabled
    
    def get_group_chat_interval(self) -> int:
        return self.group_chat_interval_spin.value() * 1000
    
    def _refresh_nanobots(self):
        self._load_nanobots()
        self._refresh_nanobot_status()
    
    def _refresh_nanobot_status(self):
        if self._wsl_manager:
            self._wsl_manager.list_distros()
        
        for config_name, card in self._nanobot_cards.items():
            wsl_status = "stopped"
            if card.config and self._wsl_manager:
                distro = self._wsl_manager.get_distro(card.config.distro_name)
                if distro:
                    wsl_status = "running" if distro.is_running else "stopped"
            
            card.set_wsl_status(wsl_status)
            
            nanobot_status = "stopped"
            if wsl_status == "running" and self._nanobot_controller:
                status = self._nanobot_controller.get_status(config_name)
                if status:
                    nanobot_status = status.value
                
                if nanobot_status != "running" and card.config:
                    is_connected = self._nanobot_controller.check_gateway_connectivity(
                        card.config.distro_name,
                        card.config.gateway_port
                    )
                    if is_connected:
                        nanobot_status = "running"
            
            card.set_nanobot_status(nanobot_status)
    
    def _refresh_nanobot_status_async(self):
        """异步刷新 Nanobot 状态，避免阻塞主线程"""
        if not self._wsl_manager:
            return
        
        def refresh_operation():
            results = {}
            if self._wsl_manager:
                self._wsl_manager.list_distros()
            
            for config_name, card in self._nanobot_cards.items():
                wsl_status = "stopped"
                if card.config and self._wsl_manager:
                    distro = self._wsl_manager.get_distro(card.config.distro_name)
                    if distro:
                        wsl_status = "running" if distro.is_running else "stopped"
                
                nanobot_status = "stopped"
                if wsl_status == "running" and self._nanobot_controller:
                    status = self._nanobot_controller.get_status(config_name)
                    if status:
                        nanobot_status = status.value
                    
                    if nanobot_status != "running" and card.config:
                        is_connected = self._nanobot_controller.check_gateway_connectivity(
                            card.config.distro_name,
                            card.config.gateway_port
                        )
                        if is_connected:
                            nanobot_status = "running"
                
                results[config_name] = {
                    "wsl_status": wsl_status,
                    "nanobot_status": nanobot_status
                }
            
            return results
        
        def on_result(results):
            if isinstance(results, AsyncResult) and not results.success:
                logger.error(f"刷新 Nanobot 状态失败: {results.error}")
                return
            
            if results:
                for config_name, status in results.items():
                    if config_name in self._nanobot_cards:
                        self._nanobot_cards[config_name].set_wsl_status(status["wsl_status"])
                        self._nanobot_cards[config_name].set_nanobot_status(status["nanobot_status"])
        
        op = AsyncOperation(self)
        op.execute(refresh_operation, on_result)
    
    def on_wsl_status_changed(self, distros: List[Dict], running_count: int, stopped_count: int):
        self._update_cards_wsl_status(distros)
    
    def on_wsl_distro_started(self, distro_name: str):
        self._refresh_nanobot_status()
    
    def on_wsl_distro_stopped(self, distro_name: str):
        self._refresh_nanobot_status()
    
    def on_wsl_distro_removed(self, distro_name: str):
        self._refresh_nanobots()
    
    def on_wsl_distro_imported(self, distro_name: str):
        self._refresh_nanobots()
    
    def on_wsl_list_changed(self, distros: List[Dict], added: List[str], removed: List[str]):
        self._refresh_nanobots()
    
    def _update_cards_wsl_status(self, distros: List[Dict]):
        distro_status = {d["name"]: d.get("is_running", False) for d in distros}
        for config_name, card in self._nanobot_cards.items():
            if card.config:
                distro_name = card.config.distro_name
                is_running = distro_status.get(distro_name, False)
                card.set_wsl_status("running" if is_running else "stopped")
                
                nanobot_status = "stopped"
                if is_running and self._nanobot_controller:
                    status = self._nanobot_controller.get_status(config_name)
                    if status:
                        nanobot_status = status.value
                    
                    if nanobot_status != "running" and card.config:
                        is_connected = self._nanobot_controller.check_gateway_connectivity(
                            card.config.distro_name,
                            card.config.gateway_port
                        )
                        if is_connected:
                            nanobot_status = "running"
                
                card.set_nanobot_status(nanobot_status)
    
    def _select_all(self):
        for name, card in self._nanobot_cards.items():
            if name not in self._selected_nanobots:
                self._selected_nanobots.add(name)
                card.set_selected(True)
                self._add_tag(name)
        self._update_tags_label()
        self.nanobot_selected.emit(list(self._selected_nanobots))
    
    def _deselect_all(self):
        for name, card in self._nanobot_cards.items():
            card.set_selected(False)
        self._selected_nanobots.clear()
        
        for name in list(self._tag_widgets.keys()):
            self._remove_tag(name)
        
        self._update_tags_label()
        self.nanobot_selected.emit(list(self._selected_nanobots))
    
    def _on_nanobot_connect_requested(self, config_name: str):
        logger.info(f"[ChatPanel] 收到连接请求: {config_name}")
        
        if config_name in self._nanobot_cards:
            self._nanobot_cards[config_name].set_connection_status("connecting")
        
        self.nanobot_connect_requested.emit(config_name)
    
    def _on_nanobot_disconnect_requested(self, config_name: str):
        logger.info(f"[ChatPanel] 收到断开请求: {config_name}")
        
        self.nanobot_disconnect_requested.emit(config_name)
    
    def _on_connect_all_clicked(self):
        connected_bots = [bot for bot, status in self._connection_status.items() if status]
        
        if connected_bots:
            logger.info("[ChatPanel] 断开全部连接")
            for bot in connected_bots:
                self._on_nanobot_disconnect_requested(bot)
        else:
            if self._selected_nanobots:
                logger.info(f"[ChatPanel] 连接全部选中的: {list(self._selected_nanobots)}")
                for bot in self._selected_nanobots:
                    if bot not in self._connection_status or not self._connection_status[bot]:
                        self._on_nanobot_connect_requested(bot)
            else:
                QMessageBox.warning(self, tr("chat.msg.select_bot_first", "请先选择要连接的 Nanobot"))
    
    def _on_send_message(self):
        text = self.message_input.toPlainText().strip()
        if not text:
            return
        
        if not self._selected_nanobots:
            QMessageBox.warning(self, tr("chat.msg.select_at_least_one", "请至少选择一个 Nanobot"))
            return
        
        self.message_input.clear()
        self.add_message("user", text)
        self.message_sent.emit(text, list(self._selected_nanobots))
    
    def add_message(self, role: str, content: str, nanobot_name: Optional[str] = None):
        message = ChatMessage(role, content, nanobot_name)
        self._messages.append(message)
        self._append_message(message)
    
    def _append_message(self, message: ChatMessage):
        cursor = self.chat_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        if message.role == "user":
            role_text = tr("chat.role.you", "你")
            role_color = QColor("#58a6ff")
            bg_color = QColor("#1f3a5f")
        elif message.role == "assistant":
            role_text = message.nanobot_name or tr("chat.role.ai", "AI")
            if message.nanobot_name:
                if message.nanobot_name not in self._bot_color_map:
                    color_idx = len(self._bot_color_map) % len(self._BOT_COLORS)
                    self._bot_color_map[message.nanobot_name] = self._BOT_COLORS[color_idx]
                role_color = QColor(self._bot_color_map[message.nanobot_name][0])
                bg_color = QColor(self._bot_color_map[message.nanobot_name][1])
            else:
                role_color = QColor("#3fb950")
                bg_color = QColor("#1a3a2f")
        else:
            role_text = message.role
            role_color = QColor("#8b949e")
            bg_color = QColor("#2d333b")
        
        format_text = QTextCharFormat()
        format_text.setBackground(bg_color)
        format_text.setForeground(role_color)
        format_text.setFontWeight(QFont.Weight.Bold)
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
    
    def _clear_clicked(self):
        self._messages.clear()
        self.chat_text.clear()
        self.clear_clicked.emit()
    
    def clear_messages(self):
        self._messages.clear()
        self.chat_text.clear()
    
    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()
        
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                self._on_send_message()
                return
        
        super().keyPressEvent(event)
    
    def _on_send_clicked(self):
        if not self._selected_nanobots:
            QMessageBox.warning(self, tr("chat.msg.select_at_least_one", "请至少选择一个 Nanobot"))
            return
        
        connected_bots = [bot for bot, status in self._connection_status.items() if status]
        
        if connected_bots:
            logger.info(f"[ChatPanel] 发出 disconnect_clicked 信号，断开: {connected_bots}")
            for bot in connected_bots:
                self.disconnect_clicked.emit(bot)
        else:
            logger.info(f"[ChatPanel] 发出 connect_clicked 信号，连接: {list(self._selected_nanobots)}")
            self.connect_clicked.emit("")
    
    def set_connecting(self):
        logger.info("[ChatPanel] 设置状态: 正在连接...")
        self._connect_btn.setEnabled(False)
        self._connect_btn.setText(tr("chat.btn.connecting", "连接中..."))
    
    def set_connection_status(self, bot_name: str, is_connected: bool, info: Optional[str] = None):
        logger.info(f"[ChatPanel] 设置连接状态: {bot_name} -> {is_connected}, info={info}")
        
        self._connection_status[bot_name] = is_connected
        
        if bot_name in self._nanobot_cards:
            if is_connected:
                self._nanobot_cards[bot_name].set_connection_status("connected")
                self._connected_bot_info[bot_name] = {
                    "address": info or "",
                    "connected_at": datetime.now(),
                    "message_count": 0
                }
            else:
                self._nanobot_cards[bot_name].set_connection_status("disconnected")
                if bot_name in self._connected_bot_info:
                    del self._connected_bot_info[bot_name]
        
        self._update_connection_status_display()
        
        connected_bots = [bot for bot, status in self._connection_status.items() if status]
        if connected_bots:
            self._connect_btn.setText(tr("chat.disconnect_all", "断开全部"))
        else:
            self._connect_btn.setText(tr("chat.connect_all", "连接全部"))
        self._connect_btn.setEnabled(True)
    
    def _update_connection_status_display(self):
        for i in reversed(range(self._connection_status_layout.count() - 1)):
            widget = self._connection_status_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        for bot_name, is_connected in self._connection_status.items():
            if is_connected and bot_name in self._connected_bot_info:
                info = self._connected_bot_info[bot_name]
                tag = ConnectedBotTag(bot_name, info.get("address", ""))
                tag.disconnect_clicked.connect(self._on_nanobot_disconnect_requested)
                self._connection_status_layout.insertWidget(self._connection_status_layout.count() - 1, tag)
    
    def clear_connection_status(self):
        self._connection_status.clear()
        self._update_connection_status_display()
        self._connect_btn.setText(tr("chat.connect_all", "连接全部"))
        self._connect_btn.setEnabled(True)
    
    def show_error(self, message: str):
        logger.error(f"[ChatPanel] 显示错误: {message}")
        QMessageBox.warning(self, tr("error.title", "错误"), message)
        self.clear_connection_status()
