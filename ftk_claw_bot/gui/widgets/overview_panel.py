import os
import time
import subprocess
import threading
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFrame, QMessageBox, QFileDialog, QProgressDialog, QDialog, QLineEdit,
    QScrollArea, QProgressBar, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from ...core import WSLManager, NanobotController, ConfigManager
from ...models import DistroStatus, WSLDistro
from ...gui.dialogs import show_info, show_critical, show_question, show_warning
from ...utils.thread_safe import ThreadSafeSignal


class ImportProgressDialog(QDialog):
    """WSL 导入进度对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress_value = 0
        self._timer = QTimer()
        self._init_ui()
        self._apply_styles()
    
    def _init_ui(self):
        self.setWindowTitle("导入 WSL 分发")
        self.setFixedSize(450, 200)
        self.setWindowFlags(Qt.WindowType.Dialog)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        layout.addStretch()
        
        title_label = QLabel("导入 WSL 分发")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        self.status_label = QLabel("准备导入...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_font = QFont()
        status_font.setPointSize(10)
        self.status_label.setFont(status_font)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        
        hint_label = QLabel("请稍候，这可能需要几分钟时间...")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_font = QFont()
        hint_font.setPointSize(9)
        hint_label.setFont(hint_font)
        layout.addWidget(hint_label)
    
    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0d1117;
                color: #f0f6fc;
            }
            QLabel {
                color: #f0f6fc;
            }
            QProgressBar {
                background-color: #21262d;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #238636;
                border-radius: 3px;
            }
        """)
    
    def start_animation(self):
        """开始进度动画"""
        self._progress_value = 0
        self._timer.timeout.connect(self._update_progress)
        self._timer.start(100)
    
    def _update_progress(self):
        """更新进度"""
        self._progress_value += 1
        if self._progress_value > 90:
            self._progress_value = 90
        self.progress_bar.setValue(self._progress_value)
        
        if self._progress_value < 25:
            self.status_label.setText("正在读取 tar 文件...")
        elif self._progress_value < 50:
            self.status_label.setText("正在解压文件...")
        elif self._progress_value < 75:
            self.status_label.setText("正在注册 WSL 分发...")
        else:
            self.status_label.setText("正在完成导入...")
    
    def stop_animation(self):
        """停止进度动画"""
        self._timer.stop()
        self.progress_bar.setValue(100)
        self.status_label.setText("导入完成！")
    
    def closeEvent(self, event):
        """关闭事件 - 停止定时器"""
        self._timer.stop()
        super().closeEvent(event)


