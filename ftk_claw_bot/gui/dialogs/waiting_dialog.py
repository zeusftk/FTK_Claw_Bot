from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class WaitingDialog(QDialog):
    operation_completed = pyqtSignal(bool, str)
    
    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self._result_success = False
        self._result_message = ""
        self._init_ui(title, message)
        
    def _init_ui(self, title: str, message: str):
        self.setWindowTitle(title)
        self.setFixedSize(400, 150)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet("""
            QDialog {
                background-color: #161b22;
            }
            QLabel {
                color: #c9d1d9;
            }
            QProgressBar {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 4px;
                text-align: center;
                color: #c9d1d9;
            }
            QProgressBar::chunk {
                background-color: #238636;
                border-radius: 3px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        self.message_label = QLabel(message)
        font = QFont()
        font.setPointSize(12)
        self.message_label.setFont(font)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("正在处理...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(self.status_label)
    
    def update_message(self, message: str):
        self.message_label.setText(message)
    
    def update_status(self, status: str):
        self.status_label.setText(status)
    
    def set_result(self, success: bool, message: str):
        self._result_success = success
        self._result_message = message
        self.operation_completed.emit(success, message)
    
    def close_with_result(self, success: bool, message: str = ""):
        self._result_success = success
        self._result_message = message
        self.accept()
