"""
FreeLLM 服务管理面板
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QSpinBox, QCheckBox, QTextEdit, QGroupBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont, QColor
from datetime import datetime
from typing import Optional, List, Dict, TYPE_CHECKING

from .styles import get_stylesheet

if TYPE_CHECKING:
    from ..service_manager import ServiceManager, ServiceInstanceState
    from .simple_wsl_manager import WSLDistroInfo


class ServiceWorker(QThread):
    """后台服务操作线程"""
    
    started_signal = pyqtSignal(str, bool, str, str)
    stopped_signal = pyqtSignal(str, bool)
    all_stopped_signal = pyqtSignal()
    
    def __init__(self, service_manager: "ServiceManager", parent=None):
        super().__init__(parent)
        self._service_manager = service_manager
        self._pending_tasks = []
        self._running = True
    
    def queue_start(self, distro_name: str):
        """队列启动任务"""
        self._pending_tasks.append(("start", distro_name))
        if not self.isRunning():
            self.start()
    
    def queue_stop(self, distro_name: str):
        """队列停止任务"""
        self._pending_tasks.append(("stop", distro_name))
        if not self.isRunning():
            self.start()
    
    def queue_stop_all(self):
        """队列停止所有任务"""
        self._pending_tasks.append(("stop_all", None))
        if not self.isRunning():
            self.start()
    
    def run(self):
        while self._running:
            task = None
            if self._pending_tasks:
                task = self._pending_tasks.pop(0)
            
            if task is None:
                break
            
            action, distro_name = task
            
            if action == "start":
                state = self._service_manager.start_service(distro_name)
                success = state.llm_status.value == "running" and state.router_status.value == "running"
                self.started_signal.emit(
                    distro_name,
                    success,
                    state.llm_url or "",
                    state.error or ""
                )
            elif action == "stop":
                success = self._service_manager.stop_service(distro_name)
                self.stopped_signal.emit(distro_name, success)
            elif action == "stop_all":
                self._service_manager.stop_all_services()
                self.all_stopped_signal.emit()
    
    def stop(self):
        self._running = False
        self.wait()


class RefreshWorker(QThread):
    """后台刷新 WSL 分发列表线程"""
    
    finished_signal = pyqtSignal(list)
    
    def __init__(self, wsl_manager, parent=None):
        super().__init__(parent)
        self._wsl_manager = wsl_manager
    
    def run(self):
        distros = self._wsl_manager.list_distros()
        self.finished_signal.emit(distros)


class FreeLLMServicePanel(QWidget):
    """FreeLLM 服务管理面板"""
    
    service_started = pyqtSignal(str)
    service_stopped = pyqtSignal(str)
    
    def __init__(self, service_manager: "ServiceManager", parent=None):
        super().__init__(parent)
        self._service_manager = service_manager
        self._distros: List["WSLDistroInfo"] = []
        self._selected_distro: Optional[str] = None
        
        self._worker = ServiceWorker(service_manager)
        self._worker.started_signal.connect(self._on_service_started)
        self._worker.stopped_signal.connect(self._on_service_stopped)
        self._worker.all_stopped_signal.connect(self._on_all_stopped)
        
        self._init_ui()
        self._apply_styles()
        self._refresh_distros_async()
        
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(3000)
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        header_layout = QHBoxLayout()
        title = QLabel("FreeLLM 服务管理")
        title.setObjectName("panelTitle")
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.setObjectName("headerButton")
        self._refresh_btn.setFixedWidth(80)
        self._refresh_btn.clicked.connect(self._refresh_distros_async)
        header_layout.addWidget(self._refresh_btn)
        
        self._start_all_btn = QPushButton("全部启动")
        self._start_all_btn.setObjectName("headerButton")
        self._start_all_btn.setFixedWidth(80)
        self._start_all_btn.clicked.connect(self._start_all_services)
        header_layout.addWidget(self._start_all_btn)
        
        self._stop_all_btn = QPushButton("全部停止")
        self._stop_all_btn.setObjectName("headerButtonDanger")
        self._stop_all_btn.setFixedWidth(80)
        self._stop_all_btn.clicked.connect(self._stop_all_services)
        header_layout.addWidget(self._stop_all_btn)
        
        layout.addLayout(header_layout)
        
        layout.addWidget(self._create_service_list_group(), stretch=1)
        layout.addWidget(self._create_config_group())
    
    def _create_service_list_group(self) -> QGroupBox:
        group = QGroupBox("服务列表")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        
        self._service_table = QTableWidget()
        self._service_table.setColumnCount(5)
        self._service_table.setHorizontalHeaderLabels(
            ["WSL 分发", "LLM 端口", "Router 端口", "状态", "操作"]
        )
        self._service_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._service_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._service_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._service_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._service_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._service_table.setColumnWidth(1, 100)
        self._service_table.setColumnWidth(2, 100)
        self._service_table.setColumnWidth(3, 80)
        self._service_table.setColumnWidth(4, 80)
        self._service_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._service_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._service_table.verticalHeader().setVisible(False)
        self._service_table.verticalHeader().setDefaultSectionSize(36)
        self._service_table.clicked.connect(self._on_table_clicked)
        layout.addWidget(self._service_table)
        
        return group
    
    def _create_config_group(self) -> QGroupBox:
        group = QGroupBox("服务配置")
        layout = QHBoxLayout(group)
        layout.setSpacing(16)
        
        layout.addWidget(QLabel("WSL 分发:"))
        self._distro_combo = QComboBox()
        self._distro_combo.setMinimumWidth(120)
        self._distro_combo.currentTextChanged.connect(self._on_distro_selected)
        layout.addWidget(self._distro_combo)
        
        layout.addWidget(QLabel("LLM 端口:"))
        self._llm_port_spin = QSpinBox()
        self._llm_port_spin.setRange(20100, 20199)
        self._llm_port_spin.setValue(20100)
        self._llm_port_spin.setFixedWidth(120)
        layout.addWidget(self._llm_port_spin)
        
        layout.addWidget(QLabel("Router 端口:"))
        self._router_port_spin = QSpinBox()
        self._router_port_spin.setRange(20200, 20299)
        self._router_port_spin.setValue(20200)
        self._router_port_spin.setFixedWidth(120)
        layout.addWidget(self._router_port_spin)
        
        self._auto_start_check = QCheckBox("自动启动")
        layout.addWidget(self._auto_start_check)
        
        layout.addStretch()
        
        save_btn = QPushButton("保存配置")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_config)
        layout.addWidget(save_btn)
        
        return group
    
    def _apply_styles(self):
        self.setStyleSheet(get_stylesheet())
    
    def _refresh_distros_async(self):
        """异步刷新 WSL 分发列表"""
        from .simple_wsl_manager import SimpleWSLManager
        
        if hasattr(self._service_manager, '_wsl_manager'):
            wsl_manager = self._service_manager._wsl_manager
        else:
            wsl_manager = SimpleWSLManager()
        
        self._refresh_worker = RefreshWorker(wsl_manager)
        self._refresh_worker.finished_signal.connect(self._on_distros_refreshed)
        self._refresh_worker.start()
    
    def _on_distros_refreshed(self, distros):
        """WSL 分发列表刷新完成"""
        self._distros = distros
        
        self._distro_combo.clear()
        for distro in self._distros:
            self._distro_combo.addItem(distro.name)
        
        self._update_service_table()
    
    def _update_service_table(self):
        states = self._service_manager.get_all_states()
        
        self._service_table.setRowCount(len(self._distros))
        
        for row, distro in enumerate(self._distros):
            name_item = QTableWidgetItem(distro.name)
            name_item.setForeground(QColor("#c9d1d9"))
            self._service_table.setItem(row, 0, name_item)
            
            config = self._service_manager.get_config().get_instance(distro.name)
            
            llm_port_item = QTableWidgetItem(str(config.llm_port))
            llm_port_item.setForeground(QColor("#8b949e"))
            llm_port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._service_table.setItem(row, 1, llm_port_item)
            
            router_port_item = QTableWidgetItem(str(config.router_port))
            router_port_item.setForeground(QColor("#8b949e"))
            router_port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._service_table.setItem(row, 2, router_port_item)
            
            state = states.get(distro.name)
            if state:
                if state.llm_status.value == "running" and state.router_status.value == "running":
                    status_text = "● 运行中"
                    status_color = "#3fb950"
                elif state.llm_status.value == "error" or state.router_status.value == "error":
                    status_text = "● 错误"
                    status_color = "#f85149"
                else:
                    status_text = "○ 停止"
                    status_color = "#8b949e"
            else:
                status_text = "○ 停止"
                status_color = "#8b949e"
            
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(status_color))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._service_table.setItem(row, 3, status_item)
            
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(4)
            
            if state and state.llm_status.value == "running":
                action_btn = QPushButton("停止")
                action_btn.setObjectName("smallButton")
                action_btn.setProperty("distro_name", distro.name)
                action_btn.clicked.connect(lambda checked, name=distro.name: self._stop_service(name))
            else:
                action_btn = QPushButton("启动")
                action_btn.setObjectName("primaryButton")
                action_btn.setProperty("distro_name", distro.name)
                action_btn.clicked.connect(lambda checked, name=distro.name: self._start_service(name))
            
            action_btn.setFixedWidth(50)
            action_layout.addWidget(action_btn)
            
            self._service_table.setCellWidget(row, 4, action_widget)
    
    def _on_table_clicked(self, index):
        if index.column() == 0:
            distro_name = self._service_table.item(index.row(), 0).text()
            self._distro_combo.setCurrentText(distro_name)
    
    def _on_distro_selected(self, distro_name: str):
        if not distro_name:
            return
        
        config = self._service_manager.get_config().get_instance(distro_name)
        self._llm_port_spin.setValue(config.llm_port)
        self._router_port_spin.setValue(config.router_port)
        self._auto_start_check.setChecked(config.auto_start)
        self._selected_distro = distro_name
    
    def _start_service(self, distro_name: str):
        """异步启动服务"""
        self._worker.queue_start(distro_name)
    
    def _on_service_started(self, distro_name: str, success: bool, llm_url: str, error: str):
        """服务启动完成回调"""
        self._update_service_table()
    
    def _stop_service(self, distro_name: str):
        """异步停止服务"""
        self._worker.queue_stop(distro_name)
    
    def _on_service_stopped(self, distro_name: str, success: bool):
        """服务停止完成回调"""
        self._update_service_table()
    
    def _start_all_services(self):
        """异步启动所有服务"""
        for distro in self._distros:
            self._worker.queue_start(distro.name)
    
    def _stop_all_services(self):
        """异步停止所有服务"""
        self._worker.queue_stop_all()
    
    def _on_all_stopped(self):
        """所有服务停止完成回调"""
        self._update_service_table()
    
    def _save_config(self):
        distro_name = self._distro_combo.currentText()
        if not distro_name:
            return
        
        self._service_manager.update_instance_config(
            distro_name,
            llm_port=self._llm_port_spin.value(),
            router_port=self._router_port_spin.value(),
            auto_start=self._auto_start_check.isChecked()
        )
        
        self._update_service_table()
    
    def _update_status(self):
        self._update_service_table()
    
    def cleanup(self):
        self._status_timer.stop()
        self._worker.stop()