class ExportProgressDialog(QDialog):
    """WSL 导出进度对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress_value = 0
        self._timer = QTimer()
        self._init_ui()
        self._apply_styles()
    
    def _init_ui(self):
        self.setWindowTitle("导出 WSL 分发")
        self.setFixedSize(450, 200)
        self.setWindowFlags(Qt.WindowType.Dialog)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        layout.addStretch()
        
        title_label = QLabel("导出 WSL 分发")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        self.status_label = QLabel("准备导出...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_font = QFont()
        status_font.setPointSize(10)
        self.status_label.setFont(status_font)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        
        hint_label = QLabel("请稍候，这可能需要几分钟时间...")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_font = QFont()
        hint_font.setPointSize(9)
        hint_label.setFont(hint_font)
        layout.addWidget(hint_label)
    
    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0d1117;
                color: #f0f6fc;
            }
            QLabel {
                color: #f0f6fc;
            }
            QProgressBar {
                background-color: #21262d;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #238636;
                border-radius: 3px;
            }
        """)
    
    def start_animation(self):
        """开始进度动画"""
        self._progress_value = 0
        self._timer.timeout.connect(self._update_progress)
        self._timer.start(100)
    
    def _update_progress(self):
        """更新进度"""
        self._progress_value += 1
        if self._progress_value > 90:
            self._progress_value = 90
        self.progress_bar.setValue(self._progress_value)
        
        if self._progress_value < 25:
            self.status_label.setText("正在准备导出...")
        elif self._progress_value < 50:
            self.status_label.setText("正在打包文件...")
        elif self._progress_value < 75:
            self.status_label.setText("正在创建 tar 文件...")
        else:
            self.status_label.setText("正在完成导出...")
    
    def stop_animation(self, output_path: str = ""):
        """停止进度动画"""
        self._timer.stop()
        self.progress_bar.setValue(100)
        if output_path:
            self.status_label.setText(f"导出完成！\n{output_path}")
        else:
            self.status_label.setText("导出完成！")
    
    def closeEvent(self, event):
        """关闭事件 - 停止定时器"""
        self._timer.stop()
        super().closeEvent(event)


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "0", icon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self._value_label = None
        self._init_ui(title, value, icon)

    def _init_ui(self, title: str, value: str, icon: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(8)

        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("font-size: 18px;")
            header.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        title_label.setStyleSheet("font-size: 12px; color: #8b949e;")
        header.addWidget(title_label)
        header.addStretch()

        layout.addLayout(header)

        self._value_label = QLabel(value)
        self._value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #f0f6fc;")
        layout.addWidget(self._value_label)

    def set_value(self, value: str):
        if self._value_label:
            self._value_label.setText(value)


class OverviewPanel(QWidget):
    distro_started = pyqtSignal(str)
    distro_stopped = pyqtSignal(str)
    distro_imported = pyqtSignal(str)

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
        self._wsl_manager.register_callback(self._on_wsl_state_changed)
        self._refresh_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QLabel("系统概览")
        title.setObjectName("panelTitle")
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        self.distro_count_card = StatCard("WSL 分发", "0", "🐧")
        stats_layout.addWidget(self.distro_count_card)

        self.running_card = StatCard("运行中", "0", "▶")
        stats_layout.addWidget(self.running_card)

        self.config_card = StatCard("配置文件", "0", "⚙")
        stats_layout.addWidget(self.config_card)
        
        self.cpu_card = StatCard("CPU 使用率", "0%", "💻")
        stats_layout.addWidget(self.cpu_card)
        
        self.memory_card = StatCard("内存使用", "0MB", "🧠")
        stats_layout.addWidget(self.memory_card)

        layout.addLayout(stats_layout)

        distro_group = QGroupBox("WSL 分发管理")
        distro_group.setObjectName("distroGroup")
        distro_layout = QVBoxLayout(distro_group)
        distro_layout.setContentsMargins(12, 12, 12, 12)
        distro_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        self.refresh_btn = QPushButton("🔄 刷新")
        self.shutdown_all_btn = QPushButton("⏹ 关闭所有")
        self.import_btn = QPushButton("📥 导入分发")
        self.create_btn = QPushButton("🆕 创建分发")
        self.export_btn = QPushButton("📤 导出分发")

        for btn in [self.refresh_btn, self.shutdown_all_btn, self.import_btn, self.create_btn, self.export_btn]:
            btn.setMinimumHeight(28)

        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(self.shutdown_all_btn)
        header_layout.addWidget(self.import_btn)
        header_layout.addWidget(self.create_btn)
        header_layout.addWidget(self.export_btn)
        header_layout.addStretch()

        distro_layout.addLayout(header_layout)

        self.distro_table = QTableWidget()
        self.distro_table.setColumnCount(8)
        self.distro_table.setHorizontalHeaderLabels(["分发名称", "版本", "状态", "Port", "内核版本", "CPU%", "内存%", "操作"])
        self.distro_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.distro_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.distro_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.distro_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.distro_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.distro_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.distro_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.distro_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.distro_table.setColumnWidth(1, 70)
        self.distro_table.setColumnWidth(2, 80)
        self.distro_table.setColumnWidth(3, 120)
        self.distro_table.setColumnWidth(4, 100)
        self.distro_table.setColumnWidth(5, 60)
        self.distro_table.setColumnWidth(6, 60)
        self.distro_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.distro_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.distro_table.setAlternatingRowColors(False)
        self.distro_table.verticalHeader().setVisible(False)
        self.distro_table.verticalHeader().setDefaultSectionSize(80)
        self.distro_table.setMinimumHeight(300)
        distro_layout.addWidget(self.distro_table)

        layout.addWidget(distro_group)

        quick_actions_group = QGroupBox("快速操作")
        quick_actions_group.setObjectName("quickActions")
        quick_layout = QHBoxLayout(quick_actions_group)
        quick_layout.setSpacing(12)

        self.send_msg_btn = QPushButton("💬 发送消息")
        self.send_msg_btn.setObjectName("primary")
        self.view_log_btn = QPushButton("📋 查看日志")
        self.edit_config_btn = QPushButton("⚙ 编辑配置")

        for btn in [self.send_msg_btn, self.view_log_btn, self.edit_config_btn]:
            btn.setMinimumHeight(40)
            btn.setMinimumWidth(130)
            quick_layout.addWidget(btn)

        layout.addWidget(quick_actions_group)

        activity_group = QGroupBox("最近活动")
        activity_group.setObjectName("activityGroup")
        activity_layout = QVBoxLayout(activity_group)

        activity_scroll = QScrollArea()
        activity_scroll.setWidgetResizable(True)
        activity_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        activity_scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        activity_content = QWidget()
        activity_content_layout = QVBoxLayout(activity_content)
        activity_content_layout.setContentsMargins(0, 0, 0, 0)
        
        self.activity_list = QLabel("暂无活动记录")
        self.activity_list.setWordWrap(True)
        self.activity_list.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.activity_list.setStyleSheet("color: #8b949e; padding: 8px;")
        activity_content_layout.addWidget(self.activity_list)
        activity_content_layout.addStretch()
        
        activity_scroll.setWidget(activity_content)
        activity_layout.addWidget(activity_scroll)

        layout.addWidget(activity_group, 1)

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
        self.distro_table.setStyleSheet(table_style)

    def _init_connections(self):
        self.refresh_btn.clicked.connect(self._refresh_list)
        self.shutdown_all_btn.clicked.connect(self._shutdown_all)
        self.import_btn.clicked.connect(self._import_distro)
        self.create_btn.clicked.connect(self._create_distro)
        self.export_btn.clicked.connect(self._export_distro)
        self.send_msg_btn.clicked.connect(self._send_message)
        self.view_log_btn.clicked.connect(self._show_log_panel)
        self.edit_config_btn.clicked.connect(self._show_config_panel)

    def _refresh_status(self):
        self._refresh_distro_list()
        self._update_stats()



    def _update_stats(self):
        distros = self._wsl_manager.list_distros()
        running = sum(1 for d in distros if d.is_running)
        
        self.distro_count_card.set_value(str(len(distros)))
        self.running_card.set_value(str(running))
        self.config_card.set_value(str(len(distros)))

    def _refresh_distro_list(self):
        distros = self._wsl_manager.list_distros()
        self.distro_table.setRowCount(len(distros))

        for row, distro in enumerate(distros):
            bg_color = QColor("#161b22") if row % 2 == 0 else QColor("#21262d")
            
            name_item = QTableWidgetItem(distro.name)
            name_item.setData(Qt.ItemDataRole.UserRole, distro.name)
            name_item.setBackground(bg_color)
            version_item = QTableWidgetItem(f"WSL{distro.version}")
            version_item.setBackground(bg_color)
            status_item = QTableWidgetItem(distro.status.value)
            status_item.setBackground(bg_color)
            if distro.status == DistroStatus.RUNNING:
                status_item.setForeground(QColor("#3fb950"))
            else:
                status_item.setForeground(QColor("#f85149"))

            port_item = QTableWidgetItem("")
            port_item.setBackground(bg_color)
            
            kernel_item = QTableWidgetItem("")
            kernel_item.setBackground(bg_color)
            
            cpu_item = QTableWidgetItem("")
            cpu_item.setBackground(bg_color)
            
            memory_item = QTableWidgetItem("")
            memory_item.setBackground(bg_color)
            
            if distro.is_running:
                config = self._config_manager.get(distro.name)
                if config and config.gateway_port:
                    port_item.setText(str(config.gateway_port))
                    port_item.setForeground(QColor("#58a6ff"))
                
                kernel_version = self._wsl_manager.get_distro_kernel_version(distro.name)
                if kernel_version:
                    kernel_item.setText(kernel_version)
                
                resources = self._wsl_manager.get_resource_usage(distro.name)
                if resources:
                    cpu_item.setText(f"{resources.get('cpu_percent', 0):.1f}%")
                    if resources.get('memory_total_mb', 0) > 0:
                        memory_percent = (resources.get('memory_used_mb', 0) / resources.get('memory_total_mb', 1)) * 100
                        memory_item.setText(f"{memory_percent:.1f}%")

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(6)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            action_widget.setStyleSheet(f"background-color: {bg_color.name()};")

            distro_config = self._config_manager.get(distro.name)

            if distro.is_running:
                stop_btn = self._create_action_btn("⏹", f"停止分发: {distro.name}", "#da3633", "#f85149", "#b62324")
                stop_btn.clicked.connect(lambda checked, n=distro.name: self._stop_distro(n))
                action_layout.addWidget(stop_btn)

                terminal_btn = self._create_action_btn("💻", f"打开终端: {distro.name}")
                terminal_btn.clicked.connect(lambda checked, n=distro.name: self._open_terminal(n))
                action_layout.addWidget(terminal_btn)
                
                if distro_config and distro_config.windows_workspace:
                    workspace_btn = self._create_action_btn("📁", f"打开工作空间: {distro.name}")
                    workspace_btn.clicked.connect(lambda checked, n=distro.name, p=distro_config.windows_workspace: self._open_distro_workspace(n, p))
                    action_layout.addWidget(workspace_btn)
            else:
                start_btn = self._create_action_btn("▶", f"启动分发: {distro.name}", "#238636", "#2ea043", "#196c2e")
                start_btn.clicked.connect(lambda checked, n=distro.name: self._start_distro(n))
                action_layout.addWidget(start_btn)

            remove_btn = self._create_action_btn("🗑️", f"移除分发: {distro.name} (不删除虚拟磁盘)", hover_color="#da3633", pressed_color="#b62324")
            remove_btn.clicked.connect(lambda checked, n=distro.name: self._remove_distro(n))
            action_layout.addWidget(remove_btn)
            
            action_layout.addStretch()

            self.distro_table.setItem(row, 0, name_item)
            self.distro_table.setItem(row, 1, version_item)
            self.distro_table.setItem(row, 2, status_item)
            self.distro_table.setItem(row, 3, port_item)
            self.distro_table.setItem(row, 4, kernel_item)
            self.distro_table.setItem(row, 5, cpu_item)
            self.distro_table.setItem(row, 6, memory_item)
            self.distro_table.setCellWidget(row, 7, action_widget)

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

    def _start_distro(self, distro_name: str):
        success = self._wsl_manager.start_distro(distro_name)
        if success:
            self.distro_started.emit(distro_name)
            self.add_activity(f"WSL '{distro_name}' 已启动")
            self._refresh_status()
        else:
            QMessageBox.warning(self, "错误", f"无法启动分发: {distro_name}")

    def _stop_distro(self, distro_name: str):
        success = self._wsl_manager.stop_distro(distro_name)
        if success:
            self.distro_stopped.emit(distro_name)
            self.add_activity(f"WSL '{distro_name}' 已停止")
            self._refresh_status()
        else:
            QMessageBox.warning(self, "错误", f"无法停止分发: {distro_name}")

    def _remove_distro(self, distro_name: str):
        reply = QMessageBox.question(
            self, "确认",
            f"确定要移除分发 '{distro_name}' 吗？\n此操作将注销分发但不会删除虚拟磁盘。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success = self._wsl_manager.unregister_distro(distro_name)
            if success:
                self.add_activity(f"WSL '{distro_name}' 已移除")
                self._refresh_status()
            else:
                QMessageBox.warning(self, "错误", f"无法移除分发: {distro_name}")

    def _refresh_list(self):
        self._refresh_status()
        self.add_activity("WSL 列表已刷新")

    def _shutdown_all(self):
        reply = QMessageBox.question(
            self, "确认",
            "确定要关闭所有 WSL 分发吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._wsl_manager.shutdown_all()
            self.add_activity("已关闭所有 WSL 分发")
            self._refresh_status()

    def _open_terminal(self, distro_name: str):
        import os
        import glob
        
        wt_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe"),
        ]
        
        program_files_pattern = os.path.expandvars(
            r"%PROGRAMFILES%\WindowsApps\Microsoft.WindowsTerminal*\wt.exe"
        )
        wt_paths.extend(glob.glob(program_files_pattern))
        
        wt_exe = None
        for path in wt_paths:
            if os.path.exists(path):
                wt_exe = path
                break
        
        if wt_exe:
            try:
                subprocess.Popen([wt_exe, "wsl", "-d", distro_name])
                self.add_activity(f"已打开终端: {distro_name}")
                return
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法打开终端: {e}")
                return
        
        try:
            subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", "wsl", "-d", distro_name])
            self.add_activity(f"已打开终端: {distro_name}")
            
            QMessageBox.information(
                self, 
                "提示", 
                "建议安装 Windows Terminal 以获得更好的体验。\n\n"
                "可通过 Microsoft Store 搜索 'Windows Terminal' 安装。"
            )
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开终端: {e}")

    def _import_distro(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("导入 WSL 分发")
        dialog.setMinimumWidth(600)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #161b22;
            }
            QLabel {
                color: #c9d1d9;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #c9d1d9;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #58a6ff;
            }
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #c9d1d9;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #484f58;
            }
            QPushButton:pressed {
                background-color: #161b22;
            }
            QPushButton#primary {
                background-color: #238636;
                border-color: rgba(46, 160, 67, 0.4);
                color: #ffffff;
            }
            QPushButton#primary:hover {
                background-color: #2ea043;
                border-color: rgba(46, 160, 67, 0.8);
            }
            QPushButton#primary:pressed {
                background-color: #196c2e;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        tar_layout = QHBoxLayout()
        tar_layout.setSpacing(12)
        tar_layout.addWidget(QLabel("tar 文件:"))

        tar_edit = QLineEdit()
        tar_edit.setPlaceholderText("选择 .tar 文件...")
        tar_layout.addWidget(tar_edit, 1)

        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(lambda: self._browse_tar(tar_edit))
        tar_layout.addWidget(browse_btn)

        layout.addLayout(tar_layout)

        name_layout = QHBoxLayout()
        name_layout.setSpacing(12)
        name_layout.addWidget(QLabel("分发名称:"))

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("clawbot")
        name_layout.addWidget(name_edit, 1)

        name_hint_label = QLabel("")
        name_hint_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        name_layout.addWidget(name_hint_label)

        layout.addLayout(name_layout)

        dir_layout = QHBoxLayout()
        dir_layout.setSpacing(12)
        dir_layout.addWidget(QLabel("安装目录:"))

        dir_edit = QLineEdit()
        dir_edit.setPlaceholderText("选择存放 WSL 分发的目录...")
        dir_layout.addWidget(dir_edit, 1)

        browse_dir_btn = QPushButton("浏览")
        browse_dir_btn.clicked.connect(lambda: self._browse_install_dir(dir_edit))
        dir_layout.addWidget(browse_dir_btn)

        layout.addLayout(dir_layout)

        hint_label = QLabel("提示: 分发名称将从 tar 文件名自动推断，可手动修改\n安装目录可选，留空则使用默认位置")
        hint_label.setStyleSheet("color: #8b949e; font-size: 12px; line-height: 1.6;")
        layout.addWidget(hint_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        import_btn = QPushButton("导入")
        import_btn.setObjectName("primary")
        import_btn.setDefault(True)
        import_btn.setEnabled(False)
        btn_layout.addWidget(import_btn)

        layout.addLayout(btn_layout)

        last_auto_name = [""]
        tar_edit.textChanged.connect(lambda: self._auto_fill_distro_name(tar_edit.text(), name_edit, last_auto_name))

        def validate_name():
            name = name_edit.text().strip()
            if not name:
                name_hint_label.setText("")
                name_hint_label.setStyleSheet("color: #8b949e; font-size: 12px;")
                import_btn.setEnabled(False)
                return

            existing_distros = self._wsl_manager.list_distros()
            if any(d.name == name for d in existing_distros):
                name_hint_label.setText("⚠ 名称已存在")
                name_hint_label.setStyleSheet("color: #f85149; font-size: 12px;")
                import_btn.setEnabled(False)
            else:
                name_hint_label.setText("✓ 名称可用")
                name_hint_label.setStyleSheet("color: #3fb950; font-size: 12px;")
                import_btn.setEnabled(True)

        name_edit.textChanged.connect(validate_name)

        def do_import():
            tar_path = tar_edit.text().strip()
            distro_name = name_edit.text().strip()
            install_location = dir_edit.text().strip() or None

            if not tar_path:
                show_warning(self, "错误", "请选择 tar 文件")
                return

            if not distro_name:
                show_warning(self, "错误", "请输入分发名称")
                return

            dialog.close()
            self._do_import(tar_path, distro_name, install_location)

        import_btn.clicked.connect(do_import)
        dialog.exec()

    def _browse_tar(self, line_edit):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 tar 文件", "", "Tar Files (*.tar *.tar.gz *.tar.xz);;All Files (*)"
        )
        if file_path:
            line_edit.setText(file_path)

    def _browse_install_dir(self, line_edit):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择存放 WSL 分发的目录"
        )
        if dir_path:
            line_edit.setText(dir_path)

    def _auto_fill_distro_name(self, tar_path: str, name_edit: QLineEdit, last_auto_name: list):
        if tar_path:
            basename = os.path.basename(tar_path)
            name = basename.replace('.tar.gz', '').replace('.tgz', '').replace('.tar.xz', '').replace('.tar', '')
            name = name.lower().replace(' ', '-')
            if name_edit.text() == "" or name_edit.text() == last_auto_name[0]:
                name_edit.setText(name)
                last_auto_name[0] = name

    def _create_distro(self):
        """打开创建分发向导"""
        from ..dialogs.create_distro_wizard import CreateDistroWizard
        wizard = CreateDistroWizard(
            self._wsl_manager, 
            self._config_manager,
            self._nanobot_controller,
            self
        )
        wizard.distro_created.connect(self._on_distro_created)
        wizard.exec()

    def _on_distro_created(self, distro_name: str):
        """分发创建完成回调"""
        self.distro_imported.emit(distro_name)
        self.add_activity(f"WSL '{distro_name}' 创建成功")
        self._refresh_status()

    def _do_import(self, tar_path: str, distro_name: str, install_location: Optional[str] = None):
        existing_distros = self._wsl_manager.list_distros()
        if any(d.name == distro_name for d in existing_distros):
            reply = show_question(
                self, "确认",
                f"分发 '{distro_name}' 已存在。导入将覆盖现有分发，是否继续？",
                yes_text="继续", no_text="取消"
            )
            if not reply:
                return

        progress = ImportProgressDialog(self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        progress.start_animation()

        if not hasattr(self, '_import_callback_signal'):
            self._import_callback_signal = ThreadSafeSignal(self._on_import_complete)

        self._import_progress = progress
        self._import_distro_name = distro_name
        self._import_tar_path = tar_path
        self._import_install_location = install_location

        def run_import():
            result = self._wsl_manager.import_distro(tar_path, distro_name, install_location)
            self._import_callback_signal.emit(result)

        thread = threading.Thread(target=run_import, daemon=True)
        thread.start()

    def _on_import_complete(self, result):
        if not hasattr(self, '_import_progress'):
            return

        progress = self._import_progress
        distro_name = self._import_distro_name

        progress.stop_animation()
        progress.close()

        del self._import_progress
        del self._import_distro_name
        if hasattr(self, '_import_tar_path'):
            del self._import_tar_path
        if hasattr(self, '_import_install_location'):
            del self._import_install_location

        if result.success:
            message = f"WSL 分发 '{distro_name}' 导入成功！"
            if result.stdout:
                message += f"\n\n{result.stdout}"
            show_info(self, "成功", message)
            self.distro_imported.emit(distro_name)
            self.add_activity(f"WSL '{distro_name}' 导入成功")
            self._refresh_status()
        else:
            message = f"无法导入 WSL 分发:\n{result.stderr}"
            show_critical(self, "导入失败", message)

    def _on_wsl_state_changed(self, distros: dict):
        self._refresh_status()

    def _show_log_panel(self):
        self._navigate_to_panel(4)

    def _show_config_panel(self):
        self._navigate_to_panel(1)

    def _send_message(self):
        self._navigate_to_panel(3)

    def _open_distro_workspace(self, distro_name: str, workspace_path: str):
        """打开指定分发的工作空间"""
        if not workspace_path:
            QMessageBox.warning(self, "错误", f"分发 '{distro_name}' 未配置工作空间路径")
            return

        try:
            subprocess.Popen(["explorer", workspace_path])
            self.add_activity(f"打开工作空间 ({distro_name}): {workspace_path}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开目录: {e}")

    def _export_distro(self):
        """导出 WSL 分发"""
        distros = self._wsl_manager.list_distros()
        if not distros:
            show_warning(self, "错误", "没有可导出的 WSL 分发")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("导出 WSL 分发")
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #161b22;
            }
            QLabel {
                color: #c9d1d9;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #c9d1d9;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #58a6ff;
            }
            QComboBox {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #c9d1d9;
                font-size: 14px;
            }
            QComboBox:hover {
                border: 1px solid #484f58;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #c9d1d9;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #21262d;
                border: 1px solid #30363d;
                color: #c9d1d9;
                selection-background-color: #30363d;
            }
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #c9d1d9;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #484f58;
            }
            QPushButton:pressed {
                background-color: #161b22;
            }
            QPushButton#primary {
                background-color: #238636;
                border-color: rgba(46, 160, 67, 0.4);
                color: #ffffff;
            }
            QPushButton#primary:hover {
                background-color: #2ea043;
                border-color: rgba(46, 160, 67, 0.8);
            }
            QPushButton#primary:pressed {
                background-color: #196c2e;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        distro_layout = QHBoxLayout()
        distro_layout.setSpacing(12)
        distro_layout.addWidget(QLabel("选择分发:"))

        distro_combo = QComboBox()
        distro_combo.addItems([d.name for d in distros])
        distro_layout.addWidget(distro_combo, 1)

        layout.addLayout(distro_layout)

        dir_layout = QHBoxLayout()
        dir_layout.setSpacing(12)
        dir_layout.addWidget(QLabel("保存目录:"))

        dir_edit = QLineEdit()
        dir_edit.setPlaceholderText("选择 tar 文件保存目录...")
        dir_layout.addWidget(dir_edit, 1)

        browse_dir_btn = QPushButton("浏览")
        browse_dir_btn.clicked.connect(lambda: self._browse_export_dir(dir_edit))
        dir_layout.addWidget(browse_dir_btn)

        layout.addLayout(dir_layout)

        hint_label = QLabel("提示: 将导出为 tar 文件，可用于备份或迁移到其他机器")
        hint_label.setStyleSheet("color: #8b949e; font-size: 12px; line-height: 1.6;")
        layout.addWidget(hint_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        export_btn = QPushButton("导出")
        export_btn.setObjectName("primary")
        export_btn.setDefault(True)
        export_btn.setEnabled(False)
        btn_layout.addWidget(export_btn)

        layout.addLayout(btn_layout)

        def validate():
            dir_path = dir_edit.text().strip()
            export_btn.setEnabled(bool(dir_path))

        dir_edit.textChanged.connect(validate)

        def do_export():
            distro_name = distro_combo.currentText()
            save_dir = dir_edit.text().strip()

            if not save_dir:
                show_warning(self, "错误", "请选择保存目录")
                return

            dialog.close()
            self._do_export(distro_name, save_dir)

        export_btn.clicked.connect(do_export)
        dialog.exec()

    def _browse_export_dir(self, line_edit):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择 tar 文件保存目录"
        )
        if dir_path:
            line_edit.setText(dir_path)

    def _do_export(self, distro_name: str, save_dir: str):
        """执行导出操作"""
        import datetime
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        tar_filename = f"{distro_name}_{timestamp}.tar"
        output_path = os.path.join(save_dir, tar_filename)

        progress = ExportProgressDialog(self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        progress.start_animation()

        if not hasattr(self, '_export_callback_signal'):
            self._export_callback_signal = ThreadSafeSignal(self._on_export_complete)

        self._export_progress = progress
        self._export_distro_name = distro_name
        self._export_output_path = output_path

        def run_export():
            result = self._wsl_manager.export_distro(distro_name, output_path)
            self._export_callback_signal.emit(result)

        thread = threading.Thread(target=run_export, daemon=True)
        thread.start()

    def _on_export_complete(self, result):
        if not hasattr(self, '_export_progress'):
            return

        progress = self._export_progress
        distro_name = self._export_distro_name
        output_path = self._export_output_path

        progress.stop_animation(output_path if result.success else "")

        if result.success:
            self.add_activity(f"WSL '{distro_name}' 导出成功: {output_path}")
            QTimer.singleShot(1500, progress.close)
            self._refresh_status()
        else:
            show_critical(self, "导出失败", f"无法导出 WSL 分发:\n{result.stderr}")
            progress.close()

        del self._export_progress
        del self._export_distro_name
        del self._export_output_path

    def _navigate_to_panel(self, index: int):
        parent = self.parent()
        while parent:
            if hasattr(parent, 'content_stack'):
                parent.content_stack.setCurrentIndex(index)
                return
            if hasattr(parent, 'setCurrentIndex'):
                parent.setCurrentIndex(index)
                return
            parent = parent.parent()

    def add_activity(self, message: str):
        current = self.activity_list.text()
        if current == "暂无活动记录":
            current = ""
        timestamp = time.strftime("%H:%M:%S")
        new_activity = f"• {timestamp}: {message}"
        self.activity_list.setText(new_activity + "\n" + current)
        self.activity_list.setStyleSheet("color: #c9d1d9; padding: 8px;")
    
    def update_system_resources(self, cpu_usage: float, mem_usage: int, mem_total: int):
        """更新系统资源使用情况
        
        Args:
            cpu_usage: CPU 使用率百分比
            mem_usage: 已使用内存 (字节)
            mem_total: 总内存 (字节)
        """
        self.cpu_card.set_value(f"{cpu_usage:.1f}%")
        
        if mem_total > 0:
            mem_mb = mem_usage / (1024 * 1024)
            mem_total_mb = mem_total / (1024 * 1024)
            self.memory_card.set_value(f"{mem_mb:.0f}MB")
    
    def update_wsl_status(self, distro_name: str, is_running: bool):
        """更新 WSL 分发状态
        
        Args:
            distro_name: 分发名称
            is_running: 是否正在运行
        """
        self._refresh_distro_list()
