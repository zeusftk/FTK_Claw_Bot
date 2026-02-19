"""
FreeLLM Client GUI 样式
深色主题
"""


def get_stylesheet() -> str:
    """获取样式表"""
    return """
    QMainWindow {
        background-color: #0d1117;
    }
    
    QWidget {
        color: #c9d1d9;
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-size: 13px;
    }
    
    QLabel#panelTitle {
        color: #f0f6fc;
        font-size: 18px;
        font-weight: bold;
    }
    
    QPushButton {
        background-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 8px;
        color: #c9d1d9;
        padding: 10px 20px;
        font-size: 13px;
        font-weight: 500;
    }
    
    QPushButton:hover {
        background-color: #30363d;
        border-color: #8b949e;
    }
    
    QPushButton:pressed {
        background-color: #161b22;
    }
    
    QPushButton:disabled {
        background-color: #161b22;
        color: #484f58;
        border-color: #21262d;
    }
    
    QPushButton#primaryButton {
        background-color: #238636;
        border: none;
        color: white;
        font-weight: 600;
    }
    
    QPushButton#primaryButton:hover {
        background-color: #2ea043;
    }
    
    QPushButton#primaryButton:disabled {
        background-color: #1a4d2e;
        color: #484f58;
    }
    
    QPushButton#smallButton {
        background-color: #21262d;
        border: 1px solid #30363d;
        padding: 6px 14px;
        font-size: 12px;
    }
    
    QPushButton#headerButton {
        background-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 8px;
        color: #c9d1d9;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 500;
        min-width: 70px;
    }
    
    QPushButton#headerButton:hover {
        background-color: #30363d;
        border-color: #8b949e;
    }
    
    QPushButton#headerButtonDanger {
        background-color: #da3633;
        border: none;
        border-radius: 8px;
        color: white;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 500;
        min-width: 70px;
    }
    
    QPushButton#headerButtonDanger:hover {
        background-color: #f85149;
    }
    
    QPushButton#dangerButton {
        background-color: #da3633;
        border: none;
        color: white;
        font-weight: 600;
    }
    
    QPushButton#dangerButton:hover {
        background-color: #f85149;
    }
    
    QSpinBox {
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 8px 12px;
        color: #c9d1d9;
        font-size: 13px;
    }
    
    QSpinBox:focus {
        border-color: #58a6ff;
    }
    
    QSpinBox::up-button, QSpinBox::down-button {
        background-color: #21262d;
        border: none;
        width: 20px;
    }
    
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
        background-color: #30363d;
    }
    
    QComboBox {
        background-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 8px 12px;
        color: #c9d1d9;
        font-size: 13px;
    }
    
    QComboBox:focus {
        border-color: #58a6ff;
    }
    
    QComboBox::drop-down {
        border: none;
        width: 24px;
    }
    
    QComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #8b949e;
    }
    
    QComboBox QAbstractItemView {
        background-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 8px;
        selection-background-color: #30363d;
        outline: none;
        padding: 4px;
    }
    
    QTableWidget {
        background-color: #0d1117;
        border: 1px solid #21262d;
        border-radius: 12px;
        gridline-color: #21262d;
        outline: none;
        padding: 4px;
    }
    
    QTableWidget::item {
        padding: 8px;
        border: none;
        border-bottom: 1px solid #21262d;
    }
    
    QTableWidget::item:selected {
        background-color: #21262d;
    }
    
    QTableWidget::item:hover {
        background-color: #161b22;
    }
    
    QHeaderView::section {
        background-color: #161b22;
        color: #8b949e;
        padding: 10px 8px;
        border: none;
        border-bottom: 1px solid #30363d;
        font-weight: 600;
        font-size: 12px;
    }
    
    QGroupBox {
        color: #f0f6fc;
        font-weight: 600;
        font-size: 14px;
        border: 1px solid #30363d;
        border-radius: 12px;
        margin-top: 12px;
        padding: 16px;
        padding-top: 24px;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 16px;
        top: 4px;
        padding: 0 8px;
        background-color: #0d1117;
    }
    
    QCheckBox {
        color: #c9d1d9;
        font-size: 13px;
        spacing: 8px;
    }
    
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 2px solid #30363d;
        background-color: #21262d;
    }
    
    QCheckBox::indicator:checked {
        background-color: #238636;
        border-color: #238636;
    }
    
    QCheckBox::indicator:hover {
        border-color: #8b949e;
    }
    
    QScrollBar:vertical {
        background-color: #161b22;
        width: 12px;
        border-radius: 6px;
        margin: 0;
    }
    
    QScrollBar::handle:vertical {
        background-color: #30363d;
        border-radius: 6px;
        min-height: 24px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #484f58;
    }
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0;
    }
    
    QScrollBar:horizontal {
        background-color: #161b22;
        height: 12px;
        border-radius: 6px;
        margin: 0;
    }
    
    QScrollBar::handle:horizontal {
        background-color: #30363d;
        border-radius: 6px;
        min-width: 24px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background-color: #484f58;
    }
    
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {
        width: 0;
    }
    
    QToolTip {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 12px;
    }
    
    QMenu {
        background-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 4px;
    }
    
    QMenu::item {
        padding: 8px 24px;
        border-radius: 4px;
    }
    
    QMenu::item:selected {
        background-color: #30363d;
    }
    
    QMenu::separator {
        height: 1px;
        background-color: #30363d;
        margin: 4px 8px;
    }
    """
