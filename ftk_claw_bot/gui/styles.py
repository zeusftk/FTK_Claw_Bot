# -*- coding: utf-8 -*-
"""
FTK_Claw_Bot 统一样式主题
Modern Dark Theme with High Contrast
"""

# 颜色方案 - 现代化深色主题
COLORS = {
    # 主背景色
    "bg_primary": "#0d1117",      # 更深的背景，GitHub Dark 风格
    "bg_secondary": "#161b22",    # 次级背景
    "bg_tertiary": "#21262d",     # 三级背景（卡片、面板）
    "bg_input": "#21262d",        # 输入框背景
    
    # 文字颜色 - 高对比度
    "text_primary": "#f0f6fc",    # 主文字 - 白色
    "text_secondary": "#c9d1d9",  # 次级文字 - 浅灰
    "text_muted": "#8b949e",      # 弱化文字 - 灰色
    "text_disabled": "#6e7681",   # 禁用文字
    
    # 边框颜色
    "border": "#30363d",          # 边框
    "border_hover": "#8b949e",    # 悬停边框
    
    # 强调色 - 蓝色系
    "accent": "#58a6ff",          # 主强调色
    "accent_hover": "#79c0ff",    # 悬停色
    "accent_active": "#388bfd",   # 激活色
    
    # 状态色
    "success": "#3fb950",         # 成功 - 绿色
    "warning": "#d29922",         # 警告 - 黄色
    "error": "#f85149",           # 错误 - 红色
    "info": "#58a6ff",            # 信息 - 蓝色
    
    # 按钮颜色
    "btn_primary": "#238636",     # 主按钮 - 绿色
    "btn_primary_hover": "#2ea043",
    "btn_secondary": "#21262d",   # 次级按钮
    "btn_secondary_hover": "#30363d",
    "btn_danger": "#da3633",      # 危险按钮
    "btn_danger_hover": "#f85149",
}

