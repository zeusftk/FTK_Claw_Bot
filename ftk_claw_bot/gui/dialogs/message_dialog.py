from PyQt6.QtWidgets import (
    QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QFont


class CustomMessageDialog(QDialog):
    """自定义美化对话框，防止假死和误点击"""
    
    def __init__(self, icon_type, title, message, parent=None):
        super().__init__(parent)
        self._icon_type = icon_type
        self._title = title
        self._message = message
        self._result = QMessageBox.StandardButton.NoButton
        self._buttons = []
        self._can_close = False
        
        self._init_ui()
        self._apply_style()
    
    def _init_ui(self):
        self.setWindowTitle(self._title)
        self.setMinimumWidth(450)
        self.setMaximumWidth(600)
        
        # 设置窗口标志 - 保持在最上层，但允许用户交互
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.WindowTitleHint | 
            Qt.WindowType.WindowCloseButtonHint
        )
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # 内容区域
        content_frame = QFrame()
        content_layout = QHBoxLayout(content_frame)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 图标
        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setStyleSheet(self._get_icon_style())
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(icon_label)
        
        # 消息
        message_label = QLabel(self._message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 14px;
                line-height: 1.6;
            }
        """)
        message_label.setTextFormat(Qt.TextFormat.PlainText)
        content_layout.addWidget(message_label, 1)
        
        layout.addWidget(content_frame)
        
        # 按钮区域
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setSpacing(12)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addStretch()
        
        layout.addWidget(button_frame)
        self._button_layout = button_layout
    
    def _get_icon_style(self) -> str:
        """获取图标样式"""
        icon_colors = {
            QMessageBox.Icon.Information: "#007acc",
            QMessageBox.Icon.Warning: "#f0a020",
            QMessageBox.Icon.Question: "#007acc",
            QMessageBox.Icon.Critical: "#d13438",
        }
        color = icon_colors.get(self._icon_type, "#007acc")
        
        return f"""
            QLabel {{
                background-color: {color};
                border-radius: 24px;
                font-size: 24px;
                font-weight: bold;
                color: white;
            }}
        """
    
    def _apply_style(self):
        """应用样式"""
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d30;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
            }
        """)
    
    def add_button(self, text, button_role, is_default=False):
        """添加按钮"""
        btn = QPushButton(text)
        btn.setMinimumWidth(100)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if is_default:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #0e639c;
                    color: white;
                    border: none;
                    padding: 8px 24px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1177bb;
                }
                QPushButton:pressed {
                    background-color: #0d5a8a;
                }
            """)
            btn.setDefault(True)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3c3c3c;
                    color: #cccccc;
                    border: none;
                    padding: 8px 24px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #4c4c4c;
                }
                QPushButton:pressed {
                    background-color: #2c2c2c;
                }
            """)
        
        btn.clicked.connect(lambda: self._on_button_clicked(button_role))
        self._button_layout.addWidget(btn)
        self._buttons.append((btn, button_role))
    
    def _on_button_clicked(self, button_role):
        """按钮点击处理"""
        self._result = button_role
        self._can_close = True
        self.accept()
    
    def showEvent(self, event):
        """显示事件 - 延迟设置可关闭，防止误点击"""
        super().showEvent(event)
        QTimer.singleShot(200, self._enable_buttons)
    
    def _enable_buttons(self):
        """启用按钮，延迟防止误点击"""
        for btn, _ in self._buttons:
            btn.setEnabled(True)
    
    def closeEvent(self, event):
        """关闭事件 - 防止意外关闭"""
        if self._can_close:
            event.accept()
        else:
            event.ignore()
    
    def get_result(self) -> QMessageBox.StandardButton:
        """获取点击结果"""
        return self._result


def show_info(parent, title, message):
    """显示信息对话框"""
    dlg = CustomMessageDialog(QMessageBox.Icon.Information, title, message, parent)
    dlg.add_button("确定", QMessageBox.StandardButton.Ok, is_default=True)
    dlg.exec()
    return dlg.get_result()


def show_warning(parent, title, message):
    """显示警告对话框"""
    dlg = CustomMessageDialog(QMessageBox.Icon.Warning, title, message, parent)
    dlg.add_button("确定", QMessageBox.StandardButton.Ok, is_default=True)
    dlg.exec()
    return dlg.get_result()


def show_critical(parent, title, message):
    """显示错误对话框"""
    dlg = CustomMessageDialog(QMessageBox.Icon.Critical, title, message, parent)
    dlg.add_button("确定", QMessageBox.StandardButton.Ok, is_default=True)
    dlg.exec()
    return dlg.get_result()


def show_question(parent, title, message, yes_text="是", no_text="否"):
    """显示确认对话框"""
    dlg = CustomMessageDialog(QMessageBox.Icon.Question, title, message, parent)
    dlg.add_button(no_text, QMessageBox.StandardButton.No)
    dlg.add_button(yes_text, QMessageBox.StandardButton.Yes, is_default=True)
    dlg.exec()
    return dlg.get_result() == QMessageBox.StandardButton.Yes


def show_question_yes_no_cancel(parent, title, message, yes_text="是", no_text="否", cancel_text="取消"):
    """显示是/否/取消对话框"""
    dlg = CustomMessageDialog(QMessageBox.Icon.Question, title, message, parent)
    dlg.add_button(cancel_text, QMessageBox.StandardButton.Cancel)
    dlg.add_button(no_text, QMessageBox.StandardButton.No)
    dlg.add_button(yes_text, QMessageBox.StandardButton.Yes, is_default=True)
    dlg.exec()
    return dlg.get_result()
