from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QSpinBox, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ...core import WSLManager


class CommandPanel(QWidget):
    command_executed = pyqtSignal(str)

    def __init__(
        self, wsl_manager: WSLManager, parent=None
    ):
        super().__init__(parent)
        self._wsl_manager = wsl_manager

        self._init_ui()
        self._init_connections()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QLabel("命令执行")
        title.setObjectName("panelTitle")
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        control_group = QGroupBox("执行设置")
        control_layout = QVBoxLayout(control_group)
        control_layout.setContentsMargins(12, 12, 12, 12)
        control_layout.setSpacing(12)

        distro_layout = QHBoxLayout()
        distro_label = QLabel("WSL 分发:")
        distro_label.setFixedWidth(100)
        self.distro_combo = QComboBox()
        self.distro_combo.setMinimumHeight(32)
        distro_layout.addWidget(distro_label)
        distro_layout.addWidget(self.distro_combo, 1)
        control_layout.addLayout(distro_layout)

        command_layout = QHBoxLayout()
        command_label = QLabel("命令:")
        command_label.setFixedWidth(100)
        self.command_edit = QTextEdit()
        self.command_edit.setPlaceholderText("输入要执行的命令...")
        self.command_edit.setMaximumHeight(80)
        command_layout.addWidget(command_label)
        command_layout.addWidget(self.command_edit, 1)
        control_layout.addLayout(command_layout)

        timeout_layout = QHBoxLayout()
        timeout_label = QLabel("超时时间(秒):")
        timeout_label.setFixedWidth(100)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(1)
        self.timeout_spin.setMaximum(3600)
        self.timeout_spin.setValue(30)
        timeout_layout.addWidget(timeout_label)
        timeout_layout.addWidget(self.timeout_spin)
        timeout_layout.addStretch()
        control_layout.addLayout(timeout_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.execute_btn = QPushButton("▶ 执行命令")
        self.execute_btn.setObjectName("primaryButton")
        self.execute_btn.setMinimumHeight(36)
        self.clear_output_btn = QPushButton("清空输出")
        self.clear_output_btn.setMinimumHeight(36)
        self.refresh_distros_btn = QPushButton("刷新分发")
        self.refresh_distros_btn.setMinimumHeight(36)
        button_layout.addWidget(self.refresh_distros_btn)
        button_layout.addWidget(self.clear_output_btn)
        button_layout.addWidget(self.execute_btn)
        control_layout.addLayout(button_layout)

        layout.addWidget(control_group)

        output_group = QGroupBox("输出")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(12, 12, 12, 12)

        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("命令输出将显示在这里...")
        output_layout.addWidget(self.output_edit)

        layout.addWidget(output_group, 1)

        self._refresh_distros()

    def _init_connections(self):
        self.execute_btn.clicked.connect(self._execute_command)
        self.clear_output_btn.clicked.connect(self._clear_output)
        self.refresh_distros_btn.clicked.connect(self._refresh_distros)

    def _refresh_distros(self):
        self.distro_combo.clear()
        distros = self._wsl_manager.list_distros()
        for distro in distros:
            self.distro_combo.addItem(distro.name)

    def _execute_command(self):
        distro_name = self.distro_combo.currentText()
        if not distro_name:
            self.output_edit.append("> 错误: 请选择 WSL 分发")
            return
            
        command = self.command_edit.toPlainText().strip()
        if not command:
            self.output_edit.append("> 错误: 请输入要执行的命令")
            return
            
        timeout = self.timeout_spin.value()
        
        self.output_edit.append(f"> 正在执行命令...")
        self.output_edit.append(f"> 分发: {distro_name}")
        self.output_edit.append(f"> 命令: {command}")
        self.output_edit.append("-" * 50)
        
        result = self._wsl_manager.execute_command(
            distro_name, command, timeout
        )
        
        if result.stdout:
            self.output_edit.append(result.stdout)
        if result.stderr:
            self.output_edit.append(f"[stderr] {result.stderr}")
        
        self.output_edit.append("-" * 50)
        self.output_edit.append(f"> 执行完成 (返回码: {result.return_code})")
        self.output_edit.append("")
        self.command_executed.emit(distro_name)

    def _clear_output(self):
        self.output_edit.clear()

