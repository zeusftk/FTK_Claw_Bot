from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QCheckBox, QComboBox, QTabWidget,
    QWidget, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...core import ConfigManager


class SettingsDialog(QDialog):
    settings_saved = pyqtSignal()

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._main_config = config_manager.get_main_config()

        self.setWindowTitle("设置")
        self.setMinimumSize(600, 500)

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标签页
        self.tabs = QTabWidget()

        # 常规设置页
        self.general_tab = self._create_general_tab()
        self.tabs.addTab(self.general_tab, "常规")

        # 桥接设置页
        self.bridge_tab = self._create_bridge_tab()
        self.tabs.addTab(self.bridge_tab, "桥接")

        # UI设置页
        self.ui_tab = self._create_ui_tab()
        self.tabs.addTab(self.ui_tab, "界面")

        # 监控设置页
        self.monitor_tab = self._create_monitor_tab()
        self.tabs.addTab(self.monitor_tab, "监控")

        layout.addWidget(self.tabs)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save_settings)
        save_btn.setDefault(True)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)

        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self._load_settings)

        btn_layout.addWidget(reset_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

        self._apply_styles()

    def _create_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # 默认分发
        distro_layout = QHBoxLayout()
        distro_layout.addWidget(QLabel("默认WSL分发:"))
        self.default_distro_edit = QLineEdit()
        self.default_distro_edit.setPlaceholderText("Ubuntu-22.04")
        distro_layout.addWidget(self.default_distro_edit)
        layout.addLayout(distro_layout)

        # 工作空间
        workspace_layout = QHBoxLayout()
        workspace_layout.addWidget(QLabel("工作空间:"))
        self.workspace_edit = QLineEdit()
        self.workspace_edit.setPlaceholderText("D:\\nanobot_workspace")
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_workspace)
        workspace_layout.addWidget(self.workspace_edit)
        workspace_layout.addWidget(browse_btn)
        layout.addLayout(workspace_layout)

        # 自动启动
        self.auto_start_check = QCheckBox("开机自动启动")
        layout.addWidget(self.auto_start_check)

        # 最小化到托盘
        self.minimize_tray_check = QCheckBox("最小化到系统托盘")
        layout.addWidget(self.minimize_tray_check)

        layout.addStretch()
        return tab

    def _create_bridge_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # 启用桥接
        self.bridge_enabled_check = QCheckBox("启用IPC桥接")
        layout.addWidget(self.bridge_enabled_check)

        # 主机
        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel("监听主机:"))
        self.bridge_host_edit = QLineEdit()
        self.bridge_host_edit.setPlaceholderText("127.0.0.1")
        host_layout.addWidget(self.bridge_host_edit)
        layout.addLayout(host_layout)

        # 端口
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("监听端口:"))
        self.bridge_port_spin = QSpinBox()
        self.bridge_port_spin.setRange(1024, 65535)
        self.bridge_port_spin.setValue(9527)
        port_layout.addWidget(self.bridge_port_spin)
        port_layout.addStretch()
        layout.addLayout(port_layout)

        layout.addStretch()
        return tab

    def _create_ui_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # 主题
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("主题:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["深色", "浅色", "系统默认"])
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)

        # 语言
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("语言:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["简体中文", "English"])
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)

        layout.addStretch()
        return tab

    def _create_monitor_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # 刷新间隔
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("刷新间隔 (毫秒):"))
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(1000, 60000)
        self.refresh_interval_spin.setValue(5000)
        self.refresh_interval_spin.setSingleStep(1000)
        interval_layout.addWidget(self.refresh_interval_spin)
        interval_layout.addStretch()
        layout.addLayout(interval_layout)

        # 日志最大行数
        log_lines_layout = QHBoxLayout()
        log_lines_layout.addWidget(QLabel("日志最大行数:"))
        self.log_max_lines_spin = QSpinBox()
        self.log_max_lines_spin.setRange(100, 10000)
        self.log_max_lines_spin.setValue(1000)
        self.log_max_lines_spin.setSingleStep(100)
        log_lines_layout.addWidget(self.log_max_lines_spin)
        log_lines_layout.addStretch()
        layout.addLayout(log_lines_layout)

        layout.addStretch()
        return tab

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #cccccc;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #5c5c5c;
                border-radius: 4px;
                padding: 8px;
            }
            QSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #5c5c5c;
                border-radius: 4px;
                padding: 8px;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #5c5c5c;
                border-radius: 4px;
                padding: 8px;
            }
            QCheckBox {
                color: #cccccc;
            }
            QPushButton {
                background-color: #0e639c;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QTabWidget::pane {
                background-color: #2d2d30;
                border: 1px solid #3c3c3c;
            }
            QTabBar::tab {
                background-color: #2d2d30;
                color: #cccccc;
                padding: 8px 16px;
                border: 1px solid #3c3c3c;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)

    def _browse_workspace(self):
        path = QFileDialog.getExistingDirectory(self, "选择工作空间")
        if path:
            self.workspace_edit.setText(path)

    def _load_settings(self):
        # 加载常规设置
        self.default_distro_edit.setText(self._main_config.get("default_distro", ""))
        workspace = self._main_config.get("workspace", {})
        self.workspace_edit.setText(workspace.get("windows_path", ""))
        ui = self._main_config.get("ui", {})
        self.auto_start_check.setChecked(ui.get("auto_start", False))
        self.minimize_tray_check.setChecked(ui.get("minimize_to_tray", True))

        # 加载桥接设置
        bridge = self._main_config.get("bridge", {})
        self.bridge_enabled_check.setChecked(bridge.get("enabled", True))
        self.bridge_host_edit.setText(bridge.get("host", "127.0.0.1"))
        self.bridge_port_spin.setValue(bridge.get("port", 9527))

        # 加载UI设置
        theme = ui.get("theme", "dark")
        theme_index = {"dark": 0, "light": 1, "system": 2}.get(theme, 0)
        self.theme_combo.setCurrentIndex(theme_index)
        lang = ui.get("language", "zh_CN")
        lang_index = 0 if lang == "zh_CN" else 1
        self.lang_combo.setCurrentIndex(lang_index)

        # 加载监控设置
        monitor = self._main_config.get("monitor", {})
        self.refresh_interval_spin.setValue(monitor.get("refresh_interval", 5000))
        self.log_max_lines_spin.setValue(monitor.get("log_max_lines", 1000))

    def _save_settings(self):
        # 保存常规设置
        self._main_config["default_distro"] = self.default_distro_edit.text()
        self._main_config["workspace"] = {
            "windows_path": self.workspace_edit.text(),
            "sync_to_mnt": True
        }
        self._main_config["ui"] = {
            "theme": ["dark", "light", "system"][self.theme_combo.currentIndex()],
            "language": "zh_CN" if self.lang_combo.currentIndex() == 0 else "en",
            "auto_start": self.auto_start_check.isChecked(),
            "minimize_to_tray": self.minimize_tray_check.isChecked()
        }

        # 保存桥接设置
        self._main_config["bridge"] = {
            "enabled": self.bridge_enabled_check.isChecked(),
            "host": self.bridge_host_edit.text() or "127.0.0.1",
            "port": self.bridge_port_spin.value()
        }

        # 保存监控设置
        self._main_config["monitor"] = {
            "refresh_interval": self.refresh_interval_spin.value(),
            "log_max_lines": self.log_max_lines_spin.value()
        }

        # 保存到配置文件
        try:
            import json
            import os

            config_path = self._config_manager._main_config_path
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self._main_config, f, indent=2, ensure_ascii=False)

            self.settings_saved.emit()
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", str(e))
