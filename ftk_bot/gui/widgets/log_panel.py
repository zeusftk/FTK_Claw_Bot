from datetime import datetime
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor


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
        self._filter_level: str = "ALL"

        self._init_ui()
        self._start_timer()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        title = QLabel("日志查看")
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        header_layout.addWidget(title)
        header_layout.addStretch()

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._clear_logs)
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._export_logs)
        header_layout.addWidget(clear_btn)
        header_layout.addWidget(export_btn)

        layout.addLayout(header_layout)

        filter_layout = QHBoxLayout()

        level_label = QLabel("日志级别:")
        self.level_combo = QComboBox()
        self.level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_combo.currentTextChanged.connect(self._on_filter_changed)

        source_label = QLabel("来源:")
        self.source_combo = QComboBox()
        self.source_combo.addItems(["ALL", "Nanobot", "Bridge", "WSL", "FTK_Bot"])

        self.auto_scroll_check = QCheckBox("实时刷新")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.stateChanged.connect(self._on_auto_scroll_changed)

        filter_layout.addWidget(level_label)
        filter_layout.addWidget(self.level_combo)
        filter_layout.addWidget(source_label)
        filter_layout.addWidget(self.source_combo)
        filter_layout.addStretch()
        filter_layout.addWidget(self.auto_scroll_check)

        layout.addLayout(filter_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.log_text, 1)

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

        if self._auto_scroll:
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _should_display(self, entry: LogEntry) -> bool:
        if self._filter_level != "ALL" and entry.level != self._filter_level:
            return False

        source_filter = self.source_combo.currentText()
        if source_filter != "ALL" and entry.source != source_filter:
            return False

        return True

    def _refresh_display(self):
        pass

    def _on_filter_changed(self, level: str):
        self._filter_level = level
        self._rebuild_display()

    def _on_auto_scroll_changed(self, state: int):
        self._auto_scroll = state == Qt.CheckState.Checked.value

    def _rebuild_display(self):
        self.log_text.clear()
        for entry in self._logs:
            self._append_log(entry)

    def _clear_logs(self):
        self._logs.clear()
        self.log_text.clear()

    def _export_logs(self):
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", "", "Text Files (*.txt);;Log Files (*.log)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    for entry in self._logs:
                        f.write(f"[{entry.level}] {entry.timestamp} [{entry.source}] {entry.message}\n")
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "错误", f"导出失败: {e}")

    def get_logs(self, count: Optional[int] = None) -> List[LogEntry]:
        if count:
            return self._logs[-count:]
        return self._logs.copy()
