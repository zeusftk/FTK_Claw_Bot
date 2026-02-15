from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QComboBox,
    QCheckBox, QFrame, QScrollArea, QSizePolicy, QFileDialog,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ...core import ConfigManager, WSLManager
from ...models import NanobotConfig


class ConfigCard(QFrame):
    """配置卡片组件"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("configCard")
        self._init_ui(title)
    
    def _init_ui(self, title: str):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 16, 20, 16)
        self.main_layout.setSpacing(16)
        
        # 标题
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        title_label.setFont(font)
        self.main_layout.addWidget(title_label)
        
        # 内容区域
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        self.main_layout.addWidget(self.content_widget)
    
    def add_row(self, label_text: str, widget) -> QHBoxLayout:
        """添加一行配置项"""
        row = QHBoxLayout()
        row.setSpacing(12)
        
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        label.setFixedWidth(100)
        row.addWidget(label)
        
        if isinstance(widget, QHBoxLayout):
            row.addLayout(widget, 1)
        else:
            row.addWidget(widget, 1)
        
        self.content_layout.addLayout(row)
        return row
    
    def add_widget(self, widget):
        """添加任意控件"""
        self.content_layout.addWidget(widget)
    
    def add_layout(self, layout):
        """添加布局"""
        self.content_layout.addLayout(layout)


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
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # 左侧配置列表
        left_panel = self._create_left_panel()
        layout.addWidget(left_panel)

        # 右侧配置详情
        right_panel = self._create_right_panel()
        layout.addWidget(right_panel, 1)

    def _create_left_panel(self) -> QFrame:
        """创建左侧面板"""
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setFixedWidth(280)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 标题和按钮
        header = QHBoxLayout()
        title = QLabel("配置列表")
        title.setObjectName("panelTitle")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()

        new_btn = QPushButton("新建")
        new_btn.setObjectName("smallButton")
        new_btn.clicked.connect(self._new_config)
        import_btn = QPushButton("导入")
        import_btn.setObjectName("smallButton")
        import_btn.clicked.connect(self._import_config)
        header.addWidget(new_btn)
        header.addWidget(import_btn)

        layout.addLayout(header)

        # 配置列表
        self.config_list = QListWidget()
        self.config_list.setObjectName("configList")
        self.config_list.currentItemChanged.connect(self._on_config_selected)
        layout.addWidget(self.config_list)

        return panel

    def _create_right_panel(self) -> QFrame:
        """创建右侧面板"""
        panel = QFrame()
        panel.setObjectName("rightPanel")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # 标题
        header = QHBoxLayout()
        self.config_title = QLabel("配置详情")
        self.config_title.setObjectName("panelTitle")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.config_title.setFont(font)
        header.addWidget(self.config_title)
        header.addStretch()
        layout.addLayout(header)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        # 内容容器
        content = QWidget()
        content.setObjectName("configContent")
        self.form_layout = QVBoxLayout(content)
        self.form_layout.setContentsMargins(0, 0, 20, 0)
        self.form_layout.setSpacing(20)

        # 基本信息卡片
        basic_card = ConfigCard("基本信息")
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入配置名称...")
        basic_card.add_row("配置名称", self.name_edit)

        self.distro_combo = QComboBox()
        basic_card.add_row("WSL 分发", self.distro_combo)
        
        self.form_layout.addWidget(basic_card)

        # 工作空间卡片
        workspace_card = ConfigCard("工作空间")
        
        ws_row = QHBoxLayout()
        ws_row.setSpacing(8)
        self.windows_ws_edit = QLineEdit()
        self.windows_ws_edit.setPlaceholderText("D:\\nanobot_workspace")
        browse_btn = QPushButton("浏览")
        browse_btn.setObjectName("smallButton")
        browse_btn.clicked.connect(self._browse_workspace)
        ws_row.addWidget(self.windows_ws_edit)
        ws_row.addWidget(browse_btn)
        workspace_card.add_row("Windows", ws_row)

        self.wsl_ws_label = QLabel("--")
        self.wsl_ws_label.setObjectName("pathLabel")
        workspace_card.add_row("WSL 路径", self.wsl_ws_label)

        self.sync_mnt_check = QCheckBox("同步到 /mnt 目录")
        self.sync_mnt_check.setChecked(True)
        self.sync_mnt_check.stateChanged.connect(self._on_sync_changed)
        workspace_card.add_widget(self.sync_mnt_check)
        
        self.form_layout.addWidget(workspace_card)

        # LLM 配置卡片
        llm_card = ConfigCard("LLM 配置")
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["openrouter", "anthropic", "openai", "azure"])
        self.provider_combo.currentTextChanged.connect(self._update_models)
        llm_card.add_row("提供商", self.provider_combo)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self._update_models()
        llm_card.add_row("模型", self.model_combo)

        key_row = QHBoxLayout()
        key_row.setSpacing(8)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("输入 API Key")
        show_key_btn = QPushButton("显示")
        show_key_btn.setObjectName("smallButton")
        show_key_btn.setCheckable(True)
        show_key_btn.toggled.connect(lambda checked: self.api_key_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        ))
        key_row.addWidget(self.api_key_edit)
        key_row.addWidget(show_key_btn)
        llm_card.add_row("API Key", key_row)
        
        self.form_layout.addWidget(llm_card)

        # 功能开关卡片
        features_card = ConfigCard("功能开关")
        
        self.memory_check = QCheckBox("启用记忆功能")
        self.memory_check.setChecked(True)
        features_card.add_widget(self.memory_check)

        self.web_search_check = QCheckBox("启用网络搜索")
        self.web_search_check.setChecked(True)
        features_card.add_widget(self.web_search_check)

        brave_row = QHBoxLayout()
        brave_row.setSpacing(8)
        brave_label = QLabel("Brave Key:")
        brave_label.setObjectName("fieldLabel")
        brave_label.setFixedWidth(100)
        self.brave_key_edit = QLineEdit()
        self.brave_key_edit.setPlaceholderText("Brave Search API Key (可选)")
        self.brave_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        brave_row.addWidget(brave_label)
        brave_row.addWidget(self.brave_key_edit)
        features_card.add_layout(brave_row)
        
        self.form_layout.addWidget(features_card)

        # 日志级别卡片
        log_card = ConfigCard("日志设置")
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        log_card.add_row("日志级别", self.log_level_combo)
        
        self.form_layout.addWidget(log_card)

        self.form_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存配置")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_config)
        
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self._reset_form)
        
        delete_btn = QPushButton("删除")
        delete_btn.setObjectName("dangerButton")
        delete_btn.clicked.connect(self._delete_config)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(reset_btn)
        btn_layout.addWidget(delete_btn)
        layout.addLayout(btn_layout)

        return panel

    def _apply_styles(self):
        # 样式已在全局样式表中定义
        pass

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

    def refresh_distros(self):
        """Refresh the distro list (public method for external calls)."""
        self._load_distros()

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
        self.config_title.setText(f"配置详情: {config.name}")
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
        self.config_title.setText("配置详情")
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
