"""
FreeLLM 服务管理独立主窗口
"""

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication, QSystemTrayIcon
from PyQt6.QtCore import Qt, QTimer, QEvent
from typing import Optional, TYPE_CHECKING

from .styles import get_stylesheet
from .service_panel import FreeLLMServicePanel
from .simple_wsl_manager import SimpleWSLManager
from .tray_icon import TrayIcon

if TYPE_CHECKING:
    pass


class FreeLLMServiceWindow(QMainWindow):
    """FreeLLM 服务管理独立窗口"""
    
    def __init__(self, wsl_manager: Optional[SimpleWSLManager] = None, parent=None):
        super().__init__(parent)
        
        if wsl_manager is None:
            self._wsl_manager = SimpleWSLManager()
            self._owns_wsl_manager = True
        else:
            self._wsl_manager = wsl_manager
            self._owns_wsl_manager = False
        
        from ..service_manager import ServiceManager
        self._service_manager = ServiceManager(self._wsl_manager)
        
        self._init_ui()
        self._apply_styles()
        self._init_tray()
        
        self._service_manager.restore_auto_start_services()
    
    def _init_ui(self):
        self.setWindowTitle("FreeLLM 服务管理")
        self.setMinimumSize(900, 700)
        self.resize(1000, 750)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self._service_panel = FreeLLMServicePanel(self._service_manager)
        layout.addWidget(self._service_panel)
    
    def _apply_styles(self):
        self.setStyleSheet(get_stylesheet())
    
    def _init_tray(self):
        """初始化系统托盘"""
        self._tray_icon = TrayIcon(self)
        self._tray_icon.show_window_requested.connect(self._show_window)
        self._tray_icon.start_all_requested.connect(self._start_all_services)
        self._tray_icon.stop_all_requested.connect(self._stop_all_services)
        self._tray_icon.quit_requested.connect(self._quit_app)
        self._tray_icon.show()
        
        self._tray_timer = QTimer()
        self._tray_timer.timeout.connect(self._update_tray_status)
        self._tray_timer.start(3000)
    
    def _show_window(self):
        """显示窗口"""
        self.show()
        self.activateWindow()
        self.raise_()
    
    def _start_all_services(self):
        """启动所有服务"""
        self._service_panel._start_all_services()
    
    def _stop_all_services(self):
        """停止所有服务"""
        self._service_panel._stop_all_services()
    
    def _quit_app(self):
        """退出应用"""
        self._tray_timer.stop()
        self._service_panel.cleanup()
        self._service_manager.stop_all_services()
        self._tray_icon.hide()
        QApplication.quit()
    
    def _update_tray_status(self):
        """更新托盘状态"""
        states = self._service_manager.get_all_states()
        total = len(self._service_panel._distros)
        running = sum(
            1 for s in states.values() 
            if s.llm_status.value == "running"
        )
        self._tray_icon.update_status(running, total)
    
    def changeEvent(self, event):
        """窗口状态改变事件 - 最小化到托盘"""
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                event.ignore()
                self.hide()
                self._tray_icon.showMessage(
                    "FreeLLM 服务管理",
                    "程序已最小化到系统托盘，双击图标可重新打开窗口",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
                return
        super().changeEvent(event)
    
    def closeEvent(self, event):
        """关闭事件 - 直接退出"""
        event.accept()
        self._quit_app()
    
    def cleanup(self):
        """清理资源"""
        self._tray_timer.stop()
        self._service_panel.cleanup()
