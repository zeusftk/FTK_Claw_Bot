from typing import Optional
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QProgressBar, QMessageBox, QAbstractItemView, QFileDialog,
    QProgressDialog, QApplication, QDialog, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from ...core import WSLManager
from ...models import WSLDistro, DistroStatus


class WSLPanel(QWidget):
    distro_started = pyqtSignal(str)
    distro_stopped = pyqtSignal(str)
    distro_imported = pyqtSignal(str)

    def __init__(self, wsl_manager: WSLManager, parent=None):
        super().__init__(parent)
        self._wsl_manager = wsl_manager
        self._selected_distro: Optional[WSLDistro] = None
        self._last_auto_name = ""

        self._init_ui()
        self._init_connections()
        self._refresh_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        title = QLabel("WSL 分发管理")
        title.setObjectName("panelTitle")
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.refresh_btn = QPushButton("刷新")
        self.shutdown_all_btn = QPushButton("关闭所有")
        self.import_btn = QPushButton("导入分发")
        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(self.shutdown_all_btn)
        header_layout.addWidget(self.import_btn)

        layout.addLayout(header_layout)

        self.distro_table = QTableWidget()
        self.distro_table.setColumnCount(5)
        self.distro_table.setHorizontalHeaderLabels(["名称", "版本", "状态", "默认", "操作"])
        self.distro_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.distro_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.distro_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.distro_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.distro_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.distro_table.setColumnWidth(1, 80)
        self.distro_table.setColumnWidth(2, 100)
        self.distro_table.setColumnWidth(3, 60)
        self.distro_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.distro_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.distro_table.setAlternatingRowColors(True)
        self.distro_table.verticalHeader().setVisible(False)
        layout.addWidget(self.distro_table)

        details_group = QGroupBox("分发详情")
        details_layout = QVBoxLayout(details_group)

        self.details_name = QLabel("请选择一个分发")
        self.details_name.setObjectName("detailsName")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.details_name.setFont(font)
        details_layout.addWidget(self.details_name)

        self.cpu_progress = QProgressBar()
        self.cpu_progress.setFormat("CPU 使用: %p%")
        self.cpu_progress.setTextVisible(True)
        details_layout.addWidget(self.cpu_progress)

        self.mem_progress = QProgressBar()
        self.mem_progress.setFormat("内存使用: %v MB / %m MB")
        self.mem_progress.setTextVisible(True)
        details_layout.addWidget(self.mem_progress)

        info_layout = QHBoxLayout()
        self.ip_label = QLabel("IP 地址: --")
        self.uptime_label = QLabel("运行时间: --")
        info_layout.addWidget(self.ip_label)
        info_layout.addWidget(self.uptime_label)
        details_layout.addLayout(info_layout)

        layout.addWidget(details_group)

        self._apply_styles()

    def _apply_styles(self):
        # 样式已在全局样式表中定义
        pass

    def _init_connections(self):
        self.refresh_btn.clicked.connect(self._refresh_list)
        self.shutdown_all_btn.clicked.connect(self._shutdown_all)
        self.import_btn.clicked.connect(self._import_distro)
        self.distro_table.itemSelectionChanged.connect(self._on_selection_changed)

    def _refresh_list(self):
        distros = self._wsl_manager.list_distros()
        self.distro_table.setRowCount(len(distros))

        for row, distro in enumerate(distros):
            name_item = QTableWidgetItem(distro.name)
            name_item.setData(Qt.ItemDataRole.UserRole, distro.name)

            version_item = QTableWidgetItem(f"WSL{distro.version}")

            status_item = QTableWidgetItem(distro.status.value)
            if distro.status == DistroStatus.RUNNING:
                status_item.setForeground(QColor("#4caf50"))
            else:
                status_item.setForeground(QColor("#f44336"))

            default_item = QTableWidgetItem("✓" if distro.is_default else "")

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)

            if distro.is_running:
                stop_btn = QPushButton("停止")
                stop_btn.setProperty("distro_name", distro.name)
                stop_btn.clicked.connect(lambda checked, n=distro.name: self._stop_distro(n))
                action_layout.addWidget(stop_btn)
            else:
                start_btn = QPushButton("启动")
                start_btn.setProperty("distro_name", distro.name)
                start_btn.clicked.connect(lambda checked, n=distro.name: self._start_distro(n))
                action_layout.addWidget(start_btn)

            terminal_btn = QPushButton("终端")
            terminal_btn.setProperty("distro_name", distro.name)
            terminal_btn.clicked.connect(lambda checked, n=distro.name: self._open_terminal(n))
            action_layout.addWidget(terminal_btn)

            self.distro_table.setItem(row, 0, name_item)
            self.distro_table.setItem(row, 1, version_item)
            self.distro_table.setItem(row, 2, status_item)
            self.distro_table.setItem(row, 3, default_item)
            self.distro_table.setCellWidget(row, 4, action_widget)

    def _on_selection_changed(self):
        selected = self.distro_table.selectedItems()
        if selected:
            row = selected[0].row()
            name_item = self.distro_table.item(row, 0)
            distro_name = name_item.data(Qt.ItemDataRole.UserRole)
            self._show_distro_details(distro_name)

    def _show_distro_details(self, distro_name: str):
        distros = self._wsl_manager.list_distros()
        distro = next((d for d in distros if d.name == distro_name), None)

        if distro:
            self._selected_distro = distro
            self.details_name.setText(distro_name)

            if distro.is_running:
                resources = self._wsl_manager.get_distro_resources(distro_name)
                self.cpu_progress.setValue(int(resources.get("cpu_usage", 0)))

                mem_usage = resources.get("memory_usage", 0) // (1024 * 1024)
                mem_total = resources.get("memory_total", 0) // (1024 * 1024)
                self.mem_progress.setMaximum(max(mem_total, 1))
                self.mem_progress.setValue(mem_usage)

                ip = self._wsl_manager.get_distro_ip(distro_name)
                self.ip_label.setText(f"IP 地址: {ip or '--'}")

                if distro.running_duration:
                    self.uptime_label.setText(f"运行时间: {distro.running_duration}")
                else:
                    self.uptime_label.setText("运行时间: --")
            else:
                self.cpu_progress.setValue(0)
                self.mem_progress.setValue(0)
                self.ip_label.setText("IP 地址: --")
                self.uptime_label.setText("运行时间: --")

    def _start_distro(self, distro_name: str):
        success = self._wsl_manager.start_distro(distro_name)
        if success:
            self.distro_started.emit(distro_name)
            self._refresh_list()
        else:
            QMessageBox.warning(self, "错误", f"无法启动分发: {distro_name}")

    def _stop_distro(self, distro_name: str):
        success = self._wsl_manager.stop_distro(distro_name)
        if success:
            self.distro_stopped.emit(distro_name)
            self._refresh_list()
        else:
            QMessageBox.warning(self, "错误", f"无法停止分发: {distro_name}")

    def _shutdown_all(self):
        reply = QMessageBox.question(
            self,
            "确认",
            "确定要关闭所有 WSL 分发吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._wsl_manager.shutdown_all()
            self._refresh_list()

    def _open_terminal(self, distro_name: str):
        import subprocess
        subprocess.Popen(["wt", "wsl", "-d", distro_name], shell=True)

    def _import_distro(self):
        """显示导入分发对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("导入 WSL 分发")
        dialog.setMinimumWidth(500)
        layout = QVBoxLayout(dialog)

        tar_layout = QHBoxLayout()
        tar_label = QLabel("tar 文件:")
        tar_layout.addWidget(tar_label)

        tar_edit = QLineEdit()
        tar_edit.setPlaceholderText("选择 .tar 文件...")
        tar_layout.addWidget(tar_edit, 1)

        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(lambda: self._browse_tar(tar_edit))
        tar_layout.addWidget(browse_btn)

        layout.addLayout(tar_layout)

        name_layout = QHBoxLayout()
        name_label = QLabel("分发名称:")
        name_layout.addWidget(name_label)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("nanobot")
        name_layout.addWidget(name_edit, 1)

        layout.addLayout(name_layout)

        hint_label = QLabel("提示: 分发名称将从 tar 文件名自动推断，可手动修改")
        hint_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(hint_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        import_btn = QPushButton("导入")
        import_btn.setDefault(True)
        btn_layout.addWidget(import_btn)

        layout.addLayout(btn_layout)

        tar_edit.textChanged.connect(lambda: self._auto_fill_distro_name(tar_edit.text(), name_edit))

        def do_import():
            tar_path = tar_edit.text().strip()
            distro_name = name_edit.text().strip()

            if not tar_path:
                QMessageBox.warning(self, "错误", "请选择 tar 文件")
                return

            if not distro_name:
                QMessageBox.warning(self, "错误", "请输入分发名称")
                return

            dialog.close()
            self._do_import(tar_path, distro_name)

        import_btn.clicked.connect(do_import)
        dialog.exec()

    def _browse_tar(self, line_edit):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 tar 文件", "", "Tar Files (*.tar *.tar.gz *.tar.xz);;All Files (*)"
        )
        if file_path:
            line_edit.setText(file_path)

    def _auto_fill_distro_name(self, tar_path: str, name_edit: QLineEdit):
        if tar_path:
            basename = os.path.basename(tar_path)
            name = basename.replace('.tar.gz', '').replace('.tgz', '').replace('.tar.xz', '').replace('.tar', '')
            name = name.lower().replace(' ', '-')
            if name_edit.text() == "" or name_edit.text() == self._last_auto_name:
                name_edit.setText(name)
                self._last_auto_name = name

    def _do_import(self, tar_path: str, distro_name: str):
        """执行实际的导入操作"""
        existing_distros = self._wsl_manager.list_distros()
        if any(d.name == distro_name for d in existing_distros):
            reply = QMessageBox.question(
                self, "确认",
                f"分发 '{distro_name}' 已存在。导入将覆盖现有分发，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        progress = QProgressDialog("正在导入 WSL 分发...", "取消", 0, 0, self)
        progress.setWindowTitle("导入中")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.show()

        try:
            result = self._wsl_manager.import_distro(tar_path, distro_name)
        finally:
            progress.close()

        if result.success:
            QMessageBox.information(
                self, "成功",
                f"WSL 分发 '{distro_name}' 导入成功！\n\n{result.stdout}"
            )
            self.distro_imported.emit(distro_name)
            self._refresh_list()
        else:
            QMessageBox.critical(
                self, "导入失败",
                f"无法导入 WSL 分发:\n{result.stderr}"
            )