# 全局样式表 - 应用到整个应用
GLOBAL_STYLESHEET = """
/* 全局基础样式 */
QWidget {
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 13px;
}

/* 主窗口 */
QMainWindow {
    background-color: %(bg_primary)s;
}

/* 框架 */
QFrame {
    background-color: %(bg_primary)s;
    border: none;
}

/* 标签 */
QLabel {
    color: %(text_secondary)s;
}

QLabel#panelTitle, QLabel#navTitle, QLabel#configTitle, QLabel#skillTitle {
    color: %(text_primary)s;
    font-size: 18px;
    font-weight: bold;
}

QLabel#navTitleMain {
    color: %(accent)s;
    font-size: 22px;
    font-weight: bold;
}

QLabel#navTitleSub {
    color: %(text_muted)s;
    font-size: 11px;
}

QLabel#cardTitle {
    color: %(text_primary)s;
    font-size: 14px;
    font-weight: bold;
}

QLabel#statusLabel {
    color: %(text_secondary)s;
    font-size: 12px;
}

QLabel#infoLabel {
    color: %(text_muted)s;
    font-size: 11px;
}

QLabel#versionLabel {
    color: %(text_muted)s;
    padding: 10px 0px;
}

/* 按钮 */
QPushButton {
    background-color: %(btn_secondary)s;
    color: %(text_primary)s;
    border: 1px solid %(border)s;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: %(btn_secondary_hover)s;
    border-color: %(border_hover)s;
}

QPushButton:pressed {
    background-color: %(border)s;
}

QPushButton:disabled {
    background-color: %(bg_secondary)s;
    color: %(text_disabled)s;
    border-color: %(border)s;
}

QPushButton#primary {
    background-color: %(btn_primary)s;
    border-color: rgba(46, 160, 67, 0.4);
}

QPushButton#primary:hover {
    background-color: %(btn_primary_hover)s;
}

QPushButton#danger {
    background-color: %(btn_danger)s;
    border-color: rgba(248, 81, 73, 0.4);
}

QPushButton#danger:hover {
    background-color: %(btn_danger_hover)s;
}

/* 输入框 */
QLineEdit {
    background-color: %(bg_input)s;
    color: %(text_primary)s;
    border: 1px solid %(border)s;
    border-radius: 6px;
    padding: 8px 12px;
}

QLineEdit:focus {
    border: 2px solid %(accent)s;
    background-color: %(bg_primary)s;
}

QLineEdit:hover {
    border-color: %(border_hover)s;
}

QLineEdit:disabled {
    background-color: %(bg_secondary)s;
    color: %(text_disabled)s;
}

/* 下拉框 */
QComboBox {
    background-color: %(bg_input)s;
    color: %(text_primary)s;
    border: 1px solid %(border)s;
    border-radius: 6px;
    padding: 8px 12px;
    min-width: 100px;
}

QComboBox:hover {
    border-color: %(border_hover)s;
}

QComboBox:focus {
    border: 2px solid %(accent)s;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid %(text_secondary)s;
    width: 0;
    height: 0;
}

QComboBox QAbstractItemView {
    background-color: %(bg_secondary)s;
    color: %(text_primary)s;
    border: 1px solid %(border)s;
    border-radius: 6px;
    selection-background-color: %(accent)s;
    selection-color: %(bg_primary)s;
}

/* 文本编辑框 */
QTextEdit {
    background-color: %(bg_secondary)s;
    color: %(text_primary)s;
    border: 1px solid %(border)s;
    border-radius: 6px;
    padding: 8px;
}

QTextEdit:focus {
    border: 2px solid %(accent)s;
}

/* 复选框 */
QCheckBox {
    color: %(text_secondary)s;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid %(border)s;
    border-radius: 3px;
    background-color: %(bg_input)s;
}

QCheckBox::indicator:checked {
    background-color: %(accent)s;
    border-color: %(accent)s;
}

QCheckBox::indicator:hover {
    border-color: %(border_hover)s;
}

/* 分组框 */
QGroupBox {
    color: %(text_primary)s;
    font-weight: bold;
    border: 1px solid %(border)s;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    padding: 16px;
    background-color: %(bg_secondary)s;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: %(text_primary)s;
}

/* 统计卡片 */
QFrame#statCard {
    background-color: %(bg_tertiary)s;
    border: 1px solid %(border)s;
    border-radius: 8px;
}

QFrame#statCard:hover {
    border-color: %(accent)s;
    background-color: rgba(88, 166, 255, 0.1);
}

/* 导航列表 */
QListWidget#navList {
    background-color: transparent;
    border: none;
    outline: none;
}

QListWidget#navList::item {
    color: %(text_secondary)s;
    padding: 12px 16px;
    border-radius: 6px;
    margin: 2px 6px;
}

QListWidget#navList::item:selected {
    background-color: %(accent)s;
    color: %(text_primary)s;
}

QListWidget#navList::item:hover:!selected {
    background-color: %(bg_tertiary)s;
}

/* 普通列表 */
QListWidget {
    background-color: %(bg_secondary)s;
    color: %(text_secondary)s;
    border: 1px solid %(border)s;
    border-radius: 6px;
    outline: none;
}

QListWidget::item {
    padding: 10px 12px;
    border-radius: 4px;
}

QListWidget::item:selected {
    background-color: %(accent)s;
    color: %(bg_primary)s;
}

QListWidget::item:hover:!selected {
    background-color: %(bg_tertiary)s;
}

/* 表格 */
QTableWidget {
    background-color: %(bg_secondary)s;
    color: %(text_secondary)s;
    border: 1px solid %(border)s;
    border-radius: 8px;
    gridline-color: transparent;
    outline: none;
}

QTableWidget::item {
    padding: 12px 8px;
    border: none;
}

QTableWidget::item:selected {
    background-color: %(accent)s;
    color: %(bg_primary)s;
}

QTableWidget::item:hover {
    background-color: %(bg_tertiary)s;
}

QHeaderView::section {
    background-color: %(bg_tertiary)s;
    color: %(text_primary)s;
    padding: 14px 10px;
    border: none;
    border-bottom: 1px solid %(border)s;
    font-weight: bold;
    font-size: 13px;
}

QHeaderView::section:first {
    border-top-left-radius: 8px;
}

QHeaderView::section:last {
    border-top-right-radius: 8px;
}

/* 导航框架 */
QFrame#navFrame {
    background-color: %(bg_secondary)s;
    border-right: 1px solid %(border)s;
}

/* 状态栏 */
QStatusBar {
    background-color: %(bg_tertiary)s;
    color: %(text_primary)s;
    border-top: 1px solid %(border)s;
}

QStatusBar QLabel {
    color: %(text_secondary)s;
}

/* 进度条 */
QProgressBar {
    border: 1px solid %(border)s;
    border-radius: 4px;
    text-align: center;
    background-color: %(bg_secondary)s;
    color: %(text_primary)s;
}

QProgressBar::chunk {
    background-color: %(accent)s;
    border-radius: 3px;
}

/* 滚动条 */
QScrollBar:vertical {
    background-color: %(bg_secondary)s;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: %(border)s;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: %(border_hover)s;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: %(bg_secondary)s;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: %(border)s;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: %(border_hover)s;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* 标签页 */
QTabWidget::pane {
    background-color: %(bg_secondary)s;
    border: 1px solid %(border)s;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: %(bg_secondary)s;
    color: %(text_secondary)s;
    padding: 10px 20px;
    border: 1px solid %(border)s;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background-color: %(bg_tertiary)s;
    color: %(text_primary)s;
    border-bottom: 2px solid %(accent)s;
}

QTabBar::tab:hover:!selected {
    background-color: %(bg_tertiary)s;
}

/* 菜单 */
QMenu {
    background-color: %(bg_secondary)s;
    color: %(text_primary)s;
    border: 1px solid %(border)s;
    border-radius: 6px;
    padding: 8px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: %(accent)s;
    color: %(bg_primary)s;
}

/* 工具提示 */
QToolTip {
    background-color: %(bg_secondary)s;
    color: %(text_primary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 6px 10px;
}

/* 配置面板特定样式 */
QFrame#configCard {
    background-color: %(bg_secondary)s;
    border: 1px solid %(border)s;
    border-radius: 12px;
}

QFrame#configCard:hover {
    border-color: %(border_hover)s;
}

QLabel#cardTitle {
    color: %(text_primary)s;
    font-size: 14px;
    font-weight: bold;
}

QLabel#fieldLabel {
    color: %(text_secondary)s;
    font-size: 12px;
}

QLabel#pathLabel {
    color: %(accent)s;
    font-size: 12px;
    font-family: 'Consolas', monospace;
}

QFrame#leftPanel, QFrame#rightPanel {
    background-color: transparent;
}

QListWidget#configList {
    background-color: %(bg_secondary)s;
    color: %(text_secondary)s;
    border: 1px solid %(border)s;
    border-radius: 8px;
    outline: none;
    padding: 8px;
}

QListWidget#configList::item {
    padding: 12px;
    border-radius: 6px;
    margin: 2px 0;
}

QListWidget#configList::item:selected {
    background-color: %(accent)s;
    color: %(bg_primary)s;
}

QListWidget#configList::item:hover:!selected {
    background-color: %(bg_tertiary)s;
}

/* 特殊按钮 */
QPushButton#smallButton {
    padding: 6px 12px;
    font-size: 12px;
}

QPushButton#primaryButton {
    background-color: %(btn_primary)s;
    border-color: rgba(46, 160, 67, 0.4);
    font-weight: bold;
}

QPushButton#primaryButton:hover {
    background-color: %(btn_primary_hover)s;
}

QPushButton#dangerButton {
    background-color: %(btn_danger)s;
    border-color: rgba(248, 81, 73, 0.4);
}

QPushButton#dangerButton:hover {
    background-color: %(btn_danger_hover)s;
}

QWidget#configContent {
    background-color: transparent;
}

/* 表格内小按钮 */
QTableWidget QPushButton {
    background-color: %(bg_tertiary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    color: %(text_secondary)s;
    font-size: 14px;
    font-weight: bold;
}

QTableWidget QPushButton:hover {
    background-color: %(border)s;
    border-color: %(border_hover)s;
    color: %(text_primary)s;
}

QTableWidget QPushButton:pressed {
    background-color: %(bg_secondary)s;
}
"""

# 状态卡片样式
STATUS_CARD_STYLE = """
    QFrame#statusCard {
        background-color: %(bg_tertiary)s;
        border: 1px solid %(border)s;
        border-radius: 12px;
        padding: 16px;
    }
    QFrame#statusCard:hover {
        border-color: %(border_hover)s;
    }
"""

# 日志面板特定样式
LOG_STYLES = {
    "DEBUG": "color: #8b949e;",
    "INFO": "color: #58a6ff;",
    "WARNING": "color: #d29922;",
    "ERROR": "color: #f85149;",
    "SUCCESS": "color: #3fb950;",
}

def get_stylesheet() -> str:
    """获取完整的样式表字符串"""
    return GLOBAL_STYLESHEET % COLORS

def get_status_card_style() -> str:
    """获取状态卡片样式"""
    return STATUS_CARD_STYLE % COLORS

def get_log_level_color(level: str) -> str:
    """获取日志级别对应的颜色"""
    return LOG_STYLES.get(level.upper(), "color: #c9d1d9;")
