# -*- coding: utf-8 -*-
import os
import tempfile
from typing import Optional, List, Dict
from datetime import datetime

from loguru import logger

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QGroupBox, QGridLayout, QLineEdit, QTextEdit,
    QComboBox, QScrollArea, QMessageBox, QApplication, QSpinBox,
    QSizePolicy, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPixmap

from ..mixins import WSLStateAwareMixin
from ..dialogs import WaitingDialog
from ...services.windows_bridge import WindowsAutomation
from ...utils.i18n import tr


class WindowsBridgePanel(QWidget, WSLStateAwareMixin):
    start_bridge = pyqtSignal()
    stop_bridge = pyqtSignal()
    port_changed = pyqtSignal(int)
    restart_wsl = pyqtSignal(str)
    refresh_distros = pyqtSignal()
    start_wsl_distro = pyqtSignal(str)
    stop_wsl_distro = pyqtSignal(str)
    refresh_wsl_status = pyqtSignal()
    
    def __init__(self, bridge_manager=None, windows_bridge=None, wsl_manager=None, parent=None):
        super().__init__(parent)
        WSLStateAwareMixin._init_wsl_state_aware(self)
        self._bridge_manager = bridge_manager
        self._windows_bridge = windows_bridge
        self._wsl_manager = wsl_manager
        self._bridge_status = False
        self._last_activity = None
        self._bridge_port = 9527
        
        self._init_ui()
    
    def set_bridge_manager(self, bridge_manager):
        self._bridge_manager = bridge_manager
    
    def set_windows_bridge(self, windows_bridge):
        self._windows_bridge = windows_bridge
    
    def set_wsl_manager(self, wsl_manager):
        self._wsl_manager = wsl_manager

    def set_bridge_port(self, port: int):
        self._bridge_port = port
        self._port_spin.setValue(port)
    
    def _on_apply_port(self):
        new_port = self._port_spin.value()
        if new_port != self._bridge_port:
            reply = QMessageBox.question(
                self,
                tr("bridge.msg.confirm_port_change", "确认修改端口"),
                tr("bridge.msg.port_change_detail", "端口将从 {old} 更改为 {new}\n\n这将：\n1. 保存配置\n2. 同步配置到所有 WSL\n3. 重启 IPC Server\n\n是否继续？").format(old=self._bridge_port, new=new_port),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._show_port_change_progress(new_port)
        else:
            self._add_log(tr("bridge.msg.port_not_changed", "端口未变更"))
    
    def _show_port_change_progress(self, new_port: int):
        dialog = WaitingDialog(tr("bridge.msg.change_port_title", "修改端口"), tr("bridge.msg.updating_port", "正在更新端口配置..."), self)
        dialog.show()
        
        old_port = self._bridge_port
        self._bridge_port = new_port
        
        self._bridge_status_label.setText(f"Windows Bridge: ● {tr('bridge.status_running_dot', '运行中')} (端口: {new_port})")
        
        self.port_changed.emit(new_port)
        
        dialog.close_with_result(True, tr("bridge.msg.port_changed", "端口已更改为 {port}").format(port=new_port))
        
        self._add_log(tr("bridge.msg.port_changed_log", "✓ 监听端口已更改为: {port}").format(port=new_port))
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        header_layout = QHBoxLayout()
        title = QLabel(tr("bridge.title", "桥接控制"))
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("color: #f0f6fc;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self._status_label = QLabel(tr("bridge.status_not_running", "状态: 未运行"))
        self._status_label.setStyleSheet("color: #8b949e; font-size: 14px;")
        header_layout.addWidget(self._status_label)
        
        self._toggle_btn = QPushButton(tr("bridge.start", "启动桥接"))
        self._toggle_btn.setObjectName("primaryButton")
        self._toggle_btn.setFixedWidth(100)
        self._toggle_btn.clicked.connect(self._on_toggle_bridge)
        header_layout.addWidget(self._toggle_btn)
        
        main_layout.addLayout(header_layout)
        
        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363d;
                border-radius: 8px;
                background-color: #161b22;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #21262d;
                color: #8b949e;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background-color: #161b22;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-bottom: none;
            }
            QTabBar::tab:hover:!selected {
                background-color: #30363d;
            }
        """)
        
        self._tab_widget.addTab(self._create_basic_tab(), tr("bridge.tab.basic", "基础设置"))
        self._tab_widget.addTab(self._create_advanced_tab(), tr("bridge.tab.advanced", "高级控制"))
        
        main_layout.addWidget(self._tab_widget)
    
    def _create_basic_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(12)
        
        layout.addWidget(self._create_wsl_connection_group(), 1)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(12)
        
        left_panel = QVBoxLayout()
        left_panel.setSpacing(12)
        left_panel.addWidget(self._create_port_settings_group())
        left_panel.addWidget(self._create_quick_actions_group())
        left_panel.addStretch()
        
        bottom_layout.addLayout(left_panel, 1)
        bottom_layout.addWidget(self._create_log_group(), 3)
        
        layout.addLayout(bottom_layout)
        
        return tab
    
    def _create_advanced_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(16)
        
        grid = QGridLayout()
        grid.setSpacing(16)
        
        grid.addWidget(self._create_mouse_control_group(), 0, 0)
        grid.addWidget(self._create_keyboard_control_group(), 0, 1)
        grid.addWidget(self._create_screenshot_group(), 1, 0)
        grid.addWidget(self._create_window_management_group(), 1, 1)
        
        layout.addLayout(grid)
        layout.addStretch()
        
        return tab
    
    def _create_wsl_connection_group(self) -> QGroupBox:
        group = QGroupBox(tr("bridge.wsl_status", "📡 WSL 连通状态"))
        group.setStyleSheet("""
            QGroupBox {
                color: #f0f6fc;
                font-weight: 600;
                font-size: 14px;
                border: 1px solid #30363d;
                border-radius: 12px;
                margin-top: 12px;
                padding: 16px;
                padding-top: 24px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                top: 4px;
                padding: 0 8px;
                background-color: #161b22;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        refresh_btn = QPushButton(tr("bridge.btn.refresh", "刷新"))
        refresh_btn.setObjectName("smallButton")
        refresh_btn.setFixedWidth(50)
        refresh_btn.clicked.connect(self._on_refresh_wsl_status)
        header_layout.addWidget(refresh_btn)
        layout.addLayout(header_layout)
        
        self._wsl_status_table = QTableWidget()
        self._wsl_status_table.setColumnCount(3)
        self._wsl_status_table.setHorizontalHeaderLabels([
            tr("bridge.table.distro_name", "分发名称"),
            tr("bridge.table.wsl_status", "WSL状态"),
            tr("bridge.table.bridge_connection", "Bridge连接")
        ])
        self._wsl_status_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._wsl_status_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._wsl_status_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._wsl_status_table.setColumnWidth(1, 80)
        self._wsl_status_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._wsl_status_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._wsl_status_table.verticalHeader().setVisible(False)
        self._wsl_status_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._wsl_status_table.setStyleSheet("""
            QTableWidget {
                background-color: #0d1117;
                border: 1px solid #21262d;
                border-radius: 8px;
                gridline-color: #21262d;
            }
            QTableWidget::item {
                padding: 8px 6px;
                border: none;
                background-color: transparent;
            }
            QHeaderView::section {
                background-color: #21262d;
                color: #8b949e;
                padding: 8px 6px;
                border: none;
                border-bottom: 1px solid #30363d;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        layout.addWidget(self._wsl_status_table)
        
        status_layout = QHBoxLayout()
        self._bridge_status_label = QLabel(f"Windows Bridge: ○ {tr('bridge.status_not_running', '未运行')}")
        self._bridge_status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        status_layout.addWidget(self._bridge_status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        return group
    
    def _create_port_settings_group(self) -> QGroupBox:
        group = QGroupBox(tr("bridge.port_settings", "⚙ 端口设置"))
        group.setStyleSheet("""
            QGroupBox {
                color: #f0f6fc;
                font-weight: 600;
                font-size: 14px;
                border: 1px solid #30363d;
                border-radius: 12px;
                margin-top: 12px;
                padding: 16px;
                padding-top: 24px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                top: 4px;
                padding: 0 8px;
                background-color: #161b22;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel(tr("bridge.listen_port", "监听端口:")))
        
        self._port_spin = QSpinBox()
        self._port_spin.setRange(1024, 65535)
        self._port_spin.setValue(self._bridge_port)
        self._port_spin.setFixedWidth(80)
        self._port_spin.setStyleSheet("""
            QSpinBox {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 4px 8px;
                color: #c9d1d9;
            }
            QSpinBox:focus {
                border-color: #58a6ff;
            }
        """)
        port_layout.addWidget(self._port_spin)
        
        self._apply_port_btn = QPushButton(tr("bridge.btn.apply", "应用"))
        self._apply_port_btn.setObjectName("smallButton")
        self._apply_port_btn.setFixedWidth(50)
        self._apply_port_btn.clicked.connect(self._on_apply_port)
        port_layout.addWidget(self._apply_port_btn)
        port_layout.addStretch()
        
        layout.addLayout(port_layout)
        layout.addStretch()
        
        return group
    
    def _on_refresh_wsl_status(self):
        self.refresh_wsl_status.emit()
    
    def _create_quick_actions_group(self) -> QGroupBox:
        group = QGroupBox(tr("bridge.quick_actions", "⚡ 快速操作"))
        group.setStyleSheet("""
            QGroupBox {
                color: #f0f6fc;
                font-weight: 600;
                font-size: 14px;
                border: 1px solid #30363d;
                border-radius: 12px;
                margin-top: 12px;
                padding: 16px;
                padding-top: 24px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                top: 4px;
                padding: 0 8px;
                background-color: #161b22;
            }
        """)
        
        layout = QGridLayout(group)
        layout.setSpacing(8)
        
        actions = [
            (tr("bridge.quick.screenshot", "📸 截图"), self._on_quick_screenshot),
            (tr("bridge.quick.clipboard", "📋 剪贴板"), self._on_quick_clipboard),
            (tr("bridge.quick.mouse_position", "🖱 鼠标位置"), self._on_get_mouse_position),
            (tr("bridge.quick.window_list", "🪟 窗口列表"), self._on_list_windows),
        ]
        
        for i, (text, callback) in enumerate(actions):
            btn = QPushButton(text)
            btn.setMinimumHeight(36)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #21262d;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    color: #c9d1d9;
                    font-size: 13px;
                    padding: 8px 12px;
                }
                QPushButton:hover {
                    background-color: #30363d;
                    border-color: #8b949e;
                }
                QPushButton:pressed {
                    background-color: #161b22;
                }
            """)
            btn.clicked.connect(callback)
            layout.addWidget(btn, i // 2, i % 2)
        
        return group
    
    def _create_log_group(self) -> QGroupBox:
        group = QGroupBox(tr("bridge.operation_log", "📋 操作日志"))
        group.setStyleSheet("""
            QGroupBox {
                color: #f0f6fc;
                font-weight: 600;
                font-size: 14px;
                border: 1px solid #30363d;
                border-radius: 12px;
                margin-top: 12px;
                padding: 16px;
                padding-top: 24px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                top: 4px;
                padding: 0 8px;
                background-color: #161b22;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        clear_btn = QPushButton(tr("bridge.btn.clear", "清空"))
        clear_btn.setObjectName("smallButton")
        clear_btn.setFixedWidth(50)
        clear_btn.clicked.connect(self._clear_log)
        header_layout.addWidget(clear_btn)
        layout.addLayout(header_layout)
        
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setFont(QFont("Consolas", 9))
        self._log_text.setStyleSheet("""
            QTextEdit {
                background-color: #0d1117;
                color: #c9d1d9;
                border: 1px solid #21262d;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self._log_text.setMinimumHeight(100)
        self._log_text.setMaximumHeight(150)
        layout.addWidget(self._log_text)
        
        return group
    
    def _create_mouse_control_group(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #0d1117;
                border: 1px solid #21262d;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)
        
        title = QLabel(tr("bridge.mouse_control", "🖱 鼠标控制"))
        title.setStyleSheet("color: #f0f6fc; font-weight: 600; font-size: 14px;")
        layout.addWidget(title)
        
        move_layout = QHBoxLayout()
        move_layout.addWidget(QLabel(tr("bridge.label.move", "移动:")))
        self._mouse_x = QLineEdit()
        self._mouse_x.setPlaceholderText(tr("bridge.placeholder.x", "X"))
        self._mouse_x.setFixedWidth(60)
        self._mouse_x.setStyleSheet(self._get_input_style())
        move_layout.addWidget(self._mouse_x)
        move_layout.addWidget(QLabel(","))
        self._mouse_y = QLineEdit()
        self._mouse_y.setPlaceholderText(tr("bridge.placeholder.y", "Y"))
        self._mouse_y.setFixedWidth(60)
        self._mouse_y.setStyleSheet(self._get_input_style())
        move_layout.addWidget(self._mouse_y)
        move_btn = QPushButton(tr("bridge.btn.move", "移动"))
        move_btn.setObjectName("smallButton")
        move_btn.clicked.connect(self._on_mouse_move)
        move_layout.addWidget(move_btn)
        layout.addLayout(move_layout)
        
        click_layout = QHBoxLayout()
        click_layout.addWidget(QLabel(tr("bridge.label.click", "点击:")))
        self._click_type = QComboBox()
        self._click_type.addItems([
            tr("bridge.left_click", "左键"),
            tr("bridge.right_click", "右键"),
            tr("bridge.double_click", "双击")
        ])
        self._click_type.setFixedWidth(80)
        self._click_type.setStyleSheet(self._get_combo_style())
        click_layout.addWidget(self._click_type)
        click_btn = QPushButton(tr("bridge.btn.execute", "执行"))
        click_btn.setObjectName("smallButton")
        click_btn.clicked.connect(self._on_mouse_click)
        click_layout.addWidget(click_btn)
        layout.addLayout(click_layout)
        
        return frame
    
    def _create_keyboard_control_group(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #0d1117;
                border: 1px solid #21262d;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)
        
        title = QLabel(tr("bridge.keyboard_control", "⌨ 键盘控制"))
        title.setStyleSheet("color: #f0f6fc; font-weight: 600; font-size: 14px;")
        layout.addWidget(title)
        
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel(tr("bridge.label.text", "文本:")))
        self._keyboard_text = QLineEdit()
        self._keyboard_text.setPlaceholderText(tr("bridge.placeholder.text", "输入文本"))
        self._keyboard_text.setStyleSheet(self._get_input_style())
        type_layout.addWidget(self._keyboard_text)
        type_btn = QPushButton(tr("bridge.btn.type", "输入"))
        type_btn.setObjectName("smallButton")
        type_btn.clicked.connect(self._on_keyboard_type)
        type_layout.addWidget(type_btn)
        layout.addLayout(type_layout)
        
        press_layout = QHBoxLayout()
        press_layout.addWidget(QLabel(tr("bridge.label.key", "按键:")))
        self._keyboard_key = QLineEdit()
        self._keyboard_key.setPlaceholderText(tr("bridge.placeholder.key", "如: enter"))
        self._keyboard_key.setFixedWidth(80)
        self._keyboard_key.setStyleSheet(self._get_input_style())
        press_layout.addWidget(self._keyboard_key)
        press_btn = QPushButton(tr("bridge.btn.press", "按下"))
        press_btn.setObjectName("smallButton")
        press_btn.clicked.connect(self._on_keyboard_press)
        press_layout.addWidget(press_btn)
        layout.addLayout(press_layout)
        
        return frame
    
    def _create_screenshot_group(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #0d1117;
                border: 1px solid #21262d;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)
        
        title = QLabel(tr("bridge.screen_capture", "📸 屏幕截图"))
        title.setStyleSheet("color: #f0f6fc; font-weight: 600; font-size: 14px;")
        layout.addWidget(title)
        
        screenshot_btn = QPushButton(tr("bridge.capture_fullscreen", "截取全屏"))
        screenshot_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                border: none;
                border-radius: 6px;
                color: white;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
        """)
        screenshot_btn.clicked.connect(self._on_screenshot)
        layout.addWidget(screenshot_btn)
        
        self._screenshot_info = QLabel(tr("bridge.msg.click_to_start", "点击按钮开始截图"))
        self._screenshot_info.setStyleSheet("color: #8b949e; font-size: 12px;")
        self._screenshot_info.setWordWrap(True)
        layout.addWidget(self._screenshot_info)
        
        return frame
    
    def _create_window_management_group(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #0d1117;
                border: 1px solid #21262d;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)
        
        title = QLabel(tr("bridge.window_management", "🪟 窗口管理"))
        title.setStyleSheet("color: #f0f6fc; font-weight: 600; font-size: 14px;")
        layout.addWidget(title)
        
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel(tr("bridge.label.title", "标题:")))
        self._window_title = QLineEdit()
        self._window_title.setPlaceholderText(tr("bridge.placeholder.title", "输入窗口标题"))
        self._window_title.setStyleSheet(self._get_input_style())
        find_layout.addWidget(self._window_title)
        find_btn = QPushButton(tr("bridge.btn.find", "查找"))
        find_btn.setObjectName("smallButton")
        find_btn.clicked.connect(self._on_find_window)
        find_layout.addWidget(find_btn)
        layout.addLayout(find_layout)
        
        list_btn = QPushButton(tr("bridge.btn.list_windows", "列出所有窗口"))
        list_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                color: #c9d1d9;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #30363d;
            }
        """)
        list_btn.clicked.connect(self._on_list_windows)
        layout.addWidget(list_btn)
        
        return frame
    
    def _get_input_style(self) -> str:
        return """
            QLineEdit {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
                color: #c9d1d9;
            }
            QLineEdit:focus {
                border-color: #58a6ff;
            }
        """
    
    def _get_combo_style(self) -> str:
        return """
            QComboBox {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
                color: #c9d1d9;
            }
            QComboBox:focus {
                border-color: #58a6ff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #8b949e;
                margin-right: 8px;
            }
        """
    
    def _clear_log(self):
        self._log_text.clear()
    
    def _on_find_window_quick(self):
        if not self._check_bridge_available():
            return
        
        automation = WindowsAutomation()
        windows = automation.list_windows()
        
        if windows:
            self._add_log(tr("bridge.msg.windows_found", "✓ 找到 {count} 个窗口:").format(count=len(windows)))
            for i, w in enumerate(windows[:10]):
                if w.title:
                    self._add_log(f"  {i+1}. {w.title}")
            if len(windows) > 10:
                self._add_log(tr("bridge.msg.more_windows", "  ... 还有 {count} 个窗口").format(count=len(windows) - 10))
            self._update_last_activity()
        else:
            self._add_log(tr("bridge.msg.no_windows", "✗ 未找到任何窗口"))
    
    def _on_toggle_bridge(self):
        if self._bridge_status:
            self.stop_bridge.emit()
            self.set_bridge_status(False)
        else:
            self.start_bridge.emit()
            self.set_bridge_status(True)
    
    def _check_bridge_available(self) -> bool:
        if not self._windows_bridge or not self._windows_bridge.is_running:
            QMessageBox.warning(self, tr("bridge.msg.hint", "提示"), tr("bridge.msg.bridge_not_running", "桥接服务未启动，请先启动桥接服务"))
            return False
        return True
    
    def _confirm_action(self, action_description: str) -> bool:
        reply = QMessageBox.question(
            self,
            tr("bridge.msg.confirm_action", "确认操作"),
            tr("bridge.msg.action_detail", "即将执行: {action}\n\n是否继续?").format(action=action_description),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
    
    def _on_mouse_move(self):
        if not self._check_bridge_available():
            return
        try:
            x = int(self._mouse_x.text())
            y = int(self._mouse_y.text())
            
            automation = WindowsAutomation()
            success = automation.mouse_move(x, y)
            
            if success:
                self._add_log(tr("bridge.msg.mouse_moved", "✓ 移动鼠标到: ({x}, {y})").format(x=x, y=y))
                self._update_last_activity()
            else:
                self._add_log(tr("bridge.msg.mouse_move_failed", "✗ 移动鼠标失败"))
        except ValueError:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("bridge.msg.invalid_coords", "请输入有效的坐标"))
    
    def _on_mouse_click(self):
        if not self._check_bridge_available():
            return
        click_type = self._click_type.currentText()
        
        if not self._confirm_action(tr("bridge.msg.mouse_click_action", "鼠标{type}点击").format(type=click_type)):
            return
        
        automation = WindowsAutomation()
        
        pos = automation.get_mouse_position()
        if click_type == tr("bridge.left_click", "左键"):
            success = automation.mouse_click(pos[0], pos[1], "left", 1)
        elif click_type == tr("bridge.right_click", "右键"):
            success = automation.mouse_click(pos[0], pos[1], "right", 1)
        else:
            success = automation.mouse_click(pos[0], pos[1], "left", 2)
        
        if success:
            self._add_log(tr("bridge.msg.mouse_clicked", "✓ 执行{type}点击 @ ({x}, {y})").format(type=click_type, x=pos[0], y=pos[1]))
            self._update_last_activity()
        else:
            self._add_log(tr("bridge.msg.mouse_click_failed", "✗ 执行{type}点击失败").format(type=click_type))
    
    def _on_keyboard_type(self):
        if not self._check_bridge_available():
            return
        text = self._keyboard_text.text()
        if not text:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("bridge.msg.enter_text", "请输入要键入的文本"))
            return
        
        if not self._confirm_action(tr("bridge.msg.type_text_action", "输入文本: {text}").format(text=text)):
            return
        
        automation = WindowsAutomation()
        success = automation.keyboard_type(text)
        
        if success:
            self._add_log(tr("bridge.msg.text_typed", "✓ 输入文本: {text}").format(text=text))
            self._update_last_activity()
        else:
            self._add_log(tr("bridge.msg.text_type_failed", "✗ 输入文本失败"))
    
    def _on_keyboard_press(self):
        if not self._check_bridge_available():
            return
        key = self._keyboard_key.text()
        if not key:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("bridge.msg.enter_key", "请输入要按下的按键"))
            return
        
        if not self._confirm_action(tr("bridge.msg.press_key_action", "按下按键: {key}").format(key=key)):
            return
        
        automation = WindowsAutomation()
        success = automation.keyboard_press(key)
        
        if success:
            self._add_log(tr("bridge.msg.key_pressed", "✓ 按下按键: {key}").format(key=key))
            self._update_last_activity()
        else:
            self._add_log(tr("bridge.msg.key_press_failed", "✗ 按下按键失败"))
    
    def _on_screenshot(self):
        if not self._check_bridge_available():
            return
        
        automation = WindowsAutomation()
        data = automation.screenshot()
        
        if data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            temp_dir = tempfile.gettempdir()
            filepath = os.path.join(temp_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(data)
            
            automation.set_clipboard(tr("bridge.msg.screenshot_clipboard", "[截图已保存: {path}]").format(path=filepath))
            self._screenshot_info.setText(tr("bridge.msg.screenshot_saved", "截图已保存: {path}").format(path=filepath))
            self._add_log(tr("bridge.msg.screenshot_saved_log", "✓ 截图已保存: {path}").format(path=filepath))
            self._update_last_activity()
        else:
            self._screenshot_info.setText(tr("bridge.msg.screenshot_failed", "截图失败"))
            self._add_log(tr("bridge.msg.screenshot_failed_log", "✗ 截图失败"))
    
    def _on_find_window(self):
        if not self._check_bridge_available():
            return
        title = self._window_title.text()
        if not title:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("bridge.msg.enter_title", "请输入窗口标题"))
            return
        
        automation = WindowsAutomation()
        window = automation.find_window(title)
        
        if window:
            self._add_log(tr("bridge.msg.window_found", "✓ 找到窗口: {title}").format(title=window.title))
            self._add_log(tr("bridge.msg.window_position", "  位置: {rect}").format(rect=window.rect))
            self._update_last_activity()
        else:
            self._add_log(tr("bridge.msg.window_not_found", "✗ 未找到窗口: {title}").format(title=title))
    
    def _on_list_windows(self):
        if not self._check_bridge_available():
            return
        
        automation = WindowsAutomation()
        windows = automation.list_windows()
        
        if windows:
            self._add_log(tr("bridge.msg.windows_found", "✓ 找到 {count} 个窗口:").format(count=len(windows)))
            for i, w in enumerate(windows[:10]):
                if w.title:
                    self._add_log(f"  {i+1}. {w.title}")
            if len(windows) > 10:
                self._add_log(tr("bridge.msg.more_windows", "  ... 还有 {count} 个窗口").format(count=len(windows) - 10))
            self._update_last_activity()
        else:
            self._add_log(tr("bridge.msg.no_windows", "✗ 未找到任何窗口"))
    
    def _on_quick_screenshot(self):
        self._on_screenshot()
    
    def _on_quick_clipboard(self):
        if not self._check_bridge_available():
            return
        
        automation = WindowsAutomation()
        text = automation.get_clipboard()
        
        if text:
            self._add_log(tr("bridge.msg.clipboard_content", "✓ 剪贴板内容: {content}").format(content=text[:100] + ('...' if len(text) > 100 else '')))
            self._update_last_activity()
        else:
            self._add_log(tr("bridge.msg.clipboard_empty", "剪贴板为空"))
    
    def _on_get_mouse_position(self):
        if not self._check_bridge_available():
            return
        
        automation = WindowsAutomation()
        pos = automation.get_mouse_position()
        
        self._add_log(tr("bridge.msg.mouse_position", "✓ 鼠标位置: ({x}, {y})").format(x=pos[0], y=pos[1]))
        self._mouse_x.setText(str(pos[0]))
        self._mouse_y.setText(str(pos[1]))
        self._update_last_activity()
    
    def set_bridge_status(self, running: bool):
        self._bridge_status = running
        if running:
            self._status_label.setText(tr("bridge.status_running", "状态: 运行中"))
            self._status_label.setStyleSheet("color: #3fb950; font-size: 14px;")
            self._toggle_btn.setText(tr("bridge.stop", "停止桥接"))
            self._bridge_status_label.setText(f"Windows Bridge: ● {tr('bridge.status_running_dot', '运行中')} (端口: {self._bridge_port})")
            self._bridge_status_label.setStyleSheet("color: #3fb950; font-size: 12px;")
            self._add_log(tr("bridge.service_started", "✓ 桥接服务已启动"))
        else:
            self._status_label.setText(tr("bridge.status_not_running", "状态: 未运行"))
            self._status_label.setStyleSheet("color: #8b949e; font-size: 14px;")
            self._toggle_btn.setText(tr("bridge.start", "启动桥接"))
            self._bridge_status_label.setText(f"Windows Bridge: ○ {tr('bridge.status_not_running', '未运行')}")
            self._bridge_status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
            self._add_log(tr("bridge.service_stopped", "桥接服务已停止"))

    def update_clients_info(self, clients_info: list):
        pass

    def update_wsl_connection_status(self, distros: list, connected_clients: list):
        """
        更新 WSL 连通状态表格
        
        Args:
            distros: 所有 WSL 分发列表 (WSLDistro 对象列表)
            connected_clients: 已连接的客户端信息列表
        """
        connected_distro_names = set()
        
        for client in connected_clients:
            distro_name = client.get("distro_name")
            if distro_name:
                connected_distro_names.add(distro_name)
        
        self._wsl_status_table.setRowCount(len(distros))
        
        for row, distro in enumerate(distros):
            name_item = QTableWidgetItem(distro.name)
            name_item.setForeground(QColor("#c9d1d9"))
            
            wsl_status_item = QTableWidgetItem(tr("bridge.status_running_dot", "● 运行") if distro.is_running else tr("bridge.status_stopped_dot", "○ 停止"))
            wsl_status_item.setForeground(QColor("#3fb950") if distro.is_running else QColor("#8b949e"))
            
            if distro.is_running:
                is_connected = distro.name in connected_distro_names
                bridge_status_item = QTableWidgetItem(tr("bridge.status_connected", "● 已连接") if is_connected else tr("bridge.status_disconnected", "○ 未连接"))
                bridge_status_item.setForeground(QColor("#3fb950") if is_connected else QColor("#f85149"))
            else:
                bridge_status_item = QTableWidgetItem("--")
                bridge_status_item.setForeground(QColor("#8b949e"))
            
            self._wsl_status_table.setItem(row, 0, name_item)
            self._wsl_status_table.setItem(row, 1, wsl_status_item)
            self._wsl_status_table.setItem(row, 2, bridge_status_item)

    def update_client_count(self, count: int):
        pass
    
    def update_distro_list(self, distros: list):
        self._add_log(tr("bridge.msg.wsl_list_updated", "✓ WSL 分发列表已更新，共 {count} 个").format(count=len(distros)))
    
    def _update_last_activity(self):
        pass
    
    def _add_log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self._log_text.append(log_entry)
        
        scrollbar = self._log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def on_wsl_status_changed(self, distros: List[Dict], running_count: int, stopped_count: int):
        self._update_wsl_table_from_data(distros)

    def on_wsl_distro_started(self, distro_name: str):
        self._add_log(tr("bridge.msg.wsl_started", "✓ WSL '{name}' 已启动").format(name=distro_name))
        self.refresh_wsl_status.emit()

    def on_wsl_distro_stopped(self, distro_name: str):
        self._add_log(tr("bridge.msg.wsl_stopped", "✓ WSL '{name}' 已停止").format(name=distro_name))
        self.refresh_wsl_status.emit()

    def _update_wsl_table_from_data(self, distros: List[Dict]):
        self._wsl_status_table.setRowCount(len(distros))
        
        for row, distro in enumerate(distros):
            name_item = QTableWidgetItem(distro.get("name", ""))
            name_item.setForeground(QColor("#c9d1d9"))
            
            is_running = distro.get("is_running", False)
            wsl_status_item = QTableWidgetItem(f"● {tr('bridge.status_running_dot', '运行')}" if is_running else f"○ {tr('bridge.status_stopped_dot', '停止')}")
            wsl_status_item.setForeground(QColor("#3fb950") if is_running else QColor("#8b949e"))
            
            bridge_status_item = QTableWidgetItem("--")
            bridge_status_item.setForeground(QColor("#8b949e"))
            
            self._wsl_status_table.setItem(row, 0, name_item)
            self._wsl_status_table.setItem(row, 1, wsl_status_item)
            self._wsl_status_table.setItem(row, 2, bridge_status_item)
