from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QComboBox,
    QCheckBox, QGroupBox, QFormLayout, QSplitter, QFrame,
    QMessageBox, QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ...core import ConfigManager, WSLManager
from ...models import NanobotConfig


class ConfigPanel(QWidget):
    config_saved = pyqtSignal(str)

    def __init__(self, config_manager: ConfigManager, wsl_manager: WSLManager, parent=None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._wsl_manager = wsl_manager
        self._current_config: Optional[NanobotConfig] = None

        self._init_ui()
        self._load_configs()
        self._load_distros()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        left_panel = QFrame()
        left_panel.setFixedWidth(250)
        left_layout = QVBoxLayout(left_panel)

        header_layout = QHBoxLayout()
        title = QLabel("配置列表")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        header_layout.addWidget(title)
        header_layout.addStretch()

        new_btn = QPushButton("新建")
        new_btn.clicked.connect(self._new_config)
        import_btn = QPushButton("导入")
        import_btn.clicked.connect(self._import_config)
        header_layout.addWidget(new_btn)
        header_layout.addWidget(import_btn)

        left_layout.addLayout(header_layout)

        self.config_list = QListWidget()
        self.config_list.currentItemChanged.connect(self._on_config_selected)
        left_layout.addWidget(self.config_list)

        layout.addWidget(left_panel)

        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)

        config_title = QLabel("配置详情")
        config_title.setObjectName("configTitle")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        config_title.setFont(font)
        right_layout.addWidget(config_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(15)

        self.name_edit = QLineEdit()
        form_layout.addRow("名称:", self.name_edit)

        self.distro_combo = QComboBox()
        form_layout.addRow("WSL 分发:", self.distro_combo)

        ws_group = QGroupBox("工作空间")
        ws_layout = QVBoxLayout(ws_group)
        ws_form = QFormLayout()
        self.windows_ws_edit = QLineEdit()
        self.windows_ws_edit.setPlaceholderText("D:\\nanobot_workspace")
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self._browse_workspace)
        ws_row = QHBoxLayout()
        ws_row.addWidget(self.windows_ws_edit)
        ws_row.addWidget(browse_btn)
        ws_form.addRow("Windows:", ws_row)

        self.wsl_ws_label = QLabel("/mnt/d/nanobot_workspace")
        ws_form.addRow("WSL:", self.wsl_ws_label)

        self.sync_mnt_check = QCheckBox("同步到 /mnt 目录")
        self.sync_mnt_check.setChecked(True)
        self.sync_mnt_check.stateChanged.connect(self._on_sync_changed)
        ws_layout.addLayout(ws_form)
        ws_layout.addWidget(self.sync_mnt_check)
        form_layout.addRow(ws_group)

        llm_group = QGroupBox("LLM 配置")
        llm_layout = QFormLayout(llm_group)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["openrouter", "anthropic", "openai", "azure"])
        llm_layout.addRow("提供商:", self.provider_combo)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self._update_models()
        self.provider_combo.currentTextChanged.connect(self._update_models)
        llm_layout.addRow("模型:", self.model_combo)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("输入 API Key")
        show_key_btn = QPushButton("显示")
        show_key_btn.setCheckable(True)
        show_key_btn.toggled.connect(lambda checked: self.api_key_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        ))
        key_row = QHBoxLayout()
        key_row.addWidget(self.api_key_edit)
        key_row.addWidget(show_key_btn)
        llm_layout.addRow("API Key:", key_row)

        form_layout.addRow(llm_group)

        features_group = QGroupBox("功能开关")
        features_layout = QVBoxLayout(features_group)

        self.memory_check = QCheckBox("启用记忆功能")
        self.memory_check.setChecked(True)
        features_layout.addWidget(self.memory_check)

        self.web_search_check = QCheckBox("启用网络搜索")
        self.web_search_check.setChecked(True)
        features_layout.addWidget(self.web_search_check)

        brave_row = QHBoxLayout()
        self.brave_key_edit = QLineEdit()
        self.brave_key_edit.setPlaceholderText("Brave Search API Key (可选)")
        self.brave_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        brave_row.addWidget(self.brave_key_edit)
        features_layout.addLayout(brave_row)

        form_layout.addRow(features_group)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        form_layout.addRow("日志级别:", self.log_level_combo)

        scroll.setWidget(form_widget)
        right_layout.addWidget(scroll, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save_config)
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self._reset_form)
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self._delete_config)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(reset_btn)
        btn_layout.addWidget(delete_btn)
        right_layout.addLayout(btn_layout)

        layout.addWidget(right_panel, 1)

        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet("""
            QLabel#configTitle {
                color: #ffffff;
            }
            QFrame {
                background-color: #1e1e1e;
            }
            QListWidget {
                background-color: #2d2d30;
                color: #cccccc;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #094771;
            }
            QListWidget::item:hover:!selected {
                background-color: #2a2d2e;
            }
            QLineEdit, QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #5c5c5c;
                border-radius: 4px;
                padding: 6px 10px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #007acc;
            }
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
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
            QPushButton:pressed {
                background-color: #0d5a8a;
            }
            QScrollArea {
                border: none;
            }
        """)

    def _load_configs(self):
        self.config_list.clear()
        configs = self._config_manager.get_all()

        for name in sorted(configs.keys()):
            item = QListWidgetItem(name)
            if name == self._config_manager.get_default_name():
                item.setText(f"{name} (默认)")
            self.config_list.addItem(item)

        if configs:
            self.config_list.setCurrentRow(0)

    def _load_distros(self):
        distros = self._wsl_manager.list_distros()
        self.distro_combo.clear()
        for distro in distros:
            self.distro_combo.addItem(distro.name)

    def _update_models(self):
        provider = self.provider_combo.currentText()
        models = {
            "openrouter": [
                "anthropic/claude-sonnet-4-20250529",
                "anthropic/claude-3-opus",
                "openai/gpt-4o",
                "openai/gpt-4-turbo",
            ],
            "anthropic": [
                "claude-sonnet-4-20250529",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
            ],
            "openai": [
                "gpt-4o",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
            ],
            "azure": [
                "gpt-4o",
                "gpt-4-turbo",
            ],
        }
        self.model_combo.clear()
        self.model_combo.addItems(models.get(provider, []))

    def _on_config_selected(self, current, previous):
        if not current:
            return

        name = current.text().replace(" (默认)", "")
        config = self._config_manager.get(name)
        if config:
            self._current_config = config
            self._populate_form(config)

    def _populate_form(self, config: NanobotConfig):
        self.name_edit.setText(config.name)
        index = self.distro_combo.findText(config.distro_name)
        if index >= 0:
            self.distro_combo.setCurrentIndex(index)

        self.windows_ws_edit.setText(config.windows_workspace)
        self.sync_mnt_check.setChecked(config.sync_to_mnt)
        self._update_wsl_path()

        index = self.provider_combo.findText(config.provider)
        if index >= 0:
            self.provider_combo.setCurrentIndex(index)

        self.model_combo.setCurrentText(config.model)
        self.api_key_edit.setText(config.api_key)
        self.memory_check.setChecked(config.enable_memory)
        self.web_search_check.setChecked(config.enable_web_search)
        self.brave_key_edit.setText(config.brave_api_key or "")
        index = self.log_level_combo.findText(config.log_level)
        if index >= 0:
            self.log_level_combo.setCurrentIndex(index)

    def _on_sync_changed(self, state):
        self._update_wsl_path()

    def _update_wsl_path(self):
        windows_path = self.windows_ws_edit.text()
        if self.sync_mnt_check.isChecked() and windows_path:
            wsl_path = self._wsl_manager.convert_windows_to_wsl_path(windows_path)
            self.wsl_ws_label.setText(wsl_path)
        else:
            self.wsl_ws_label.setText("--")

    def _browse_workspace(self):
        folder = QFileDialog.getExistingDirectory(self, "选择工作空间目录")
        if folder:
            self.windows_ws_edit.setText(folder)
            self._update_wsl_path()

    def _new_config(self):
        self._current_config = None
        self._reset_form()

        distros = self._wsl_manager.list_distros()
        default_distro = next((d for d in distros if d.is_default), None)
        if default_distro:
            self.distro_combo.setCurrentText(default_distro.name)

        self.name_edit.setFocus()

    def _import_config(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置", "", "JSON Files (*.json)"
        )
        if file_path:
            import json
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                config = NanobotConfig.from_dict(data)
                self._config_manager.save(config)
                self._load_configs()
                QMessageBox.information(self, "成功", f"已导入配置: {config.name}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导入失败: {e}")

    def _save_config(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "请输入配置名称")
            return

        distro_name = self.distro_combo.currentText()
        if not distro_name:
            QMessageBox.warning(self, "错误", "请选择 WSL 分发")
            return

        windows_ws = self.windows_ws_edit.text().strip()
        wsl_ws = ""
        if self.sync_mnt_check.isChecked() and windows_ws:
            wsl_ws = self._wsl_manager.convert_windows_to_wsl_path(windows_ws)

        config = NanobotConfig(
            name=name,
            distro_name=distro_name,
            workspace=wsl_ws,
            windows_workspace=windows_ws,
            sync_to_mnt=self.sync_mnt_check.isChecked(),
            provider=self.provider_combo.currentText(),
            model=self.model_combo.currentText(),
            api_key=self.api_key_edit.text(),
            enable_memory=self.memory_check.isChecked(),
            enable_web_search=self.web_search_check.isChecked(),
            brave_api_key=self.brave_key_edit.text() or None,
            log_level=self.log_level_combo.currentText(),
        )

        if self._config_manager.save(config):
            self._current_config = config
            self._load_configs()
            self.config_saved.emit(name)
            QMessageBox.information(self, "成功", f"已保存配置: {name}")
        else:
            QMessageBox.warning(self, "错误", "保存配置失败")

    def _reset_form(self):
        if self._current_config:
            self._populate_form(self._current_config)
        else:
            self.name_edit.clear()
            self.windows_ws_edit.clear()
            self.api_key_edit.clear()
            self.brave_key_edit.clear()
            self.memory_check.setChecked(True)
            self.web_search_check.setChecked(True)
            self.sync_mnt_check.setChecked(True)

    def _delete_config(self):
        if not self._current_config:
            return

        name = self._current_config.name
        reply = QMessageBox.question(
            self, "确认", f"确定要删除配置 '{name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self._config_manager.delete(name):
                self._current_config = None
                self._load_configs()
                QMessageBox.information(self, "成功", f"已删除配置: {name}")
