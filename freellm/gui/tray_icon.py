"""
FreeLLM 服务托盘图标
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSignal, QObject, Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont

class TrayIcon(QSystemTrayIcon):
    """系统托盘图标"""
    
    show_window_requested = pyqtSignal()
    start_all_requested = pyqtSignal()
    stop_all_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._create_icon()
        self._create_menu()
        
        self.activated.connect(self._on_activated)
    
    def _create_icon(self):
        """创建托盘图标"""
        
        
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(QColor("#238636"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 56, 56)
        
        painter.setPen(QColor("#ffffff"))
        font = QFont("Arial", 28, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "F")
        
        painter.end()
        
        self.setIcon(QIcon(pixmap))
        self.setToolTip("FreeLLM 服务管理")
    
    def _create_menu(self):
        """创建托盘菜单"""
        menu = QMenu()
        
        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self.show_window_requested.emit)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        self._start_all_action = QAction("启动所有服务", self)
        self._start_all_action.triggered.connect(self.start_all_requested.emit)
        menu.addAction(self._start_all_action)
        
        self._stop_all_action = QAction("停止所有服务", self)
        self._stop_all_action.triggered.connect(self.stop_all_requested.emit)
        menu.addAction(self._stop_all_action)
        
        menu.addSeparator()
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)
        
        self.setContextMenu(menu)
    
    def _on_activated(self, reason):
        """托盘图标激活"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window_requested.emit()
    
    def update_status(self, running_count: int, total_count: int):
        """更新状态显示"""
        if running_count == 0:
            status = "无服务运行"
        elif running_count == total_count:
            status = f"所有服务运行中 ({running_count})"
        else:
            status = f"{running_count}/{total_count} 服务运行中"
        
        self.setToolTip(f"FreeLLM 服务管理\n{status}")
        
        self._start_all_action.setEnabled(running_count < total_count)
        self._stop_all_action.setEnabled(running_count > 0)
