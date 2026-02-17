
import time
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ...core import WSLManager, NanobotController, ConfigManager


class NanobotPanel(QWidget):
    instance_started = pyqtSignal(str)
    instance_stopped = pyqtSignal(str)
    instance_restarted = pyqtSignal(str)

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
        self._apply_styles()
        self._refresh_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QLabel("clawbot 实例管理")
        title.setObjectName("panelTitle")
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        nanobot_group = QGroupBox("实例列表")
        nanobot_group.setObjectName("nanobotGroup")
        nanobot_layout = QVBoxLayout(nanobot_group)
        nanobot_layout.setContentsMargins(12, 12, 12, 12)
        nanobot_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.setMinimumHeight(28)
        header_layout.addWidget(self.refresh_btn)
        header_layout.addStretch()

        nanobot_layout.addLayout(header_layout)

        self.nanobot_table = QTableWidget()
        self.nanobot_table.setColumnCount(6)
        self.nanobot_table.setHorizontalHeaderLabels(["实例名称", "WSL 分发", "状态", "运行时间", "操作", "日志"])
        self.nanobot_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.nanobot_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.nanobot_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.nanobot_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.nanobot_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.nanobot_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.nanobot_table.setColumnWidth(1, 120)
        self.nanobot_table.setColumnWidth(2, 80)
        self.nanobot_table.setColumnWidth(3, 100)
        self.nanobot_table.setColumnWidth(5, 80)
        self.nanobot_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.nanobot_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nanobot_table.setAlternatingRowColors(False)
        self.nanobot_table.verticalHeader().setVisible(False)
        self.nanobot_table.verticalHeader().setDefaultSectionSize(60)
        self.nanobot_table.setMinimumHeight(400)
        nanobot_layout.addWidget(self.nanobot_table)

        layout.addWidget(nanobot_group)

    def _apply_styles(self):
        table_style = """
            QTableWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                outline: none;
                gridline-color: #30363d;
            }
            QTableWidget::item {
                padding: 10px 8px;
                border: none;
                background-color: #161b22;
            }
            QTableWidget::item:alternate {
                background-color: #21262d;
            }
            QHeaderView::section {
                background-color: #21262d;
                color: #f0f6fc;
                padding: 12px 8px;
                border: none;
                border-bottom: 1px solid #30363d;
                font-weight: bold;
            }
            QTableWidget QPushButton {
                border: 1px solid #30363d;
                border-radius: 4px;
                background-color: #21262d !important;
                color: #c9d1d9;
                font-size: 12px;
                font-weight: bold;
            }
            QTableWidget QPushButton:hover {
                background-color: #30363d !important;
                border-color: #484f58;
                color: #f0f6fc;
            }
            QTableWidget QPushButton:pressed {
                background-color: #161b22 !important;
            }
        """
        self.nanobot_table.setStyleSheet(table_style)

    def _init_connections(self):
        self.refresh_btn.clicked.connect(self._refresh_status)

    def _refresh_status(self):
        self._refresh_nanobot_list()

    def _refresh_nanobot_list(self):
        configs = self._config_manager.get_all()
        self.nanobot_table.setRowCount(len(configs))

        for row, (config_name, config) in enumerate(configs.items()):
            bg_color = QColor("#161b22") if row % 2 == 0 else QColor("#21262d")

            name_item = QTableWidgetItem(config_name)
            name_item.setData(Qt.ItemDataRole.UserRole, config_name)
            name_item.setBackground(bg_color)

            distro_item = QTableWidgetItem(config.distro_name)
            distro_item.setBackground(bg_color)

            instance = self._nanobot_controller.get_instance(config_name)
            if instance:
                status_text = instance.status.value
                status_item = QTableWidgetItem(status_text)
                if instance.status.value == "running":
                    status_item.setForeground(QColor("#3fb950"))
                elif instance.status.value == "error":
                    status_item.setForeground(QColor("#f85149"))
                else:
                    status_item.setForeground(QColor("#8b949e"))

                if instance.started_at:
                    uptime = datetime.now() - instance.started_at
                    hours = int(uptime.total_seconds() // 3600)
                    minutes = int((uptime.total_seconds() % 3600) // 60)
                    uptime_text = f"{hours}h {minutes}m"
                else:
                    uptime_text = "--"
            else:
                status_item = QTableWidgetItem("stopped")
                status_item.setForeground(QColor("#8b949e"))
                uptime_text = "--"

            status_item.setBackground(bg_color)
            uptime_item = QTableWidgetItem(uptime_text)
            uptime_item.setBackground(bg_color)

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(6)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            action_widget.setStyleSheet(f"background-color: {bg_color.name()};")

            is_running = instance and instance.status.value == "running"

            if is_running:
                stop_btn = self._create_action_btn("⏹", f"停止: {config_name}", "#da3633", "#f85149", "#b62324")
                stop_btn.clicked.connect(lambda checked, n=config_name: self._stop_nanobot(n))
                action_layout.addWidget(stop_btn)

                restart_btn = self._create_action_btn("🔄", f"重启: {config_name}")
                restart_btn.clicked.connect(lambda checked, n=config_name: self._restart_nanobot(n))
                action_layout.addWidget(restart_btn)
            else:
                start_btn = self._create_action_btn("▶", f"启动: {config_name}", "#238636", "#2ea043", "#196c2e")
                start_btn.clicked.connect(lambda checked, n=config_name: self._start_nanobot(n))
                action_layout.addWidget(start_btn)

            log_btn = self._create_action_btn("📋", f"查看日志: {config_name}")
            log_btn.clicked.connect(lambda checked, n=config_name: self._view_nanobot_logs(n))
            action_layout.addWidget(log_btn)

            action_layout.addStretch()

            self.nanobot_table.setItem(row, 0, name_item)
            self.nanobot_table.setItem(row, 1, distro_item)
            self.nanobot_table.setItem(row, 2, status_item)
            self.nanobot_table.setItem(row, 3, uptime_item)
            self.nanobot_table.setCellWidget(row, 4, action_widget)

            log_widget = QWidget()
            log_layout = QVBoxLayout(log_widget)
            log_layout.setContentsMargins(0, 0, 0, 0)
            log_widget.setStyleSheet(f"background-color: {bg_color.name()};")

            log_btn_short = self._create_action_btn("日志", f"查看日志: {config_name}")
            log_btn_short.setFixedSize(60, 32)
            log_btn_short.clicked.connect(lambda checked, n=config_name: self._view_nanobot_logs(n))
            log_layout.addWidget(log_btn_short)

            self.nanobot_table.setCellWidget(row, 5, log_widget)

    def _start_nanobot(self, config_name: str):
        config = self._config_manager.get(config_name)
        if not config:
            QMessageBox.warning(self, "错误", f"找不到配置: {config_name}")
            return

        success = self._nanobot_controller.start(config)
        if success:
            self.instance_started.emit(config_name)
            self._refresh_nanobot_list()
        else:
            QMessageBox.warning(self, "错误", f"无法启动 Nanobot: {config_name}")

    def _stop_nanobot(self, config_name: str):
        success = self._nanobot_controller.stop(config_name)
        if success:
            self.instance_stopped.emit(config_name)
            self._refresh_nanobot_list()
        else:
            QMessageBox.warning(self, "错误", f"无法停止 Nanobot: {config_name}")

    def _restart_nanobot(self, config_name: str):
        success = self._nanobot_controller.restart(config_name)
        if success:
            self.instance_restarted.emit(config_name)
            self._refresh_nanobot_list()
        else:
            QMessageBox.warning(self, "错误", f"无法重启 Nanobot: {config_name}")

    def _view_nanobot_logs(self, config_name: str):
        logs = self._nanobot_controller.get_logs(config_name, 100)
        if logs:
            log_text = "\n".join(logs)
            QMessageBox.information(self, f"{config_name} 日志", log_text)
        else:
            QMessageBox.information(self, f"{config_name} 日志", "暂无日志")

    def _create_action_btn(self, text: str, tooltip: str, bg_color: str = "#21262d", hover_color: str = "#30363d", pressed_color: str = "#161b22") -> QPushButton:
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setFixedSize(100, 36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                border: 1px solid {'rgba(46, 160, 67, 0.4)' if bg_color == '#238636' else 'rgba(248, 81, 73, 0.4)' if bg_color == '#da3633' else '#30363d'};
                border-radius: 3px;
                color: #ffffff;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border-color: {'rgba(46, 160, 67, 0.8)' if bg_color == '#238636' else 'rgba(248, 81, 73, 0.8)' if bg_color == '#da3633' else '#484f58'};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
        """)
        return btn

    def update_nanobot_status(self, instance_name: str, is_running: bool):
        """更新 clawbot 实例状态

        Args:
            instance_name: 实例名称
            is_running: 是否正在运行
        """
        self._refresh_nanobot_list()
