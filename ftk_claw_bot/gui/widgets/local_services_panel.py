# -*- coding: utf-8 -*-
import time
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSpinBox, QFileDialog, QProgressBar, QScrollArea,
    QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QCursor

from loguru import logger

from ...services import ServiceRegistry, ServiceStatus
from ...utils import tr


def get_windows_host_ip() -> str:
    """获取 WSL vEthernet 适配器 IP"""
    import subprocess
    
    try:
        result = subprocess.run(
            ["ipconfig"],
            capture_output=True,
            text=True,
            encoding="gbk",
            errors="ignore"
        )
        output = result.stdout
        lines = output.split('\n')
        
        in_wsl_section = False
        wsl_ip = None
        
        for line in lines:
            if 'vEthernet (WSL)' in line or 'vEthernet (WSL2)' in line:
                in_wsl_section = True
            elif in_wsl_section:
                if 'IPv4 Address' in line or 'IPv4 地址' in line:
                    ip = line.split(':')[-1].strip()
                    if ip:
                        if ip.startswith('169.254'):
                            wsl_ip = ip
                        else:
                            return ip
                elif 'adapter' in line.lower() or '适配器' in line:
                    in_wsl_section = False
        
        if wsl_ip:
            return wsl_ip
        
        return "localhost"
    except:
        return "localhost"


class ClickableURLLabel(QLabel):
    """可点击的 URL 标签，点击复制到剪贴板"""
    
    def __init__(self, url: str = ""):
        super().__init__()
        self._url = url
        self.setStyleSheet("color: #5bc0de;")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(tr("local_services.click_to_copy", "点击复制到剪贴板"))
    
    def set_url(self, url: str):
        self._url = url
        self.setText(f"🔗 {url}")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._url:
            clipboard = QApplication.clipboard()
            clipboard.setText(self._url)
            self.setStyleSheet("color: #7dd3fc;")
            QTimer.singleShot(200, lambda: self.setStyleSheet("color: #5bc0de;"))


class ServiceStartWorker(QThread):
    """服务启动工作线程"""
    status_changed = pyqtSignal(str, str, str)
    
    def __init__(self, service):
        super().__init__()
        self._service = service
    
    def run(self):
        if not self._service.start():
            info = self._service.get_status()
            self.status_changed.emit(self._service.id, "error", info.error or "启动失败")
            return
        
        for _ in range(60):
            if self._service.check_started():
                self.status_changed.emit(self._service.id, "running", "")
                return
            time.sleep(1)
        
        info = self._service.get_status()
        self.status_changed.emit(self._service.id, "error", info.error or "启动超时")


class UpgradeWorker(QThread):
    progress = pyqtSignal(str, int, int, str)
    finished = pyqtSignal(dict)
    
    def __init__(self, upgrader, whl_path, distro_names):
        super().__init__()
        self._upgrader = upgrader
        self._whl_path = whl_path
        self._distro_names = distro_names
    
    def run(self):
        results = self._upgrader.upgrade_all(
            self._whl_path,
            self._distro_names,
            progress_callback=self._on_progress
        )
        self.finished.emit(results)
    
    def _on_progress(self, distro_name, current, total, status):
        self.progress.emit(distro_name, current, total, status)


