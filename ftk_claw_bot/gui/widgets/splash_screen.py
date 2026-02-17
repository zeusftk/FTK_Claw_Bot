from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter


class SplashScreen(QWidget):
    """启动画面，显示初始化进度"""
    
    initialization_complete = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._init_ui()
        self._apply_styles()
        self._center_on_screen()
    
    def _center_on_screen(self):
        """将窗口居中显示"""
        from PyQt6.QtGui import QScreen
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def _init_ui(self):
        self.setFixedSize(500, 300)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        layout.addStretch()
        
        title_label = QLabel("FTK_Claw_Bot")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        subtitle_label = QLabel("WSL ClawBot 管理工具")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_label.setFont(subtitle_font)
        layout.addWidget(subtitle_label)
        
        layout.addStretch()
        
        self.status_label = QLabel("正在初始化...")
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
        
        version_label = QLabel("v0.1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_font = QFont()
        version_font.setPointSize(9)
        version_label.setFont(version_font)
        layout.addWidget(version_label)
    
    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget {
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
    
    def set_status(self, status: str, progress: int = None):
        """设置状态文本和进度
        
        Args:
            status: 状态文本
            progress: 进度值（0-100），None 表示不更新
        """
        self.status_label.setText(status)
        if progress is not None:
            self.progress_bar.setValue(progress)
        QApplication.processEvents()
