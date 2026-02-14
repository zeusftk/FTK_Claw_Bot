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
        self.wsl_card.start_btn.clicked.connect(self._start_wsl)
        self.wsl_card.stop_btn.clicked.connect(self._stop_wsl)
        self.nanobot_card.start_btn.clicked.connect(self._start_nanobot)
        self.nanobot_card.stop_btn.clicked.connect(self._stop_nanobot)

        self.view_log_btn.clicked.connect(self._show_log_panel)
        self.edit_config_btn.clicked.connect(self._show_config_panel)

    def _refresh_status(self):
        distros = self._wsl_manager.list_distros()
        if distros:
            default_distro = next(
                (d for d in distros if d.is_default),
                distros[0]
            )
            self.update_wsl_status(default_distro.name, default_distro.is_running)

        config = self._config_manager.get_default()
        if config:
            is_running = self._nanobot_controller.is_running(config.name)
            self.update_nanobot_status(config.name, is_running)

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
        if distros:
            default_distro = next(
                (d for d in distros if d.is_default),
                distros[0]
            )
            self._wsl_manager.start_distro(default_distro.name)

    def _stop_wsl(self):
        distros = self._wsl_manager.list_distros()
        if distros:
            default_distro = next(
                (d for d in distros if d.is_default),
                distros[0]
            )
            self._wsl_manager.stop_distro(default_distro.name)

    def _start_nanobot(self):
        config = self._config_manager.get_default()
        if config:
            self._nanobot_controller.start(config)

    def _stop_nanobot(self):
        config = self._config_manager.get_default()
        if config:
            self._nanobot_controller.stop(config.name)

    def _show_log_panel(self):
        parent = self.parent()
        if hasattr(parent, 'setCurrentIndex'):
            parent.setCurrentIndex(4)

    def _show_config_panel(self):
        parent = self.parent()
        if hasattr(parent, 'setCurrentIndex'):
            parent.setCurrentIndex(2)

    def add_activity(self, message: str):
        current = self.activity_list.text()
        if current == "暂无活动记录":
            current = ""
        import time
        timestamp = time.strftime("%H:%M:%S")
        new_activity = f"• {timestamp}: {message}"
        self.activity_list.setText(new_activity + "\n" + current)