class LocalServicesPanel(QWidget):
    def __init__(self, wsl_manager=None, parent=None):
        super().__init__(parent)
        self._wsl_manager = wsl_manager
        self._status_labels = {}
        self._url_labels = {}
        self._upgrade_worker = None
        self._start_workers = {}
        self._port_spinbox = None
        self._whl_edit = None
        self._progress_bar = None
        self._upgrade_status = None
        self._upgrade_btn = None
        self._status_timer = None
        
        self._init_ui()
        self._setup_wsl_manager()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: #1e1e1e; border: none; }")
        
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_content.setStyleSheet("background-color: #1e1e1e;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)
        
        services = ServiceRegistry.get_all()
        for i, service in enumerate(services):
            if i > 0:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setStyleSheet("background-color: #3c3c3c;")
                line.setFixedHeight(1)
                scroll_layout.addWidget(line)
            
            if service.id == "embedding":
                card = self._create_embedding_card(service)
            elif service.id == "clawbot_upgrader":
                card = self._create_upgrader_card(service)
            else:
                card = self._create_service_card(service)
            scroll_layout.addWidget(card)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
    
    def _create_embedding_card(self, service) -> QFrame:
        card = QFrame()
        card.setObjectName("serviceCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        main_layout = QVBoxLayout(card)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(18, 14, 18, 14)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        title = QLabel(f"🔧 {service.name}")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)
        
        desc = QLabel(service.description)
        desc.setStyleSheet("font-size: 12px; color: #9d9d9d;")
        header_layout.addWidget(desc)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)
        
        port_label = QLabel(tr("local_services.port", "端口:"))
        port_label.setStyleSheet("color: #cccccc;")
        controls_layout.addWidget(port_label)
        
        self._port_spinbox = QSpinBox()
        self._port_spinbox.setRange(1024, 65535)
        self._port_spinbox.setValue(service.get_config().get("port", 18765))
        self._port_spinbox.valueChanged.connect(lambda v: service.set_config({"port": v}))
        self._port_spinbox.setStyleSheet("""
            QSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #5c5c5c;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 80px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
            }
        """)
        controls_layout.addWidget(self._port_spinbox)
        
        self._status_labels[service.id] = QLabel()
        self._status_labels[service.id].setMinimumWidth(100)
        controls_layout.addWidget(self._status_labels[service.id])
        
        self._url_labels[service.id] = ClickableURLLabel()
        self._url_labels[service.id].setVisible(False)
        controls_layout.addWidget(self._url_labels[service.id])
        
        controls_layout.addStretch()
        
        start_btn = QPushButton(tr("local_services.start", "启动"))
        stop_btn = QPushButton(tr("local_services.stop", "停止"))
        start_btn.clicked.connect(lambda: self._start_service(service.id))
        stop_btn.clicked.connect(lambda: self._stop_service(service.id))
        controls_layout.addWidget(start_btn)
        controls_layout.addWidget(stop_btn)
        
        main_layout.addLayout(controls_layout)
        
        self._update_service_status(service)
        return card
    
    def _create_upgrader_card(self, service) -> QFrame:
        card = QFrame()
        card.setObjectName("serviceCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        main_layout = QVBoxLayout(card)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(18, 14, 18, 14)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        title = QLabel(f"⬆️ {service.name}")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)
        
        desc = QLabel(service.description)
        desc.setStyleSheet("font-size: 12px; color: #9d9d9d;")
        header_layout.addWidget(desc)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        
        self._whl_edit = QLabel(tr("local_services.select_whl", "未选择文件"))
        self._whl_edit.setStyleSheet(
            "color: #b0b0b0; padding: 6px 12px; background: #3c3c3c; border-radius: 4px;"
        )
        self._whl_edit.setMinimumWidth(280)
        action_layout.addWidget(self._whl_edit)
        
        select_btn = QPushButton(tr("local_services.browse", "浏览..."))
        select_btn.clicked.connect(self._select_whl_file)
        action_layout.addWidget(select_btn)
        
        self._upgrade_btn = QPushButton(tr("local_services.upgrade_all", "一键升级所有在线 WSL"))
        self._upgrade_btn.clicked.connect(self._start_upgrade)
        action_layout.addWidget(self._upgrade_btn)
        
        action_layout.addStretch()
        main_layout.addLayout(action_layout)
        
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(10)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setMaximumWidth(180)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3c3c3c;
                border: none;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #0e639c;
                border-radius: 4px;
            }
        """)
        progress_layout.addWidget(self._progress_bar)
        
        self._upgrade_status = QLabel()
        self._upgrade_status.setStyleSheet("color: #9d9d9d;")
        progress_layout.addWidget(self._upgrade_status)
        progress_layout.addStretch()
        
        main_layout.addLayout(progress_layout)
        
        return card
    
    def _create_service_card(self, service) -> QFrame:
        card = QFrame()
        card.setObjectName("serviceCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        main_layout = QVBoxLayout(card)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(18, 14, 18, 14)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        title = QLabel(f"⚙️ {service.name}")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)
        
        desc = QLabel(service.description)
        desc.setStyleSheet("font-size: 12px; color: #9d9d9d;")
        header_layout.addWidget(desc)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)
        
        self._status_labels[service.id] = QLabel()
        self._status_labels[service.id].setMinimumWidth(100)
        controls_layout.addWidget(self._status_labels[service.id])
        
        controls_layout.addStretch()
        
        start_btn = QPushButton(tr("local_services.start", "启动"))
        stop_btn = QPushButton(tr("local_services.stop", "停止"))
        start_btn.clicked.connect(lambda: self._start_service(service.id))
        stop_btn.clicked.connect(lambda: self._stop_service(service.id))
        controls_layout.addWidget(start_btn)
        controls_layout.addWidget(stop_btn)
        
        main_layout.addLayout(controls_layout)
        
        self._update_service_status(service)
        return card
    
    def _setup_wsl_manager(self):
        upgrader = ServiceRegistry.get("clawbot_upgrader")
        if upgrader and hasattr(upgrader, 'set_wsl_manager'):
            upgrader.set_wsl_manager(self._wsl_manager)
    
    def _update_service_status(self, service):
        info = service.get_status()
        label = self._status_labels.get(service.id)
        url_label = self._url_labels.get(service.id)
        
        if label:
            status_config = {
                ServiceStatus.STOPPED: ("● " + tr("local_services.status_stopped", "已停止"), "#f0ad4e"),
                ServiceStatus.STARTING: ("● " + tr("local_services.status_starting", "启动中..."), "#5bc0de"),
                ServiceStatus.RUNNING: ("● " + tr("local_services.status_running", "运行中"), "#5cb85c"),
                ServiceStatus.ERROR: ("● " + tr("local_services.status_error", "错误"), "#d9534f"),
            }
            
            text, color = status_config.get(info.status, (str(info.status), "#cccccc"))
            
            if info.error:
                text += f" - {info.error}"
            
            label.setText(text)
            label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
        if url_label:
            if info.status == ServiceStatus.RUNNING and info.port:
                host_ip = get_windows_host_ip()
                url = f"http://{host_ip}:{info.port}"
                url_label.set_url(url)
                url_label.setVisible(True)
            else:
                url_label.setVisible(False)
    
    def _start_service(self, service_id: str):
        service = ServiceRegistry.get(service_id)
        if not service:
            return
        
        if service_id in self._start_workers:
            return
        
        worker = ServiceStartWorker(service)
        worker.status_changed.connect(self._on_service_status_changed)
        worker.finished.connect(lambda: self._cleanup_worker(service_id))
        worker.start()
        
        self._start_workers[service_id] = worker
    
    def _on_service_status_changed(self, service_id: str, status: str, error: str):
        service = ServiceRegistry.get(service_id)
        if service:
            if status == "running":
                service._status = ServiceStatus.RUNNING
            elif status == "error":
                service._status = ServiceStatus.ERROR
                service._error = error
            self._update_service_status(service)
    
    def _cleanup_worker(self, service_id: str):
        if service_id in self._start_workers:
            del self._start_workers[service_id]
    
    def _stop_service(self, service_id: str):
        service = ServiceRegistry.get(service_id)
        if service:
            service.stop()
            self._update_service_status(service)
    
    def _select_whl_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("local_services.select_whl_dialog", "选择 clawbot wheel 文件"),
            "",
            "Wheel Files (*.whl);;All Files (*)"
        )
        if file_path:
            self._whl_edit.setText(file_path)
            self._whl_edit.setToolTip(file_path)
    
    def _start_upgrade(self):
        whl_path = self._whl_edit.text()
        if not whl_path or whl_path == tr("local_services.select_whl", "未选择文件"):
            self._upgrade_status.setText(
                tr("local_services.please_select_whl", "请先选择 wheel 文件")
            )
            return
        
        distros = self._wsl_manager.list_distros()
        running_distros = [d.name for d in distros if d.is_running]
        
        if not running_distros:
            self._upgrade_status.setText(
                tr("local_services.no_running_distros", "没有在线的 WSL 分发")
            )
            return
        
        upgrader = ServiceRegistry.get("clawbot_upgrader")
        if not upgrader:
            return
        
        self._upgrade_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setMaximum(len(running_distros))
        self._progress_bar.setValue(0)
        
        self._upgrade_worker = UpgradeWorker(upgrader, whl_path, running_distros)
        self._upgrade_worker.progress.connect(self._on_upgrade_progress)
        self._upgrade_worker.finished.connect(self._on_upgrade_finished)
        self._upgrade_worker.start()
    
    def _on_upgrade_progress(self, distro_name: str, current: int, total: int, status: str):
        self._progress_bar.setValue(current)
        status_text = tr(
            f"local_services.upgrading_{status}",
            f"{distro_name}: {status}"
        )
        self._upgrade_status.setText(f"[{current}/{total}] {status_text}")
    
    def _on_upgrade_finished(self, results: dict):
        self._upgrade_btn.setEnabled(True)
        
        success_count = sum(1 for s, _ in results.values() if s)
        total_count = len(results)
        
        self._upgrade_status.setText(
            tr("local_services.upgrade_complete", 
               f"升级完成: {success_count}/{total_count} 成功")
        )
        logger.info(f"批量升级完成: {success_count}/{total_count} 成功")
    
    def auto_start_embedding(self):
        """自动启动 Embedding 服务"""
        self._start_service("embedding")
    
    def start_status_monitor(self):
        """启动状态监控定时器"""
        if self._status_timer is None:
            self._status_timer = QTimer(self)
            self._status_timer.timeout.connect(self._monitor_services)
        self._status_timer.start(5000)
    
    def _monitor_services(self):
        """监控服务状态"""
        for service in ServiceRegistry.get_all():
            if service.id == "embedding":
                if service._status == ServiceStatus.STARTING:
                    if service.check_started():
                        self._update_service_status(service)
                elif service._status == ServiceStatus.RUNNING:
                    if not service._health_check():
                        service._status = ServiceStatus.ERROR
                        service._error = "服务无响应"
                        self._update_service_status(service)
    
    def stop_status_monitor(self):
        """停止状态监控"""
        if self._status_timer:
            self._status_timer.stop()
    
    def showEvent(self, event):
        super().showEvent(event)
        self.start_status_monitor()
    
    def hideEvent(self, event):
        self.stop_status_monitor()
        super().hideEvent(event)
