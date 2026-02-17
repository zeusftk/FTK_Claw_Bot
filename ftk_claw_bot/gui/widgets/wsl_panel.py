from typing import Optional
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView, QFileDialog,
    QProgressDialog, QDialog, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ...core import WSLManager, NanobotController, ConfigManager
from ...models import WSLDistro, DistroStatus


class WSLPanel(QWidget):
    distro_started = pyqtSignal(str)
    distro_stopped = pyqtSignal(str)
    distro_imported = pyqtSignal(str)

    def __init__(
        self,
        wsl_manager: WSLManager,
        nanobot_controller: NanobotController = None,
        config_manager: ConfigManager = None,
        parent=None
    ):
        super().__init__(parent)
        self._wsl_manager = wsl_manager
        self._nanobot_controller = nanobot_controller
        self._config_manager = config_manager
        self._selected_distro: Optional[WSLDistro] = None
        self._last_auto_name = ""

        self._init_ui()
        self._init_connections()
        self._refresh_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        title = QLabel("WSL 分发管理")
        title.setObjectName("panelTitle")
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        title.setFont(font)
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.refresh_btn = QPushButton("🔄 刷新")
        self.shutdown_all_btn = QPushButton("⏹ 关闭所有")
        self.import_btn = QPushButton("📥 导入分发")

        for btn in [self.refresh_btn, self.shutdown_all_btn, self.import_btn]:
            btn.setMinimumHeight(36)

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
        self.distro_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.distro_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.distro_table.setAlternatingRowColors(True)
        self.distro_table.verticalHeader().setVisible(False)
        self.distro_table.setMinimumHeight(300)
        layout.addWidget(self.distro_table)

        self._apply_styles()

    def _apply_styles(self):
        self.distro_table.setStyleSheet("""
            QTableWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                outline: none;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #21262d;
                background-color: transparent;
            }
            QTableWidget::item:selected {
                background-color: transparent;
            }
            QTableWidget::item:focus {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QHeaderView::section {
                background-color: #21262d;
                color: #f0f6fc;
                padding: 10px 8px;
                border: none;
                font-weight: bold;
            }
            QTableWidget:focus {
                outline: none;
                border: 1px solid #30363d;
            }
        """)

    def _init_connections(self):
        self.refresh_btn.clicked.connect(self._refresh_list)
        self.shutdown_all_btn.clicked.connect(self._shutdown_all)
        self.import_btn.clicked.connect(self._import_distro)

    def _refresh_list(self):
        distros = self._wsl_manager.list_distros()
        self.distro_table.setRowCount(len(distros))

        for row, distro in enumerate(distros):
            name_item = QTableWidgetItem(distro.name)
            name_item.setData(Qt.ItemDataRole.UserRole, distro.name)
            name_item.setFont(QFont("Microsoft YaHei UI", 11))

            version_item = QTableWidgetItem(f"WSL{distro.version}")

            status_item = QTableWidgetItem(distro.status.value)
            if distro.status == DistroStatus.RUNNING:
                status_item.setForeground(QColor("#3fb950"))
            else:
                status_item.setForeground(QColor("#f85149"))

            default_item = QTableWidgetItem("✓" if distro.is_default else "")
            if distro.is_default:
                default_item.setForeground(QColor("#d29922"))

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(8)
            action_widget.setStyleSheet("background: transparent;")
            action_widget.setMinimumHeight(32)

            if distro.is_running:
                stop_btn = QPushButton("■ 停止")
                stop_btn.setObjectName("danger")
                stop_btn.setMinimumSize(70, 28)
                stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                stop_btn.clicked.connect(lambda checked, n=distro.name: self._stop_distro(n))
                action_layout.addWidget(stop_btn)
            else:
                start_btn = QPushButton("▶ 启动")
                start_btn.setObjectName("primary")
                start_btn.setMinimumSize(70, 28)
                start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                start_btn.clicked.connect(lambda checked, n=distro.name: self._start_distro(n))
                action_layout.addWidget(start_btn)

            remove_btn = QPushButton("✕ 移除")
            remove_btn.setMinimumSize(60, 28)
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.clicked.connect(lambda checked, n=distro.name: self._remove_distro(n))
            action_layout.addWidget(remove_btn)

            self.distro_table.setItem(row, 0, name_item)
            self.distro_table.setItem(row, 1, version_item)
            self.distro_table.setItem(row, 2, status_item)
            self.distro_table.setItem(row, 3, default_item)
            self.distro_table.setCellWidget(row, 4, action_widget)

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

    def _remove_distro(self, distro_name: str):
        reply = QMessageBox.question(
            self, "确认",
            f"确定要移除分发 '{distro_name}' 吗？\n此操作将注销分发但不会删除虚拟磁盘。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success = self._wsl_manager.unregister_distro(distro_name)
            if success:
                QMessageBox.information(self, "成功", f"分发 '{distro_name}' 已移除")
                self._refresh_list()
            else:
                QMessageBox.warning(self, "错误", f"无法移除分发: {distro_name}")

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
        import_btn.setObjectName("primary")
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
        from loguru import logger
        
        logger.info(f"开始导入 WSL 分发: tar_path={tar_path}, distro_name={distro_name}")
        
        # 检查 tar 文件是否存在
        import os
        if not os.path.exists(tar_path):
            logger.error(f"tar 文件不存在: {tar_path}")
            QMessageBox.critical(self, "导入失败", f"tar 文件不存在: {tar_path}")
            return
        
        logger.info(f"tar 文件大小: {os.path.getsize(tar_path)} bytes")
        
        existing_distros = self._wsl_manager.list_distros()
        existing_names = [d.name for d in existing_distros]
        logger.info(f"现有分发列表: {existing_names}")
        
        if any(d.name == distro_name for d in existing_distros):
            logger.warning(f"分发 '{distro_name}' 已存在")
            reply = QMessageBox.question(
                self, "确认",
                f"分发 '{distro_name}' 已存在。导入将覆盖现有分发，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                logger.info("用户取消了导入")
                return

        progress = QProgressDialog("正在导入 WSL 分发...", "取消", 0, 0, self)
        progress.setWindowTitle("导入中")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.show()

        try:
            logger.info("调用 wsl_manager.import_distro")
            result = self._wsl_manager.import_distro(tar_path, distro_name)
            logger.info(f"导入结果: success={result.success}, return_code={result.return_code}")
            logger.debug(f"导入 stdout: {result.stdout}")
            if result.stderr:
                logger.warning(f"导入 stderr: {result.stderr}")
        except Exception as e:
            logger.error(f"导入过程异常: {e}")
            import traceback
            logger.error(f"详细堆栈: {traceback.format_exc()}")
            result = None
        finally:
            progress.close()

        if result and result.success:
            logger.info(f"分发 '{distro_name}' 导入成功")
            QMessageBox.information(
                self, "成功",
                f"WSL 分发 '{distro_name}' 导入成功！\n\n{result.stdout}"
            )
            self.distro_imported.emit(distro_name)
            self._refresh_list()
        else:
            error_msg = result.stderr if result else "未知错误"
            logger.error(f"分发 '{distro_name}' 导入失败: {error_msg}")
            QMessageBox.critical(
                self, "导入失败",
                f"无法导入 WSL 分发:\n{error_msg}"
            )
