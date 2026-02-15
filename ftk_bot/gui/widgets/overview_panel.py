from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QFrame, QScrollArea, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from ...core import WSLManager, NanobotController, ConfigManager
from ...models import DistroStatus


class StatusCard(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statusCard")
        self._init_ui(title)

    def _init_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")
        layout.addWidget(self.title_label)

        self.status_indicator = QLabel("●")
        self.status_indicator.setObjectName("statusIndicator")
        self.status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(24)
        self.status_indicator.setFont(font)
        layout.addWidget(self.status_indicator)

        self.status_label = QLabel("未检测")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.info_label = QLabel("")
        self.info_label.setObjectName("infoLabel")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        self.button_layout = QHBoxLayout()
        self.start_btn = QPushButton("启动")
        self.stop_btn = QPushButton("停止")
        self.button_layout.addWidget(self.start_btn)
        self.button_layout.addWidget(self.stop_btn)
        layout.addLayout(self.button_layout)

    def set_status(self, is_running: bool, info: str = ""):
        if is_running:
            self.status_indicator.setStyleSheet("color: #4caf50;")
            self.status_label.setText("运行中")
        else:
            self.status_indicator.setStyleSheet("color: #f44336;")
            self.status_label.setText("已停止")
        self.info_label.setText(info)

    def set_running_style(self):
        from ..styles import get_status_card_style, COLORS
        self.setStyleSheet(get_status_card_style())


class OverviewPanel(QWidget):
    def __init__(
        self,
        wsl_manager: WSLManager,
        nanobot_controller: NanobotController,
        config_manager: ConfigManager,
        parent=None
    ):
        super().__init__(parent)
        self._wsl_manager = wsl_manager
        self._nanobot_controller = nanobot_controller
        self._config_manager = config_manager

        self._init_ui()
        self._init_connections()
        self._refresh_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("系统概览")
        title.setObjectName("panelTitle")
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        status_layout = QHBoxLayout()

        self.wsl_card = StatusCard("WSL 状态")
        self.wsl_card.set_running_style()
        status_layout.addWidget(self.wsl_card)

        self.nanobot_card = StatusCard("Nanobot 状态")
        self.nanobot_card.set_running_style()
        status_layout.addWidget(self.nanobot_card)

        layout.addLayout(status_layout)

        quick_actions_group = QGroupBox("快速操作")
        quick_actions_group.setObjectName("quickActions")
        quick_layout = QHBoxLayout(quick_actions_group)

        self.send_msg_btn = QPushButton("发送消息")
        self.view_log_btn = QPushButton("查看日志")
        self.open_workspace_btn = QPushButton("打开工作空间")
        self.edit_config_btn = QPushButton("编辑配置")

        for btn in [self.send_msg_btn, self.view_log_btn, self.open_workspace_btn, self.edit_config_btn]:
            btn.setMinimumHeight(40)
            quick_layout.addWidget(btn)

        layout.addWidget(quick_actions_group)

        activity_group = QGroupBox("最近活动")
        activity_group.setObjectName("activityGroup")
        activity_layout = QVBoxLayout(activity_group)

        self.activity_list = QLabel("暂无活动记录")
        self.activity_list.setWordWrap(True)
        self.activity_list.setAlignment(Qt.AlignmentFlag.AlignTop)
        activity_layout.addWidget(self.activity_list)

        layout.addWidget(activity_group, 1)

        # 样式已在全局样式表中定义

    def _init_connections(self):
        # WSL 状态卡片按钮
        self.wsl_card.start_btn.clicked.connect(self._on_wsl_start_clicked)
        self.wsl_card.stop_btn.clicked.connect(self._stop_wsl)
        
        # Nanobot 状态卡片按钮
        self.nanobot_card.start_btn.clicked.connect(self._start_nanobot)
        self.nanobot_card.stop_btn.clicked.connect(self._stop_nanobot)

        # 快速操作按钮
        self.send_msg_btn.clicked.connect(self._send_message)
        self.view_log_btn.clicked.connect(self._show_log_panel)
        self.open_workspace_btn.clicked.connect(self._open_workspace)
        self.edit_config_btn.clicked.connect(self._show_config_panel)
    
    def _on_wsl_start_clicked(self):
        """根据当前按钮文本决定操作"""
        btn_text = self.wsl_card.start_btn.text()
        if btn_text == "启动":
            self._start_wsl()
        elif btn_text == "安装 WSL":
            self._install_wsl()
        elif btn_text == "安装分发":
            self._install_distro()

    def _refresh_status(self):
        # 始终确保按钮连接正确，不断开重连
        btn_text = self.wsl_card.start_btn.text()
        
        if not self._wsl_manager.is_wsl_installed():
            self.wsl_card.set_status(False, "WSL 未安装")
            self.wsl_card.start_btn.setText("安装 WSL")
            self.nanobot_card.set_status(False, "需要 WSL")
            return
        
        distros = self._wsl_manager.list_distros()
        if not distros:
            self.wsl_card.set_status(False, "无 WSL 分发")
            self.wsl_card.start_btn.setText("安装分发")
            self.nanobot_card.set_status(False, "需要 WSL 分发")
            return
        
        self._reset_wsl_buttons()
        
        default_distro = next(
            (d for d in distros if d.is_default),
            distros[0]
        )
        self.update_wsl_status(default_distro.name, default_distro.is_running)

        config = self._config_manager.get_default()
        if config:
            is_running = self._nanobot_controller.is_running(config.name)
            self.update_nanobot_status(config.name, is_running)
        else:
            self.nanobot_card.set_status(False, "无配置\n点击启动创建")

    def _install_wsl(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "安装 WSL",
            "是否安装 WSL？\n这将运行 'wsl --install' 命令。\n安装后需要重启计算机。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            import subprocess
            try:
                subprocess.run(["wsl.exe", "--install"], check=True)
                QMessageBox.information(self, "提示", "WSL 安装命令已执行，请重启计算机后继续。")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"安装失败: {e}")

    def _install_distro(self):
        from PyQt6.QtWidgets import QMessageBox, QInputDialog
        available = self._wsl_manager.get_available_distros()
        if not available:
            available = ["Ubuntu", "Debian", "kali-linux", "openSUSE-42", "SLES-12"]
        
        distro, ok = QInputDialog.getItem(
            self, "安装 WSL 分发",
            "选择要安装的分发:", available, 0, False
        )
        if ok and distro:
            reply = QMessageBox.question(
                self, "确认安装",
                f"是否安装 {distro}？\n这可能需要几分钟时间。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.add_activity(f"正在安装 {distro}...")
                success = self._wsl_manager.install_distro(distro)
                if success:
                    QMessageBox.information(self, "成功", f"{distro} 安装完成！")
                    self.add_activity(f"{distro} 安装完成")
                    self._refresh_status()
                else:
                    QMessageBox.warning(self, "错误", f"安装 {distro} 失败")

    def update_wsl_status(self, distro_name: str, is_running: bool):
        distros = self._wsl_manager.list_distros()
        distro = next((d for d in distros if d.name == distro_name), None)

        if distro:
            info = f"{distro_name}\nWSL{distro.version}"
            if distro.is_default:
                info += " | 默认"
            self.wsl_card.set_status(is_running, info)

    def update_nanobot_status(self, config_name: str, is_running: bool):
        config = self._config_manager.get(config_name)
        if config:
            instance = self._nanobot_controller.get_instance(config_name)
            info = f"配置: {config_name}\n"
            if instance and instance.running_duration:
                info += f"运行时间: {instance.running_duration}"
            else:
                info += "未运行"
            self.nanobot_card.set_status(is_running, info)

    def _start_wsl(self):
        distros = self._wsl_manager.list_distros()
        if not distros:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", "未检测到 WSL 分发，请先安装 WSL 并创建分发。")
            self._refresh_status()
            return
        default_distro = next(
            (d for d in distros if d.is_default),
            distros[0]
        )
        success = self._wsl_manager.start_distro(default_distro.name)
        if success:
            self.update_wsl_status(default_distro.name, True)
            self.add_activity(f"已启动 WSL: {default_distro.name}")
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"无法启动 WSL 分发: {default_distro.name}")

    def _stop_wsl(self):
        distros = self._wsl_manager.list_distros()
        if not distros:
            return
        default_distro = next(
            (d for d in distros if d.is_default),
            distros[0]
        )
        success = self._wsl_manager.stop_distro(default_distro.name)
        if success:
            self.update_wsl_status(default_distro.name, False)
            self.add_activity(f"已停止 WSL: {default_distro.name}")

    def _reset_wsl_buttons(self):
        try:
            self.wsl_card.start_btn.clicked.disconnect()
        except TypeError:
            pass
        self.wsl_card.start_btn.setText("启动")
        self.wsl_card.start_btn.clicked.connect(self._start_wsl)

    def _start_nanobot(self):
        from PyQt6.QtWidgets import QMessageBox
        
        config = self._config_manager.get_default()
        if not config:
            reply = QMessageBox.question(
                self, "创建配置",
                "没有找到默认配置，是否创建一个新配置？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._create_default_config()
            return
        
        distros = self._wsl_manager.list_distros()
        if not distros:
            QMessageBox.warning(self, "错误", "请先启动 WSL 分发。")
            return
        
        if not config.distro_name:
            default_distro = next((d for d in distros if d.is_default), distros[0])
            config.distro_name = default_distro.name
            self._config_manager.save(config)
        
        distro = self._wsl_manager.get_distro(config.distro_name)
        if not distro or not distro.is_running:
            reply = QMessageBox.question(
                self, "启动 WSL",
                f"WSL 分发 '{config.distro_name}' 未运行，是否启动？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                success = self._wsl_manager.start_distro(config.distro_name)
                if not success:
                    QMessageBox.warning(self, "错误", f"无法启动 WSL 分发: {config.distro_name}")
                    return
            else:
                return
        
        self.add_activity(f"正在启动 Nanobot: {config.name}...")
        success = self._nanobot_controller.start(config)
        if success:
            self.add_activity(f"Nanobot {config.name} 启动成功")
            self.update_nanobot_status(config.name, True)
        else:
            QMessageBox.warning(self, "错误", f"无法启动 Nanobot: {config.name}")

    def _stop_nanobot(self):
        from PyQt6.QtWidgets import QMessageBox
        
        config = self._config_manager.get_default()
        if not config:
            QMessageBox.warning(self, "错误", "没有找到默认配置。")
            return
        
        self.add_activity(f"正在停止 Nanobot: {config.name}...")
        success = self._nanobot_controller.stop(config.name)
        if success:
            self.add_activity(f"Nanobot {config.name} 已停止")
            self.update_nanobot_status(config.name, False)
        else:
            QMessageBox.warning(self, "错误", f"无法停止 Nanobot: {config.name}")

    def _create_default_config(self):
        from PyQt6.QtWidgets import QInputDialog
        
        distros = self._wsl_manager.list_distros()
        distro_name = ""
        if distros:
            default_distro = next((d for d in distros if d.is_default), distros[0])
            distro_name = default_distro.name
        
        config = self._config_manager.create_default_config(distro_name)
        self.add_activity(f"已创建默认配置: {config.name}")
        self.update_nanobot_status(config.name, False)

    def _show_log_panel(self):
        self._navigate_to_panel(4)  # 日志面板索引

    def _show_config_panel(self):
        self._navigate_to_panel(2)  # 配置面板索引
    
    def _send_message(self):
        """发送消息到 Nanobot"""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        config = self._config_manager.get_default()
        if not config:
            QMessageBox.warning(self, "错误", "请先创建配置")
            return
        
        if not self._nanobot_controller.is_running(config.name):
            QMessageBox.warning(self, "错误", "Nanobot 未运行")
            return
        
        text, ok = QInputDialog.getMultiLineText(
            self, "发送消息", "输入要发送的消息:"
        )
        if ok and text.strip():
            self.add_activity(f"发送消息: {text[:50]}...")
            # 这里可以扩展为实际发送消息的功能
    
    def _open_workspace(self):
        """打开工作空间目录"""
        import subprocess
        config = self._config_manager.get_default()
        if not config or not config.windows_workspace:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", "请先配置工作空间路径")
            return
        
        try:
            subprocess.Popen(["explorer", config.windows_workspace])
            self.add_activity(f"打开工作空间: {config.windows_workspace}")
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"无法打开目录: {e}")
    
    def _navigate_to_panel(self, index: int):
        """导航到指定面板"""
        # 查找父窗口中的 content_stack
        parent = self.parent()
        while parent:
            if hasattr(parent, 'content_stack'):
                parent.content_stack.setCurrentIndex(index)
                return
            if hasattr(parent, 'setCurrentIndex'):
                parent.setCurrentIndex(index)
                return
            parent = parent.parent()
        
        # 尝试通过祖父窗口查找
        grandparent = self.parent().parent() if self.parent() else None
        if grandparent and hasattr(grandparent, 'content_stack'):
            grandparent.content_stack.setCurrentIndex(index)
        elif grandparent and hasattr(grandparent, 'setCurrentIndex'):
            grandparent.setCurrentIndex(index)

    def add_activity(self, message: str):
        current = self.activity_list.text()
        if current == "暂无活动记录":
            current = ""
        import time
        timestamp = time.strftime("%H:%M:%S")
        new_activity = f"• {timestamp}: {message}"
        self.activity_list.setText(new_activity + "\n" + current)
