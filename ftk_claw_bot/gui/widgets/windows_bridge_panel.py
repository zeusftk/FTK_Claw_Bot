from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QGroupBox, QGridLayout, QLineEdit, QTextEdit,
    QComboBox, QScrollArea, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPixmap
from typing import Optional
from datetime import datetime


class WindowsBridgePanel(QWidget):
    start_bridge = pyqtSignal()
    stop_bridge = pyqtSignal()
    
    def __init__(self, bridge_manager=None, windows_bridge=None, parent=None):
        super().__init__(parent)
        self._bridge_manager = bridge_manager
        self._windows_bridge = windows_bridge
        self._bridge_status = False
        self._agent_status = "stopped"
        self._last_activity = None
        
        self._init_ui()
    
    def set_bridge_manager(self, bridge_manager):
        self._bridge_manager = bridge_manager
        if bridge_manager:
            bridge_manager.register_status_callback(self._on_agent_status_changed)
    
    def set_windows_bridge(self, windows_bridge):
        self._windows_bridge = windows_bridge
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        title = QLabel("桥接控制")
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("color: #f0f6fc;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self._status_label = QLabel("状态: 未运行")
        self._status_label.setStyleSheet("color: #8b949e; font-size: 14px;")
        header_layout.addWidget(self._status_label)
        
        self._toggle_btn = QPushButton("启动桥接")
        self._toggle_btn.setObjectName("primaryButton")
        self._toggle_btn.clicked.connect(self._on_toggle_bridge)
        header_layout.addWidget(self._toggle_btn)
        
        main_layout.addLayout(header_layout)
        
        self._status_card = self._create_status_card()
        main_layout.addWidget(self._status_card)
        
        quick_action_group = self._create_quick_actions_group()
        main_layout.addWidget(quick_action_group)
        
        function_grid = QGridLayout()
        function_grid.setSpacing(16)
        
        mouse_group = self._create_mouse_control_group()
        function_grid.addWidget(mouse_group, 0, 0)
        
        keyboard_group = self._create_keyboard_control_group()
        function_grid.addWidget(keyboard_group, 0, 1)
        
        screenshot_group = self._create_screenshot_group()
        function_grid.addWidget(screenshot_group, 1, 0)
        
        window_group = self._create_window_management_group()
        function_grid.addWidget(window_group, 1, 1)
        
        main_layout.addLayout(function_grid)
        
        log_group = QGroupBox("操作日志")
        log_group.setStyleSheet("""
            QGroupBox {
                color: #c9d1d9;
                font-weight: 600;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                top: -5px;
                padding: 0 5px;
                background-color: #161b22;
            }
        """)
        
        log_layout = QVBoxLayout(log_group)
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setFont(QFont("Consolas", 9))
        self._log_text.setStyleSheet("""
            QTextEdit {
                background-color: #0d1117;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        self._log_text.setFixedHeight(150)
        log_layout.addWidget(self._log_text)
        
        main_layout.addWidget(log_group)
        
        help_label = QLabel(
            "💡 提示: 桥接服务会在连接 Bot 时自动启动。"
            "您可以使用快速操作按钮进行测试，或通过聊天面板让 Nanobot 执行自动化操作。"
        )
        help_label.setStyleSheet("color: #8b949e; font-size: 11px; padding: 8px;")
        help_label.setWordWrap(True)
        main_layout.addWidget(help_label)
    
    def _create_status_card(self) -> QFrame:
        """创建状态卡片"""
        card = QFrame()
        card.setObjectName("statusCard")
        card.setStyleSheet("""
            QFrame#statusCard {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        
        title = QLabel("连接状态")
        title.setStyleSheet("color: #f0f6fc; font-weight: 600; font-size: 14px;")
        layout.addWidget(title)
        
        self._windows_status_label = QLabel("Windows 端: ● 未运行")
        self._windows_status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(self._windows_status_label)
        
        self._wsl_status_label = QLabel("WSL 端: ● 未连接")
        self._wsl_status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(self._wsl_status_label)
        
        self._last_activity_label = QLabel("最后活动: --")
        self._last_activity_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(self._last_activity_label)
        
        return card
    
    def _create_quick_actions_group(self) -> QGroupBox:
        """创建快速操作区域"""
        group = QGroupBox("快速操作")
        group.setStyleSheet("""
            QGroupBox {
                color: #c9d1d9;
                font-weight: 600;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                top: -5px;
                padding: 0 5px;
                background-color: #161b22;
            }
        """)
        
        layout = QHBoxLayout(group)
        layout.setSpacing(12)
        
        screenshot_btn = QPushButton("📸 截图")
        screenshot_btn.setObjectName("smallButton")
        screenshot_btn.setFixedHeight(36)
        screenshot_btn.clicked.connect(self._on_quick_screenshot)
        layout.addWidget(screenshot_btn)
        
        clipboard_btn = QPushButton("📋 剪贴板")
        clipboard_btn.setObjectName("smallButton")
        clipboard_btn.setFixedHeight(36)
        clipboard_btn.clicked.connect(self._on_quick_clipboard)
        layout.addWidget(clipboard_btn)
        
        windows_btn = QPushButton("🪟 窗口列表")
        windows_btn.setObjectName("smallButton")
        windows_btn.setFixedHeight(36)
        windows_btn.clicked.connect(self._on_list_windows)
        layout.addWidget(windows_btn)
        
        mouse_pos_btn = QPushButton("🖱 鼠标位置")
        mouse_pos_btn.setObjectName("smallButton")
        mouse_pos_btn.setFixedHeight(36)
        mouse_pos_btn.clicked.connect(self._on_get_mouse_position)
        layout.addWidget(mouse_pos_btn)
        
        layout.addStretch()
        
        return group
    
    def _create_mouse_control_group(self) -> QGroupBox:
        """创建鼠标控制面板"""
        group = QGroupBox("鼠标控制")
        group.setStyleSheet("""
            QGroupBox {
                color: #c9d1d9;
                font-weight: 600;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                top: -5px;
                padding: 0 5px;
                background-color: #161b22;
            }
        """)
        
        layout = QVBoxLayout(group)
        
        # 鼠标移动
        move_layout = QHBoxLayout()
        move_layout.addWidget(QLabel("移动到:"))
        self._mouse_x = QLineEdit()
        self._mouse_x.setPlaceholderText("X")
        self._mouse_x.setFixedWidth(80)
        move_layout.addWidget(self._mouse_x)
        
        move_layout.addWidget(QLabel(","))
        
        self._mouse_y = QLineEdit()
        self._mouse_y.setPlaceholderText("Y")
        self._mouse_y.setFixedWidth(80)
        move_layout.addWidget(self._mouse_y)
        
        move_btn = QPushButton("移动")
        move_btn.setObjectName("smallButton")
        move_btn.clicked.connect(self._on_mouse_move)
        move_layout.addWidget(move_btn)
        layout.addLayout(move_layout)
        
        # 鼠标点击
        click_layout = QHBoxLayout()
        click_layout.addWidget(QLabel("点击类型:"))
        
        self._click_type = QComboBox()
        self._click_type.addItems(["左键", "右键", "双击"])
        self._click_type.setFixedWidth(100)
        click_layout.addWidget(self._click_type)
        
        click_btn = QPushButton("执行点击")
        click_btn.setObjectName("smallButton")
        click_btn.clicked.connect(self._on_mouse_click)
        click_layout.addWidget(click_btn)
        layout.addLayout(click_layout)
        
        return group
    
    def _create_keyboard_control_group(self) -> QGroupBox:
        """创建键盘控制面板"""
        group = QGroupBox("键盘控制")
        group.setStyleSheet("""
            QGroupBox {
                color: #c9d1d9;
                font-weight: 600;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                top: -5px;
                padding: 0 5px;
                background-color: #161b22;
            }
        """)
        
        layout = QVBoxLayout(group)
        
        # 文本输入
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("输入文本:"))
        self._keyboard_text = QLineEdit()
        self._keyboard_text.setPlaceholderText("输入要键入的文本")
        type_layout.addWidget(self._keyboard_text)
        
        type_btn = QPushButton("输入")
        type_btn.setObjectName("smallButton")
        type_btn.clicked.connect(self._on_keyboard_type)
        type_layout.addWidget(type_btn)
        layout.addLayout(type_layout)
        
        # 按键
        press_layout = QHBoxLayout()
        press_layout.addWidget(QLabel("按键:"))
        self._keyboard_key = QLineEdit()
        self._keyboard_key.setPlaceholderText("如: enter, ctrl, alt")
        self._keyboard_key.setFixedWidth(120)
        press_layout.addWidget(self._keyboard_key)
        
        press_btn = QPushButton("按下")
        press_btn.setObjectName("smallButton")
        press_btn.clicked.connect(self._on_keyboard_press)
        press_layout.addWidget(press_btn)
        layout.addLayout(press_layout)
        
        return group
    
    def _create_screenshot_group(self) -> QGroupBox:
        """创建屏幕截图面板"""
        group = QGroupBox("屏幕截图")
        group.setStyleSheet("""
            QGroupBox {
                color: #c9d1d9;
                font-weight: 600;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                top: -5px;
                padding: 0 5px;
                background-color: #161b22;
            }
        """)
        
        layout = QVBoxLayout(group)
        
        # 截图按钮
        screenshot_btn = QPushButton("截取屏幕")
        screenshot_btn.setObjectName("primaryButton")
        screenshot_btn.clicked.connect(self._on_screenshot)
        layout.addWidget(screenshot_btn)
        
        # 截图信息
        self._screenshot_info = QLabel("点击按钮开始截图")
        self._screenshot_info.setStyleSheet("color: #8b949e; font-size: 12px;")
        self._screenshot_info.setWordWrap(True)
        layout.addWidget(self._screenshot_info)
        
        return group
    
    def _create_window_management_group(self) -> QGroupBox:
        """创建窗口管理面板"""
        group = QGroupBox("窗口管理")
        group.setStyleSheet("""
            QGroupBox {
                color: #c9d1d9;
                font-weight: 600;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                top: -5px;
                padding: 0 5px;
                background-color: #161b22;
            }
        """)
        
        layout = QVBoxLayout(group)
        
        # 查找窗口
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("窗口标题:"))
        self._window_title = QLineEdit()
        self._window_title.setPlaceholderText("输入窗口标题")
        find_layout.addWidget(self._window_title)
        
        find_btn = QPushButton("查找")
        find_btn.setObjectName("smallButton")
        find_btn.clicked.connect(self._on_find_window)
        find_layout.addWidget(find_btn)
        layout.addLayout(find_layout)
        
        # 窗口列表
        list_btn = QPushButton("列出所有窗口")
        list_btn.setObjectName("smallButton")
        list_btn.clicked.connect(self._on_list_windows)
        layout.addWidget(list_btn)
        
        return group
    
    def _on_toggle_bridge(self):
        """处理启动/停止桥接按钮点击"""
        if self._bridge_status:
            self.stop_bridge.emit()
            self.set_bridge_status(False)
        else:
            self.start_bridge.emit()
            self.set_bridge_status(True)
    
    def _check_bridge_available(self) -> bool:
        """检查桥接服务是否可用"""
        if not self._windows_bridge or not self._windows_bridge.is_running:
            QMessageBox.warning(self, "提示", "桥接服务未启动，请先启动桥接服务")
            return False
        return True
    
    def _confirm_action(self, action_description: str) -> bool:
        """确认敏感操作
        
        Args:
            action_description: 操作描述
            
        Returns:
            用户是否确认执行
        """
        reply = QMessageBox.question(
            self,
            "确认操作",
            f"即将执行: {action_description}\n\n是否继续?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
    
    def _on_mouse_move(self):
        """处理鼠标移动"""
        if not self._check_bridge_available():
            return
        try:
            x = int(self._mouse_x.text())
            y = int(self._mouse_y.text())
            
            from ftk_claw_bot.services.windows_bridge import WindowsAutomation
            automation = WindowsAutomation()
            success = automation.mouse_move(x, y)
            
            if success:
                self._add_log(f"✓ 移动鼠标到: ({x}, {y})")
                self._update_last_activity()
            else:
                self._add_log(f"✗ 移动鼠标失败")
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的坐标")
    
    def _on_mouse_click(self):
        """处理鼠标点击"""
        if not self._check_bridge_available():
            return
        click_type = self._click_type.currentText()
        
        if not self._confirm_action(f"鼠标{click_type}点击"):
            return
        
        from ftk_claw_bot.services.windows_bridge import WindowsAutomation
        automation = WindowsAutomation()
        
        pos = automation.get_mouse_position()
        if click_type == "左键":
            success = automation.mouse_click(pos[0], pos[1], "left", 1)
        elif click_type == "右键":
            success = automation.mouse_click(pos[0], pos[1], "right", 1)
        else:
            success = automation.mouse_click(pos[0], pos[1], "left", 2)
        
        if success:
            self._add_log(f"✓ 执行{click_type}点击 @ ({pos[0]}, {pos[1]})")
            self._update_last_activity()
        else:
            self._add_log(f"✗ 执行{click_type}点击失败")
    
    def _on_keyboard_type(self):
        """处理键盘输入"""
        if not self._check_bridge_available():
            return
        text = self._keyboard_text.text()
        if not text:
            QMessageBox.warning(self, "错误", "请输入要键入的文本")
            return
        
        if not self._confirm_action(f"输入文本: {text}"):
            return
        
        from ftk_claw_bot.services.windows_bridge import WindowsAutomation
        automation = WindowsAutomation()
        success = automation.keyboard_type(text)
        
        if success:
            self._add_log(f"✓ 输入文本: {text}")
            self._update_last_activity()
        else:
            self._add_log(f"✗ 输入文本失败")
    
    def _on_keyboard_press(self):
        """处理键盘按键"""
        if not self._check_bridge_available():
            return
        key = self._keyboard_key.text()
        if not key:
            QMessageBox.warning(self, "错误", "请输入要按下的按键")
            return
        
        if not self._confirm_action(f"按下按键: {key}"):
            return
        
        from ftk_claw_bot.services.windows_bridge import WindowsAutomation
        automation = WindowsAutomation()
        success = automation.keyboard_press(key)
        
        if success:
            self._add_log(f"✓ 按下按键: {key}")
            self._update_last_activity()
        else:
            self._add_log(f"✗ 按下按键失败")
    
    def _on_screenshot(self):
        """处理屏幕截图"""
        if not self._check_bridge_available():
            return
        
        from ftk_claw_bot.services.windows_bridge import WindowsAutomation
        automation = WindowsAutomation()
        data = automation.screenshot()
        
        if data:
            import tempfile
            import os
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            temp_dir = tempfile.gettempdir()
            filepath = os.path.join(temp_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(data)
            
            automation.set_clipboard(f"[截图已保存: {filepath}]")
            self._screenshot_info.setText(f"截图已保存: {filepath}")
            self._add_log(f"✓ 截图已保存: {filepath}")
            self._update_last_activity()
        else:
            self._screenshot_info.setText("截图失败")
            self._add_log(f"✗ 截图失败")
    
    def _on_find_window(self):
        """处理查找窗口"""
        if not self._check_bridge_available():
            return
        title = self._window_title.text()
        if not title:
            QMessageBox.warning(self, "错误", "请输入窗口标题")
            return
        
        from ftk_claw_bot.services.windows_bridge import WindowsAutomation
        automation = WindowsAutomation()
        window = automation.find_window(title)
        
        if window:
            self._add_log(f"✓ 找到窗口: {window.title}")
            self._add_log(f"  位置: {window.rect}")
            self._update_last_activity()
        else:
            self._add_log(f"✗ 未找到窗口: {title}")
    
    def _on_list_windows(self):
        """处理列出窗口"""
        if not self._check_bridge_available():
            return
        
        from ftk_claw_bot.services.windows_bridge import WindowsAutomation
        automation = WindowsAutomation()
        windows = automation.list_windows()
        
        if windows:
            self._add_log(f"✓ 找到 {len(windows)} 个窗口:")
            for i, w in enumerate(windows[:10]):
                if w.title:
                    self._add_log(f"  {i+1}. {w.title}")
            if len(windows) > 10:
                self._add_log(f"  ... 还有 {len(windows) - 10} 个窗口")
            self._update_last_activity()
        else:
            self._add_log(f"✗ 未找到任何窗口")
    
    def _on_quick_screenshot(self):
        """快速截图"""
        self._on_screenshot()
    
    def _on_quick_clipboard(self):
        """获取剪贴板内容"""
        if not self._check_bridge_available():
            return
        
        from ftk_claw_bot.services.windows_bridge import WindowsAutomation
        automation = WindowsAutomation()
        text = automation.get_clipboard()
        
        if text:
            self._add_log(f"✓ 剪贴板内容: {text[:100]}{'...' if len(text) > 100 else ''}")
            self._update_last_activity()
        else:
            self._add_log(f"剪贴板为空")
    
    def _on_get_mouse_position(self):
        """获取鼠标位置"""
        if not self._check_bridge_available():
            return
        
        from ftk_claw_bot.services.windows_bridge import WindowsAutomation
        automation = WindowsAutomation()
        pos = automation.get_mouse_position()
        
        self._add_log(f"✓ 鼠标位置: ({pos[0]}, {pos[1]})")
        self._mouse_x.setText(str(pos[0]))
        self._mouse_y.setText(str(pos[1]))
        self._update_last_activity()
    
    def set_bridge_status(self, running: bool):
        """设置桥接状态"""
        self._bridge_status = running
        if running:
            self._status_label.setText("状态: 运行中")
            self._status_label.setStyleSheet("color: #3fb950; font-size: 14px;")
            self._toggle_btn.setText("停止桥接")
            self._windows_status_label.setText("Windows 端: ● 运行中 (127.0.0.1:9527)")
            self._windows_status_label.setStyleSheet("color: #3fb950; font-size: 12px;")
            self._add_log("✓ 桥接服务已启动")
        else:
            self._status_label.setText("状态: 未运行")
            self._status_label.setStyleSheet("color: #8b949e; font-size: 14px;")
            self._toggle_btn.setText("启动桥接")
            self._windows_status_label.setText("Windows 端: ● 未运行")
            self._windows_status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
            self._wsl_status_label.setText("WSL 端: ● 未连接")
            self._wsl_status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
            self._add_log("桥接服务已停止")
    
    def set_agent_status(self, status: str, distro_name: str = None, wsl_ip: str = None):
        """设置 WSL 端代理状态"""
        self._agent_status = status
        if status == "running":
            self._wsl_status_label.setText(f"WSL 端: ● 已连接 ({distro_name} @ {wsl_ip})")
            self._wsl_status_label.setStyleSheet("color: #3fb950; font-size: 12px;")
        elif status == "starting":
            self._wsl_status_label.setText("WSL 端: ● 连接中...")
            self._wsl_status_label.setStyleSheet("color: #d29922; font-size: 12px;")
        elif status == "error":
            self._wsl_status_label.setText("WSL 端: ● 连接错误")
            self._wsl_status_label.setStyleSheet("color: #f85149; font-size: 12px;")
        else:
            self._wsl_status_label.setText("WSL 端: ● 未连接")
            self._wsl_status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
    
    def _on_agent_status_changed(self, status):
        """处理代理状态变化"""
        from ftk_claw_bot.core.bridge_manager import AgentStatus
        if status == AgentStatus.RUNNING:
            self.set_agent_status("running")
        elif status == AgentStatus.STARTING:
            self.set_agent_status("starting")
        elif status == AgentStatus.ERROR:
            self.set_agent_status("error")
        else:
            self.set_agent_status("stopped")
    
    def _update_last_activity(self):
        """更新最后活动时间"""
        self._last_activity = datetime.now()
        self._last_activity_label.setText(f"最后活动: 刚刚")
    
    def _add_log(self, message: str):
        """添加操作日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self._log_text.append(log_entry)
        
        scrollbar = self._log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())