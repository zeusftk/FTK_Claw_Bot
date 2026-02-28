# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QCheckBox, QFrame, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor

from ...utils.i18n import tr


class LogEntry:
    def __init__(self, level: str, timestamp: str, source: str, message: str):
        self.level = level
        self.timestamp = timestamp
        self.source = source
        self.message = message


class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logs: List[LogEntry] = []
        self._max_logs: int = 1000
        self._auto_scroll: bool = True
        self._filter_level: str = tr("log.all", "全部")
        self._displayed_count: int = 0

        self._init_ui()
        self._start_timer()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        title = QLabel(tr("log.title", "日志查看"))
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        header_layout.addWidget(title)
        header_layout.addStretch()

        clear_btn = QPushButton(tr("btn.clear", "清空"))
        clear_btn.clicked.connect(self._clear_logs)
        export_btn = QPushButton(tr("log.btn_export", "导出"))
        export_btn.clicked.connect(self._export_logs)
        header_layout.addWidget(clear_btn)
        header_layout.addWidget(export_btn)

        layout.addLayout(header_layout)

        filter_layout = QHBoxLayout()

        level_label = QLabel(tr("log.level", "日志级别:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems([tr("log.all", "全部"), "DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_combo.currentTextChanged.connect(self._on_filter_changed)

        source_label = QLabel(tr("log.source", "来源:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems([tr("log.all", "全部"), tr("log.source_clawbot", "Clawbot"), tr("log.source_bridge", "Bridge"), tr("log.source_wsl", "WSL"), tr("log.source_ftk", "FTK_Claw_Bot")])
        self.source_combo.currentTextChanged.connect(self._on_filter_changed)
        
        time_label = QLabel(tr("log.time_range", "时间范围:"))
        self.time_combo = QComboBox()
        self.time_combo.addItems([tr("log.last_10min", "最近10分钟"), tr("log.last_1hour", "最近1小时"), tr("log.last_24hours", "最近24小时"), tr("log.all", "全部")])
        self.time_combo.currentTextChanged.connect(self._on_filter_changed)

        self.auto_scroll_check = QCheckBox(tr("log.realtime_refresh", "实时刷新"))
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.stateChanged.connect(self._on_auto_scroll_changed)

        filter_layout.addWidget(level_label)
        filter_layout.addWidget(self.level_combo)
        filter_layout.addWidget(source_label)
        filter_layout.addWidget(self.source_combo)
        filter_layout.addWidget(time_label)
        filter_layout.addWidget(self.time_combo)
        filter_layout.addStretch()
        filter_layout.addWidget(self.auto_scroll_check)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel(tr("log.search", "搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(tr("log.search_placeholder", "输入关键词搜索..."))
        self.search_edit.textChanged.connect(self._on_filter_changed)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit, 1)

        layout.addLayout(filter_layout)
        layout.addLayout(search_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.log_text, 1)
        
        # 分页信息
        self.pagination_label = QLabel(tr("log.pagination", "第 {start}-{end} 条，共 {total} 条").format(start=1, end=0, total=0))
        self.pagination_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.pagination_label)

        self._apply_styles()

    def _apply_styles(self):
        # 样式已在全局样式表中定义
        pass

    def _start_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_display)
        self._timer.start(1000)

    def add_log(self, level: str, source: str, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = LogEntry(level, timestamp, source, message)

        self._logs.append(entry)

        if len(self._logs) > self._max_logs:
            self._logs.pop(0)

        self._append_log(entry)
        self._update_pagination()

    def _should_display(self, entry: LogEntry) -> bool:
        # 级别过滤
        level_filter = self.level_combo.currentText()
        if level_filter != tr("log.all", "全部") and entry.level != level_filter:
            return False

        # 来源过滤
        source_filter = self.source_combo.currentText()
        if source_filter != tr("log.all", "全部"):
            # 检查来源是否匹配（需要反向映射翻译后的来源名称）
            source_map = {
                tr("log.source_clawbot", "Clawbot"): "Clawbot",
                tr("log.source_bridge", "Bridge"): "Bridge",
                tr("log.source_wsl", "WSL"): "WSL",
                tr("log.source_ftk", "FTK_Claw_Bot"): "FTK_Claw_Bot"
            }
            if source_filter in source_map and entry.source != source_map[source_filter]:
                return False
        
        # 时间范围过滤
        time_filter = self.time_combo.currentText()
        if time_filter != tr("log.all", "全部"):
            try:
                entry_time = datetime.strptime(entry.timestamp, "%Y-%m-%d %H:%M:%S")
                now = datetime.now()
                
                if time_filter == tr("log.last_10min", "最近10分钟"):
                    cutoff = now - timedelta(minutes=10)
                elif time_filter == tr("log.last_1hour", "最近1小时"):
                    cutoff = now - timedelta(hours=1)
                elif time_filter == tr("log.last_24hours", "最近24小时"):
                    cutoff = now - timedelta(hours=24)
                else:
                    cutoff = None
                
                if cutoff and entry_time < cutoff:
                    return False
            except:
                pass
        
        # 关键词搜索
        search_text = self.search_edit.text().strip().lower()
        if search_text:
            if search_text not in entry.message.lower() and search_text not in entry.source.lower():
                return False

        return True

    def _refresh_display(self):
        pass

    def _on_filter_changed(self, *args):
        self._rebuild_display()

    def _on_auto_scroll_changed(self, state: int):
        self._auto_scroll = state == Qt.CheckState.Checked.value

    def _rebuild_display(self):
        self.log_text.clear()
        self._displayed_count = 0
        for entry in self._logs:
            self._append_log(entry)
        self._update_pagination()
    
    def _update_pagination(self):
        self.pagination_label.setText(tr("log.pagination", "第 {start}-{end} 条，共 {total} 条").format(start=1, end=self._displayed_count, total=len(self._logs)))
    
    def _append_log(self, entry: LogEntry):
        if not self._should_display(entry):
            return

        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        format = QTextCharFormat()

        # 使用高对比度颜色方案
        level_colors = {
            "DEBUG": QColor("#8b949e"),    # 灰色
            "INFO": QColor("#58a6ff"),     # 蓝色
            "WARNING": QColor("#d29922"),  # 黄色
            "ERROR": QColor("#f85149"),    # 红色
            "SUCCESS": QColor("#3fb950"),  # 绿色
        }
        format.setForeground(level_colors.get(entry.level, QColor("#c9d1d9")))

        cursor.insertText(f"[{entry.level}] ", format)

        format.setForeground(QColor("#8b949e"))
        cursor.insertText(f"{entry.timestamp} ", format)

        format.setForeground(QColor("#3fb950"))
        cursor.insertText(f"[{entry.source}] ", format)

        format.setForeground(QColor("#f0f6fc"))
        cursor.insertText(f"{entry.message}\n", format)
        
        self._displayed_count += 1

        if self._auto_scroll:
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _clear_logs(self):
        self._logs.clear()
        self.log_text.clear()

    def _export_logs(self):
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, tr("log.export_title", "导出日志"), "", "Text Files (*.txt);;Log Files (*.log)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    for entry in self._logs:
                        f.write(f"[{entry.level}] {entry.timestamp} [{entry.source}] {entry.message}\n")
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, tr("error.title", "错误"), tr("log.export_failed", "导出失败: {error}").format(error=e))

    def get_logs(self, count: Optional[int] = None) -> List[LogEntry]:
        if count:
            return self._logs[-count:]
        return self._logs.copy()
