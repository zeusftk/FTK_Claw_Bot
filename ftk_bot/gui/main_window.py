import sys
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QListWidget, QListWidgetItem, QLabel, QPushButton,
    QStatusBar, QSystemTrayIcon, QMenu, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QFont

from ..core import WSLManager, NanobotController, SkillManager, ConfigManager
from ..services import WindowsBridge, MonitorService
from .widgets import WSLPanel, ConfigPanel, SkillPanel, LogPanel, OverviewPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._wsl_manager = WSLManager()
        self._config_manager = ConfigManager()
        self._nanobot_controller = NanobotController(self._wsl_manager)
        self._skill_manager: Optional[SkillManager] = None
        self._windows_bridge = WindowsBridge()
        self._monitor_service = MonitorService(self._wsl_manager, self._nanobot_controller)

        self._init_ui()
        self._init_managers()
        self._init_connections()
        self._init_tray()

    def _init_ui(self):
        self.setWindowTitle("FTK_Bot")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        nav_frame = QFrame()
        nav_frame.setFixedWidth(200)
        nav_frame.setObjectName("navFrame")
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel("FTK_Bot")
        title_label.setObjectName("navTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        nav_layout.addWidget(title_label)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        self.nav_list.setSpacing(5)
        self.nav_list.addItem(QListWidgetItem("概览"))
        self.nav_list.addItem(QListWidgetItem("WSL 管理"))
        self.nav_list.addItem(QListWidgetItem("配置管理"))
        self.nav_list.addItem(QListWidgetItem("技能管理"))
        self.nav_list.addItem(QListWidgetItem("日志查看"))
        self.nav_list.setCurrentRow(0)
        nav_layout.addWidget(self.nav_list)

        nav_layout.addStretch()

        version_label = QLabel("v0.1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setObjectName("versionLabel")
        nav_layout.addWidget(version_label)

        main_layout.addWidget(nav_frame)

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentStack")

        self.overview_panel = OverviewPanel(
            self._wsl_manager,
            self._nanobot_controller,
            self._config_manager
        )
        self.wsl_panel = WSLPanel(self._wsl_manager)
        self.config_panel = ConfigPanel(
            self._config_manager,
            self._wsl_manager
        )
        self.skill_panel = SkillPanel(self._skill_manager)
        self.log_panel = LogPanel()

        self.content_stack.addWidget(self.overview_panel)
        self.content_stack.addWidget(self.wsl_panel)
        self.content_stack.addWidget(self.config_panel)
        self.content_stack.addWidget(self.skill_panel)
        self.content_stack.addWidget(self.log_panel)

        main_layout.addWidget(self.content_stack, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.wsl_status_label = QLabel("WSL: 未检测")
        self.nanobot_status_label = QLabel("Nanobot: 未运行")
        self.resource_label = QLabel("CPU: -- | MEM: --")

        self.status_bar.addWidget(self.wsl_status_label)
        self.status_bar.addWidget(QLabel(" | "))
        self.status_bar.addWidget(self.nanobot_status_label)
        self.status_bar.addWidget(QLabel(" | "))
        self.status_bar.addWidget(self.resource_label)
        self.status_bar.addPermanentWidget(QLabel("FTK_Bot v0.1.0"))

        self._apply_styles()

    def _apply_styles(self):
        from .styles import get_stylesheet
        self.setStyleSheet(get_stylesheet())

    def _init_managers(self):
        distros = self._wsl_manager.list_distros()
        if distros:
            default_config = self._config_manager.get_default()
            if not default_config:
                default_distro = next(
                    (d for d in distros if d.is_default),
                    distros[0]
                )
                self._config_manager.create_default_config(default_distro.name)

            default_config = self._config_manager.get_default()
            if default_config:
                skills_dir = default_config.skills_dir
                if not skills_dir and default_config.windows_workspace:
                    import os
                    skills_dir = os.path.join(default_config.windows_workspace, "skills")
                if skills_dir:
                    self._skill_manager = SkillManager(skills_dir)
                    self.skill_panel.set_skill_manager(self._skill_manager)

        self._monitor_service.start()
        self._windows_bridge.start()

    def _init_connections(self):
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        self._monitor_service.register_callback("wsl_status", self._on_wsl_status_changed)
        self._monitor_service.register_callback("nanobot_status", self._on_nanobot_status_changed)
        self._monitor_service.register_callback("resources", self._on_resources_updated)

        self.wsl_panel.distro_started.connect(self._on_distro_started)
        self.wsl_panel.distro_stopped.connect(self._on_distro_stopped)
        self.config_panel.config_saved.connect(self._on_config_saved)

        # Register log callback to forward nanobot logs to log panel
        self._nanobot_controller.register_log_callback(self._on_nanobot_log)

    def _init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(
            self.style().StandardPixmap.SP_ComputerIcon
        ))
        self.tray_icon.setToolTip("FTK_Bot")

        tray_menu = QMenu()

        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_nav_changed(self, index: int):
        self.content_stack.setCurrentIndex(index)

    def _on_wsl_status_changed(self, data: dict):
        distro_name = data.get("distro_name", "")
        status = data.get("status", "Unknown")
        is_running = data.get("is_running", False)

        self.wsl_status_label.setText(f"WSL ({distro_name}): {status}")

        if is_running:
            self.overview_panel.update_wsl_status(distro_name, True)
        else:
            self.overview_panel.update_wsl_status(distro_name, False)

    def _on_resources_updated(self, data: dict):
        cpu = data.get("cpu_usage", 0.0)
        mem = data.get("memory_usage", 0)
        mem_total = data.get("memory_total", 0)

        mem_mb = mem / (1024 * 1024) if mem else 0
        mem_total_mb = mem_total / (1024 * 1024) if mem_total else 0

        self.resource_label.setText(f"CPU: {cpu:.1f}% | MEM: {mem_mb:.0f}MB / {mem_total_mb:.0f}MB")

    def _on_distro_started(self, distro_name: str):
        self.status_bar.showMessage(f"已启动 WSL 分发: {distro_name}", 3000)

    def _on_distro_stopped(self, distro_name: str):
        self.status_bar.showMessage(f"已停止 WSL 分发: {distro_name}", 3000)

    def _on_config_saved(self, config_name: str):
        config = self._config_manager.get(config_name)
        if config and config.skills_dir:
            self._skill_manager = SkillManager(config.skills_dir)
            self.skill_panel.set_skill_manager(self._skill_manager)
        self.status_bar.showMessage(f"已保存配置: {config_name}", 3000)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "FTK_Bot",
            "程序已最小化到系统托盘",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def _quit_app(self):
        self._monitor_service.stop()
        self._windows_bridge.stop()
        self._wsl_manager.stop_monitoring()
        self.tray_icon.hide()
        QApplication.quit()

    def _on_nanobot_status_changed(self, data: dict):
        """Handle nanobot status changes from monitor service."""
        instance_name = data.get("instance_name", "")
        status = data.get("status", "unknown")
        is_running = data.get("is_running", False)

        self.nanobot_status_label.setText(f"Nanobot ({instance_name}): {status}")

        if is_running:
            self.overview_panel.update_nanobot_status(instance_name, True)
            self.log_panel.add_log("INFO", "Nanobot", f"Instance '{instance_name}' started")
        else:
            self.overview_panel.update_nanobot_status(instance_name, False)
            error = data.get("last_error")
            if error:
                self.log_panel.add_log("ERROR", "Nanobot", f"Instance '{instance_name}' error: {error}")
            else:
                self.log_panel.add_log("INFO", "Nanobot", f"Instance '{instance_name}' stopped")

    def _on_nanobot_log(self, instance_name: str, log_type: str, message: str):
        """Handle nanobot log messages."""
        level = "INFO" if log_type == "stdout" else "DEBUG"
        self.log_panel.add_log(level, f"Nanobot:{instance_name}", message)
