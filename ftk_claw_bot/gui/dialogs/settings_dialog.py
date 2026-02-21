from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QCheckBox, QComboBox, QTabWidget,
    QWidget, QMessageBox, QFileDialog, QGroupBox, QFormLayout,
    QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ...core import ConfigManager
from ...utils.i18n import I18nManager, tr


class SettingsDialog(QDialog):
    settings_saved = pyqtSignal()

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._main_config = config_manager.get_main_config()
        self._original_lang = self._main_config.get("ui", {}).get("language", "zh_CN")

        self.setWindowTitle(tr("settings.title", "设置"))
        self.setMinimumSize(650, 550)

        self._init_ui()
        self._load_settings()
        self._apply_styles()
        
        I18nManager().language_changed.connect(self._retranslate_ui)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("settingsTabs")

        self.general_tab = self._create_general_tab()
        self.tabs.addTab(self.general_tab, tr("settings.tab.general", "常规"))

        self.bridge_tab = self._create_bridge_tab()
        self.tabs.addTab(self.bridge_tab, tr("settings.tab.bridge", "桥接"))

        self.ui_tab = self._create_ui_tab()
        self.tabs.addTab(self.ui_tab, tr("settings.tab.ui", "界面"))

        self.monitor_tab = self._create_monitor_tab()
        self.tabs.addTab(self.monitor_tab, tr("settings.tab.monitor", "监控"))

        layout.addWidget(self.tabs)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("horizontalLine")
        layout.addWidget(line)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        self.reset_btn = QPushButton(tr("btn.reset", "重置"))
        self.reset_btn.setObjectName("secondaryButton")
        self.reset_btn.clicked.connect(self._load_settings)

        self.save_btn = QPushButton(tr("btn.save", "保存"))
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._save_settings)
        self.save_btn.setDefault(True)

        self.cancel_btn = QPushButton(tr("btn.cancel", "取消"))
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.reset_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def _create_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        basic_group = QGroupBox(tr("settings.group.basic", "基本设置"))
        basic_group.setObjectName("settingsGroup")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(12)
        basic_layout.setContentsMargins(16, 20, 16, 16)

        self.default_distro_edit = QLineEdit()
        self.default_distro_edit.setPlaceholderText("Ubuntu-22.04")
        basic_layout.addRow(tr("settings.default_distro", "默认WSL分发:"), self.default_distro_edit)

        workspace_layout = QHBoxLayout()
        self.workspace_edit = QLineEdit()
        self.workspace_edit.setPlaceholderText("D:\\clawbot_workspace")
        self.browse_btn = QPushButton(tr("btn.browse", "浏览..."))
        self.browse_btn.setObjectName("smallButton")
        self.browse_btn.clicked.connect(self._browse_workspace)
        workspace_layout.addWidget(self.workspace_edit)
        workspace_layout.addWidget(self.browse_btn)
        basic_layout.addRow(tr("settings.workspace", "工作空间:"), workspace_layout)

        layout.addWidget(basic_group)

        startup_group = QGroupBox(tr("settings.group.startup", "启动选项"))
        startup_group.setObjectName("settingsGroup")
        startup_layout = QVBoxLayout(startup_group)
        startup_layout.setSpacing(12)
        startup_layout.setContentsMargins(16, 20, 16, 16)

        self.auto_start_check = QCheckBox(tr("settings.auto_start", "开机自动启动"))
        self.minimize_tray_check = QCheckBox(tr("settings.minimize_tray", "最小化到系统托盘"))
        startup_layout.addWidget(self.auto_start_check)
        startup_layout.addWidget(self.minimize_tray_check)

        layout.addWidget(startup_group)
        layout.addStretch()

        return tab

    def _create_bridge_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        bridge_group = QGroupBox(tr("settings.group.bridge", "桥接设置"))
        bridge_group.setObjectName("settingsGroup")
        bridge_layout = QFormLayout(bridge_group)
        bridge_layout.setSpacing(12)
        bridge_layout.setContentsMargins(16, 20, 16, 16)

        self.bridge_enabled_check = QCheckBox(tr("settings.bridge_enabled", "启用IPC桥接"))
        bridge_layout.addRow(self.bridge_enabled_check)

        self.bridge_host_edit = QLineEdit()
        self.bridge_host_edit.setPlaceholderText("127.0.0.1")
        bridge_layout.addRow(tr("settings.bridge_host", "监听主机:"), self.bridge_host_edit)

        self.bridge_port_spin = QSpinBox()
        self.bridge_port_spin.setRange(1024, 65535)
        self.bridge_port_spin.setValue(9527)
        self.bridge_port_spin.setMinimumWidth(120)
        bridge_layout.addRow(tr("settings.bridge_port", "监听端口:"), self.bridge_port_spin)

        layout.addWidget(bridge_group)
        layout.addStretch()

        return tab

    def _create_ui_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        ui_group = QGroupBox(tr("settings.group.ui", "界面设置"))
        ui_group.setObjectName("settingsGroup")
        ui_layout = QFormLayout(ui_group)
        ui_layout.setSpacing(12)
        ui_layout.setContentsMargins(16, 20, 16, 16)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems([tr("settings.theme_dark", "深色"), tr("settings.theme_light", "浅色"), tr("settings.theme_system", "系统默认")])
        self.theme_combo.setMinimumWidth(150)
        ui_layout.addRow(tr("settings.theme", "主题:"), self.theme_combo)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems([tr("settings.language_zh", "简体中文"), tr("settings.language_en", "English")])
        self.lang_combo.setMinimumWidth(150)
        ui_layout.addRow(tr("settings.language", "语言:"), self.lang_combo)

        layout.addWidget(ui_group)
        layout.addStretch()

        return tab

    def _create_monitor_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        monitor_group = QGroupBox(tr("settings.group.monitor", "监控设置"))
        monitor_group.setObjectName("settingsGroup")
        monitor_layout = QFormLayout(monitor_group)
        monitor_layout.setSpacing(12)
        monitor_layout.setContentsMargins(16, 20, 16, 16)

        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(1000, 60000)
        self.refresh_interval_spin.setValue(5000)
        self.refresh_interval_spin.setSingleStep(1000)
        self.refresh_interval_spin.setMinimumWidth(120)
        self.refresh_interval_spin.setSuffix(tr("settings.ms_suffix", " 毫秒"))
        monitor_layout.addRow(tr("settings.refresh_interval", "刷新间隔:"), self.refresh_interval_spin)

        self.log_max_lines_spin = QSpinBox()
        self.log_max_lines_spin.setRange(100, 10000)
        self.log_max_lines_spin.setValue(1000)
        self.log_max_lines_spin.setSingleStep(100)
        self.log_max_lines_spin.setMinimumWidth(120)
        monitor_layout.addRow(tr("settings.log_max_lines", "日志最大行数:"), self.log_max_lines_spin)

        layout.addWidget(monitor_group)
        layout.addStretch()

        return tab

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0d1117;
            }
            QWidget {
                background-color: #0d1117;
                color: #f0f6fc;
            }
            QGroupBox#settingsGroup {
                font-weight: bold;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #161b22;
            }
            QGroupBox#settingsGroup::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #f0f6fc;
            }
            QTabWidget#settingsTabs::pane {
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 8px;
                background-color: #0d1117;
            }
            QTabWidget#settingsTabs {
                background-color: #0d1117;
            }
            QTabBar::tab {
                padding: 8px 20px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                background-color: #21262d;
                color: #f0f6fc;
            }
            QTabBar::tab:selected {
                background-color: #30363d;
            }
            QFrame#horizontalLine {
                background-color: #30363d;
                max-height: 1px;
            }
            QPushButton#primaryButton {
                background-color: #238636;
                color: white;
                padding: 8px 24px;
                border-radius: 6px;
                font-weight: bold;
                border: none;
            }
            QPushButton#primaryButton:hover {
                background-color: #2ea043;
            }
            QPushButton#secondaryButton {
                background-color: #21262d;
                color: #f0f6fc;
                padding: 8px 24px;
                border-radius: 6px;
                border: 1px solid #30363d;
            }
            QPushButton#secondaryButton:hover {
                background-color: #30363d;
            }
            QPushButton#smallButton {
                padding: 6px 12px;
                border-radius: 4px;
                background-color: #21262d;
                color: #f0f6fc;
                border: 1px solid #30363d;
            }
            QLineEdit {
                background-color: #0d1117;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 6px 10px;
            }
            QLineEdit:focus {
                border-color: #58a6ff;
            }
            QSpinBox {
                background-color: #0d1117;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QComboBox {
                background-color: #21262d;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #21262d;
                color: #f0f6fc;
                selection-background-color: #30363d;
            }
            QCheckBox {
                color: #f0f6fc;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QLabel {
                color: #f0f6fc;
                background-color: transparent;
            }
        """)

    def _retranslate_ui(self):
        self.setWindowTitle(tr("settings.title", "设置"))
        self.tabs.setTabText(0, tr("settings.tab.general", "常规"))
        self.tabs.setTabText(1, tr("settings.tab.bridge", "桥接"))
        self.tabs.setTabText(2, tr("settings.tab.ui", "界面"))
        self.tabs.setTabText(3, tr("settings.tab.monitor", "监控"))
        
        self.reset_btn.setText(tr("btn.reset", "重置"))
        self.save_btn.setText(tr("btn.save", "保存"))
        self.cancel_btn.setText(tr("btn.cancel", "取消"))
        self.browse_btn.setText(tr("btn.browse", "浏览..."))
        
        self.auto_start_check.setText(tr("settings.auto_start", "开机自动启动"))
        self.minimize_tray_check.setText(tr("settings.minimize_tray", "最小化到系统托盘"))
        self.bridge_enabled_check.setText(tr("settings.bridge_enabled", "启用IPC桥接"))

    def _browse_workspace(self):
        path = QFileDialog.getExistingDirectory(self, tr("settings.select_workspace", "选择工作空间"))
        if path:
            self.workspace_edit.setText(path)

    def _load_settings(self):
        self.default_distro_edit.setText(self._main_config.get("default_distro", ""))
        workspace = self._main_config.get("workspace", {})
        self.workspace_edit.setText(workspace.get("windows_path", ""))
        ui = self._main_config.get("ui", {})
        self.auto_start_check.setChecked(ui.get("auto_start", False))
        self.minimize_tray_check.setChecked(ui.get("minimize_to_tray", True))

        bridge = self._main_config.get("bridge", {})
        self.bridge_enabled_check.setChecked(bridge.get("enabled", True))
        self.bridge_host_edit.setText(bridge.get("host", "127.0.0.1"))
        self.bridge_port_spin.setValue(bridge.get("port", 9527))

        theme = ui.get("theme", "dark")
        theme_index = {"dark": 0, "light": 1, "system": 2}.get(theme, 0)
        self.theme_combo.setCurrentIndex(theme_index)
        lang = ui.get("language", "zh_CN")
        lang_index = 0 if lang == "zh_CN" else 1
        self.lang_combo.setCurrentIndex(lang_index)

        monitor = self._main_config.get("monitor", {})
        self.refresh_interval_spin.setValue(monitor.get("refresh_interval", 5000))
        self.log_max_lines_spin.setValue(monitor.get("log_max_lines", 1000))

    def _save_settings(self):
        self._main_config["default_distro"] = self.default_distro_edit.text()
        self._main_config["workspace"] = {
            "windows_path": self.workspace_edit.text(),
            "sync_to_mnt": True
        }
        
        lang = "zh_CN" if self.lang_combo.currentIndex() == 0 else "en_US"
        self._main_config["ui"] = {
            "theme": ["dark", "light", "system"][self.theme_combo.currentIndex()],
            "language": lang,
            "auto_start": self.auto_start_check.isChecked(),
            "minimize_to_tray": self.minimize_tray_check.isChecked()
        }

        self._main_config["bridge"] = {
            "enabled": self.bridge_enabled_check.isChecked(),
            "host": self.bridge_host_edit.text() or "127.0.0.1",
            "port": self.bridge_port_spin.value()
        }

        self._main_config["monitor"] = {
            "refresh_interval": self.refresh_interval_spin.value(),
            "log_max_lines": self.log_max_lines_spin.value()
        }

        try:
            import json
            import os

            config_path = self._config_manager._main_config_path
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self._main_config, f, indent=2, ensure_ascii=False)

            I18nManager.load_locale(lang)

            self.settings_saved.emit()
            
            if lang != self._original_lang:
                QMessageBox.information(
                    self, 
                    tr("settings.title", "设置"),
                    tr("settings.restart_hint", "语言设置已更改，请重启应用以完全生效。")
                )
            
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, tr("error.warning", "警告"), str(e))
