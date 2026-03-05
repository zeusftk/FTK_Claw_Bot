# -*- coding: utf-8 -*-
import json
import threading
from typing import Optional, List, Dict

from loguru import logger

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QComboBox,
    QCheckBox, QFrame, QScrollArea, QFileDialog,
    QMessageBox, QDialog, QTabWidget, QApplication, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ...core import ConfigManager, WSLManager
from ...models import ClawbotConfig, CHANNEL_INFO, ChannelsConfig
from ...models.clawbot_config import ProviderConfigItem, MultiModelConfigItem
from ...services import ServiceRegistry
from ...utils.async_ops import AsyncOperation, AsyncResult
from ...utils.thread_safe import ThreadSafeSignal
from ...utils.i18n import tr
from ..mixins import WSLStateAwareMixin
from .channel_config_dialog import get_channel_dialog
from .skills_config_widget import SkillsConfigWidget
from .multi_model_config_widget import MultiModelConfigWidget
from .whitelist_panel import WhitelistPanel


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


class ConfigPanel(QWidget, WSLStateAwareMixin):
    config_saved = pyqtSignal(str)

    def __init__(self, config_manager: ConfigManager, wsl_manager: WSLManager, clawbot_controller=None, parent=None):
        super().__init__(parent)
        WSLStateAwareMixin._init_wsl_state_aware(self)
        self._config_manager = config_manager
        self._wsl_manager = wsl_manager
        self._clawbot_controller = clawbot_controller
        self._current_config: Optional[ClawbotConfig] = None

        self._init_ui()
        self._load_configs()
        self._load_distros()

        # 加载状态管理
        self._is_loading = False
        self._loading_overlay = None

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
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setFixedWidth(280)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel(tr("config.title", "WSL 分发"))
        title.setObjectName("panelTitle")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setObjectName("smallButton")
        refresh_btn.setToolTip(tr("btn.refresh", "刷新"))
        refresh_btn.clicked.connect(self._refresh_data)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        self.config_list = QListWidget()
        self.config_list.setObjectName("configList")
        self.config_list.currentItemChanged.connect(self._on_config_selected)
        layout.addWidget(self.config_list)

        return panel

    def _create_right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("rightPanel")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        header = QHBoxLayout()
        self.config_title = QLabel(tr("config.details", "配置详情"))
        self.config_title.setObjectName("panelTitle")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.config_title.setFont(font)
        header.addWidget(self.config_title)
        header.addStretch()
        layout.addLayout(header)

        self._tab_widget = QTabWidget()
        self._tab_widget.setObjectName("configTabWidget")
        
        basic_tab = self._create_basic_settings_tab()
        self._tab_widget.addTab(basic_tab, tr("config.tab.basic", "基础设置"))
        
        skills_tab = self._create_skills_tab()
        self._tab_widget.addTab(skills_tab, tr("config.tab.skills", "技能配置"))
        
        whitelist_tab = self._create_whitelist_tab()
        self._tab_widget.addTab(whitelist_tab, tr("config.tab.whitelist", "白名单"))
        
        layout.addWidget(self._tab_widget, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton(tr("btn.save", "保存"))
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_config)
        
        reset_btn = QPushButton(tr("btn.reset", "重置"))
        reset_btn.clicked.connect(self._reset_form)
        
        set_default_btn = QPushButton(tr("btn.confirm", "确认"))
        set_default_btn.clicked.connect(self._set_default_config)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(reset_btn)
        btn_layout.addWidget(set_default_btn)
        layout.addLayout(btn_layout)

        return panel

    def _create_skills_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # 创建技能配置 widget，传入 WSL 管理器
        self._skills_widget = SkillsConfigWidget(
            wsl_manager=self._wsl_manager,
            distro_name="",  # 将在加载配置时设置
            workspace=""
        )
        self._skills_widget.config_changed.connect(self._on_skills_config_changed)
        layout.addWidget(self._skills_widget)
        
        return tab

    def _create_whitelist_tab(self) -> QWidget:
        """创建白名单管理标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建白名单管理 widget
        self._whitelist_widget = WhitelistPanel()
        self._whitelist_widget.config_changed.connect(self._on_whitelist_changed)
        layout.addWidget(self._whitelist_widget)
        
        return tab

    def _on_whitelist_changed(self):
        """白名单配置变更回调"""
        logger.info("白名单配置已变更")

    def _create_basic_settings_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content.setObjectName("configContent")
        self.form_layout = QVBoxLayout(content)
        self.form_layout.setContentsMargins(0, 0, 20, 0)
        self.form_layout.setSpacing(20)

        basic_card = ConfigCard(tr("config.card.basic_info", "基本信息"))
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(tr("config.placeholder.name_equals_distro", "配置名称等于WSL分发名称"))
        self.name_edit.setReadOnly(True)
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #8b949e;
                font-size: 14px;
            }
        """)
        basic_card.add_row(tr("config.label.name", "配置名称"), self.name_edit)

        self.distro_combo = QComboBox()
        self.distro_combo.setEnabled(False)
        self.distro_combo.setStyleSheet("""
            QComboBox {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #8b949e;
                font-size: 14px;
            }
        """)
        basic_card.add_row(tr("config.label.distro", "WSL 分发"), self.distro_combo)
        
        self.form_layout.addWidget(basic_card)

        workspace_card = ConfigCard(tr("config.card.workspace", "工作空间"))
        
        ws_row = QHBoxLayout()
        ws_row.setSpacing(8)
        self.windows_ws_edit = QLineEdit()
        self.windows_ws_edit.setPlaceholderText(tr("config.placeholder.windows_workspace", "D:\\clawbot_workspace"))
        browse_btn = QPushButton(tr("config.label.browse", "浏览"))
        browse_btn.setObjectName("smallButton")
        browse_btn.clicked.connect(self._browse_workspace)
        ws_row.addWidget(self.windows_ws_edit)
        ws_row.addWidget(browse_btn)
        workspace_card.add_row(tr("config.label.windows", "Windows"), ws_row)

        self.wsl_ws_label = QLabel("--")
        self.wsl_ws_label.setObjectName("pathLabel")
        workspace_card.add_row(tr("config.label.wsl_path", "WSL 路径"), self.wsl_ws_label)

        self.sync_mnt_check = QCheckBox(tr("config.label.sync_to_mnt", "同步到 /mnt 目录"))
        self.sync_mnt_check.setChecked(True)
        self.sync_mnt_check.stateChanged.connect(self._on_sync_changed)
        workspace_card.add_widget(self.sync_mnt_check)
        
        self.form_layout.addWidget(workspace_card)

        # LLM 配置卡片（统一的多模型配置界面）
        llm_card = ConfigCard(tr("config.card.llm", "LLM 配置"))
        
        # 多模型配置区域
        self.multi_model_widget = MultiModelConfigWidget()
        self.multi_model_widget.config_changed.connect(self._on_multi_model_changed)
        llm_card.add_widget(self.multi_model_widget)
        
        self.form_layout.addWidget(llm_card)

        gateway_card = ConfigCard(tr("config.card.gateway", "Gateway 设置"))
        
        self.gateway_host_edit = QLineEdit()
        self.gateway_host_edit.setPlaceholderText(tr("config.placeholder.gateway_host", "0.0.0.0"))
        self.gateway_host_edit.hide()
        
        gateway_port_row = QHBoxLayout()
        gateway_port_row.setSpacing(8)
        self.gateway_port_edit = QLineEdit()
        self.gateway_port_edit.setPlaceholderText(tr("config.placeholder.gateway_port", "18888"))
        gateway_port_row.addWidget(self.gateway_port_edit)
        
        self.gateway_port_hint_label = QLabel("")
        self.gateway_port_hint_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        gateway_port_row.addWidget(self.gateway_port_hint_label)
        
        gateway_card.add_row(tr("config.label.port", "Port"), gateway_port_row)
        
        self.gateway_port_edit.textChanged.connect(self._validate_gateway_port)
        
        self.form_layout.addWidget(gateway_card)

        memory_card = ConfigCard(tr("config.card.memory", "Memory 设置"))

        self.memory_check = QCheckBox(tr("config.label.enable_memory", "启用记忆功能"))
        self.memory_check.setChecked(True)
        memory_card.add_widget(self.memory_check)

        self.memory_enabled_check = QCheckBox(tr("config.label.enable_memory_api", "启用 Embedding API"))
        memory_card.add_widget(self.memory_enabled_check)
        
        embedding_url_row = QHBoxLayout()
        embedding_url_row.setSpacing(8)
        self.embedding_url_edit = QLineEdit()
        self.embedding_url_edit.setPlaceholderText(tr("config.placeholder.embedding_url", "http://localhost:18765"))
        self.embedding_url_edit.setText(self._get_default_embedding_url())
        
        use_default_btn = QPushButton(tr("config.label.use_default", "使用默认"))
        use_default_btn.setObjectName("smallButton")
        use_default_btn.clicked.connect(self._use_default_embedding_url)
        embedding_url_row.addWidget(self.embedding_url_edit)
        embedding_url_row.addWidget(use_default_btn)
        memory_card.add_row(tr("config.label.embedding_url", "Embedding URL"), embedding_url_row)
        
        self.form_layout.addWidget(memory_card)

        channels_card = self._create_channels_card()
        self.form_layout.addWidget(channels_card)

        log_card = ConfigCard(tr("config.card.log", "日志设置"))

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        log_card.add_row(tr("config.label.log_level", "日志级别"), self.log_level_combo)

        self.form_layout.addWidget(log_card)

        features_card = ConfigCard(tr("config.card.features", "功能开关"))

        self.web_search_check = QCheckBox(tr("config.label.enable_web_search", "启用网络搜索"))
        self.web_search_check.setChecked(True)
        features_card.add_widget(self.web_search_check)

        brave_row = QHBoxLayout()
        brave_row.setSpacing(8)
        brave_label = QLabel(tr("config.label.brave_key", "Brave Key:"))
        brave_label.setObjectName("fieldLabel")
        brave_label.setFixedWidth(100)
        self.brave_key_edit = QLineEdit()
        self.brave_key_edit.setPlaceholderText(tr("config.placeholder.brave_key", "Brave Search API Key (可选)"))
        self.brave_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        brave_row.addWidget(brave_label)
        brave_row.addWidget(self.brave_key_edit)
        features_card.add_layout(brave_row)

        self.form_layout.addWidget(features_card)

        self.form_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return tab

    def _apply_styles(self):
        pass

    def _create_channels_card(self) -> ConfigCard:
        channels_card = ConfigCard(tr("config.card.channels", "Channels 配置"))
        
        self._channel_items: dict[str, dict] = {}
        
        for channel_name, channel_info in CHANNEL_INFO.items():
            item_widget = QFrame()
            item_widget.setObjectName("channelItem")
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(8, 6, 8, 6)
            item_layout.setSpacing(12)
            
            icon_label = QLabel(channel_info.get("icon", "📡"))
            icon_label.setStyleSheet("font-size: 16px;")
            icon_label.setFixedWidth(24)
            item_layout.addWidget(icon_label)
            
            info_layout = QVBoxLayout()
            info_layout.setSpacing(2)
            
            name_label = QLabel(channel_info.get("name", channel_name))
            name_label.setStyleSheet("font-weight: bold; font-size: 12px;")
            info_layout.addWidget(name_label)
            
            desc_label = QLabel(channel_info.get("description", ""))
            desc_label.setStyleSheet("color: #8b949e; font-size: 10px;")
            info_layout.addWidget(desc_label)
            
            item_layout.addLayout(info_layout, 1)
            
            enable_check = QCheckBox(tr("config.label.enable", "启用"))
            enable_check.setObjectName("channelEnableCheck")
            item_layout.addWidget(enable_check)
            
            config_btn = QPushButton(tr("config.label.configure", "配置"))
            config_btn.setObjectName("smallButton")
            config_btn.setFixedWidth(60)
            item_layout.addWidget(config_btn)
            
            self._channel_items[channel_name] = {
                "widget": item_widget,
                "enable_check": enable_check,
                "config_btn": config_btn,
            }
            
            enable_check.stateChanged.connect(
                lambda state, cn=channel_name: self._on_channel_enabled(cn, state)
            )
            config_btn.clicked.connect(
                lambda checked, cn=channel_name: self._on_channel_config(cn)
            )
            
            channels_card.add_widget(item_widget)
        
        return channels_card

    def _on_channel_enabled(self, channel_name: str, state: int):
        if not self._current_config:
            return
        
        enabled = state == Qt.CheckState.Checked.value
        channel_config = getattr(self._current_config.channels, channel_name, None)
        if channel_config:
            channel_config.enabled = enabled

    def _on_channel_config(self, channel_name: str):
        if not self._current_config:
            return
        
        channel_config = getattr(self._current_config.channels, channel_name, None)
        if not channel_config:
            return
        
        dialog = get_channel_dialog(channel_name, channel_config, self)
        if dialog and dialog.exec() == QDialog.DialogCode.Accepted:
            new_config = dialog.get_config()
            setattr(self._current_config.channels, channel_name, new_config)
            self._update_channel_ui(channel_name, new_config)

    def _update_channel_ui(self, channel_name: str, config):
        if channel_name not in self._channel_items:
            return
        
        item = self._channel_items[channel_name]
        item["enable_check"].setChecked(config.enabled)

    def _on_skills_config_changed(self):
        pass

    def _load_channel_configs(self):
        if not self._current_config:
            return
        
        for channel_name, item in self._channel_items.items():
            channel_config = getattr(self._current_config.channels, channel_name, None)
            if channel_config:
                item["enable_check"].setChecked(channel_config.enabled)

    def _load_skills_config(self):
        if not self._current_config:
            return
        
        # 设置 WSL 上下文
        self._skills_widget.set_wsl_context(
            self._wsl_manager,
            self._current_config.distro_name,
            self._current_config.workspace
        )
        
        self._skills_widget.set_config(self._current_config.skills)

    def _load_configs(self):
        self.config_list.clear()
        
        distros = self._wsl_manager.list_distros()
        logger.info(f"重新加载配置，WSL 分发: {[d.name for d in distros]}")
        
        for distro in distros:
            config = self._config_manager.get(distro.name)
            if not config:
                config = ClawbotConfig(
                    name=distro.name,
                    distro_name=distro.name
                )
                self._config_manager.save(config)
                logger.info(f"为 WSL 分发 '{distro.name}' 创建新配置")
            
            # 尝试从WSL读取配置
            if self._clawbot_controller:
                try:
                    distro_obj = self._wsl_manager.get_distro(distro.name)
                    distro_running = distro_obj and distro_obj.is_running
                    
                    if not distro_running:
                        logger.info(f"WSL 分发 '{distro.name}' 未运行，尝试启动")
                        self._wsl_manager.start_distro(distro.name)
                    
                    wsl_config = self._clawbot_controller.read_config_from_wsl(distro.name)
                    if wsl_config and wsl_config != {}:
                        logger.info(f"从 WSL 分发 '{distro.name}' 读取到配置")
                        self._config_manager.apply_wsl_config_to_ftk(config, wsl_config, self._wsl_manager)
                        self._config_manager.save(config)
                except Exception as e:
                    logger.warning(f"初始化时从 WSL 分发 '{distro.name}' 读取配置失败: {e}")
        
        # 显示所有WSL分发
        default_name = self._config_manager.get_default_name()
        
        for distro in distros:
            item = QListWidgetItem(distro.name)
            if distro.name == default_name:
                item.setText(f"{distro.name}{tr('config.msg.default_suffix', ' (默认)')}")
            self.config_list.addItem(item)

        if distros:
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
            "custom": [],
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
            "openrouter": [
                "anthropic/claude-sonnet-4-20250529",
                "anthropic/claude-3-opus",
                "openai/gpt-4o",
                "openai/gpt-4-turbo",
            ],
            "deepseek": [
                "deepseek-chat",
                "deepseek-coder",
            ],
            "groq": [
                "llama-3.3-70b-versatile",
                "llama-3.1-70b-versatile",
                "mixtral-8x7b-32768",
            ],
            "zhipu": [
                "glm-4-plus",
                "glm-4",
                "glm-3-turbo",
            ],
            "dashscope": [
                "qwen-max",
                "qwen-plus",
                "qwen-turbo",
            ],
            "siliconflow": [],
            "volcengine": [],
            "vllm": [],
            "ollama": [
                "qwen3.5:9b",
                "glm-5:cloud",
                "qwen3.5:397b-cloud",
                "minimax-m2.5:cloud",
                "kimi-k2.5:cloud",
            ],
            "gemini": [
                "gemini-2.0-flash-exp",
                "gemini-2.0-flash",
                "gemini-1.5-pro",
            ],
            "moonshot": [
                "moonshot-v1-128k",
                "moonshot-v1-32k",
                "moonshot-v1-8k",
            ],
            "minimax": [
                "abab6.5s",
                "abab6.5",
                "abab6",
            ],
            "aihubmix": [],
            "qwen_portal": [
                "qwen-portal/coder-model",
                "qwen-portal/qwen-max",
            ],
            "openai_codex": [
                "codex",
            ],
            "github_copilot": [
                "github_copilot/gpt-4o",
                "github_copilot/claude-3.5-sonnet",
            ],
            "doubao_web": [],
            "deepseek_web": [],
        }
        self.model_combo.clear()
        self.model_combo.addItems(models.get(provider, []))

    def _on_provider_changed(self, provider: str):
        """当提供商变更时显示/隐藏 URL 输入框"""
        # OAuth 提供商列表（与 clawbot registry.py 保持一致）
        oauth_providers = {"qwen_portal", "openai_codex", "github_copilot", "doubao_web", "deepseek_web"}
        is_oauth = provider in oauth_providers
        
        # 本地部署提供商，需要启用自定义 URL
        local_providers = {"custom", "vllm", "ollama"}
        is_local = provider in local_providers
        
        self.apiKey_edit.setVisible(not is_oauth)
        self.oauth_status_label.setVisible(is_oauth)
        self.oauth_login_btn.setVisible(is_oauth)
        
        if is_local:
            self.base_url_edit.setEnabled(True)
            # 清空并设置默认 URL
            self.base_url_edit.setText("")
            self.base_url_edit.setPlaceholderText("")
            if provider == "ollama":
                self.base_url_edit.setText("http://localhost:11434/v1")
            elif provider == "vllm":
                self.base_url_edit.setPlaceholderText("http://localhost:8000/v1")
            # custom 提供商不设置默认值，让用户自己填写
        else:
            self.base_url_edit.setEnabled(False)
            self.base_url_edit.setText("")
        
        if is_oauth:
            self._check_oauth_status()

    def _validate_gateway_port(self):
        """验证 Gateway 端口唯一性"""
        port_text = self.gateway_port_edit.text().strip()
        
        if not port_text:
            self.gateway_port_hint_label.setText("")
            return True
        
        try:
            port = int(port_text)
        except ValueError:
            self.gateway_port_hint_label.setText(tr("config.msg.port_valid_number", "⚠ 请输入有效数字"))
            self.gateway_port_hint_label.setStyleSheet("color: #f85149; font-size: 12px;")
            return False
        
        if port < 1024 or port > 65535:
            self.gateway_port_hint_label.setText(tr("config.msg.port_range", "⚠ 端口范围: 1024-65535"))
            self.gateway_port_hint_label.setStyleSheet("color: #f85149; font-size: 12px;")
            return False
        
        current_distro = self._current_config.distro_name if self._current_config else ""
        existing_ports = {}
        for config in self._config_manager.get_all().values():
            if config.distro_name != current_distro and config.gateway_port:
                existing_ports[config.gateway_port] = config.distro_name
        
        if port in existing_ports:
            self.gateway_port_hint_label.setText(tr("config.msg.port_in_use", "⚠ 已被 '{name}' 使用").format(name=existing_ports[port]))
            self.gateway_port_hint_label.setStyleSheet("color: #f85149; font-size: 12px;")
            return False
        else:
            self.gateway_port_hint_label.setText(tr("config.msg.port_available", "✓ 端口可用"))
            self.gateway_port_hint_label.setStyleSheet("color: #3fb950; font-size: 12px;")
            return True

    def _on_config_selected(self, current, previous):
        if not current:
            return
        
        name = current.text().replace(tr('config.msg.default_suffix', ' (默认)'), "")
        config = self._config_manager.get(name)
        if config:
            # 确保配置名称等于WSL分发名称
            if config.name != name or config.distro_name != name:
                config.name = name
                config.distro_name = name
                self._config_manager.save(config)
            
            self._current_config = config
            self._populate_form(config)

    def _populate_form(self, config: ClawbotConfig):
        self.config_title.setText(f"{tr('config.details', '配置详情')}: {config.name}")
        self.name_edit.setText(config.name)
        index = self.distro_combo.findText(config.distro_name)
        if index >= 0:
            self.distro_combo.setCurrentIndex(index)

        self.windows_ws_edit.setText(config.windows_workspace)
        self.sync_mnt_check.setChecked(config.sync_to_mnt)
        self._update_wsl_path()

        self.memory_check.setChecked(config.enable_memory)
        self.web_search_check.setChecked(config.enable_web_search)
        self.brave_key_edit.setText(config.brave_apiKey or "")
        index = self.log_level_combo.findText(config.log_level)
        if index >= 0:
            self.log_level_combo.setCurrentIndex(index)
        
        self.gateway_host_edit.setText(config.gateway_host)
        self.gateway_port_edit.setText(str(config.gateway_port))
        self._validate_gateway_port()
        
        self.embedding_url_edit.setText(config.embedding_url or self._get_default_embedding_url())
        self.memory_enabled_check.setChecked(config.embedding_enabled)
        
        # 加载多模型配置（传递 wsl_manager 和 distro_name 用于 OAuth 登录）
        self.multi_model_widget.set_config(
            config.providers, 
            config.multi_model,
            wsl_manager=self._wsl_manager,
            distro_name=config.distro_name
        )
        
        self._load_channel_configs()
        self._load_skills_config()

    def _quick_add_model(self):
        """快速添加模型到列表"""
        provider = self.provider_combo.currentText()
        model = self.model_combo.currentText()
        api_key = self.apiKey_edit.text()
        base_url = self.base_url_edit.text()
        
        if not model:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("error.model_required", "请选择或输入模型名称"))
            return
        
        # 创建模型配置
        from ...models.clawbot_config import ModelConfigItem, ProviderConfigItem
        
        model_config = ModelConfigItem(
            name=model,
            provider=provider,
            alias="",  # 用户可以在列表中编辑
            capabilities=[],
            cost_tier="medium",
            max_tokens=4096,
            priority=1,
            enabled=True,
        )
        
        # 添加到多模型配置
        providers, multi_config = self.multi_model_widget.get_config()
        multi_config.models.append(model_config)
        
        # 确保 provider 在列表中
        provider_exists = any(p.name == provider for p in providers)
        if not provider_exists and api_key:
            providers.append(ProviderConfigItem(
                name=provider,
                api_key=api_key,
                base_url=base_url,
                enabled=True,
            ))
        
        # 更新 UI
        self.multi_model_widget.set_config(providers, multi_config)
        
        # 清空输入
        self.model_combo.setCurrentText("")
        self.apiKey_edit.clear()
        self.base_url_edit.clear()
        
        logger.info(f"快速添加模型: {provider}/{model}")

    def _on_multi_model_changed(self):
        """多模型配置变更回调"""
        # 可以在这里添加实时验证或提示逻辑
        pass

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
        folder = QFileDialog.getExistingDirectory(self, tr("config.msg.select_workspace", "选择工作空间目录"))
        if folder:
            self.windows_ws_edit.setText(folder)
            self._update_wsl_path()

    def _get_default_embedding_url(self) -> str:
        """获取默认的 Embedding URL（本地服务）"""
        service = ServiceRegistry.get("embedding")
        if service:
            info = service.get_status()
            if info.port:
                from .local_services_panel import get_windows_host_ip
                host_ip = get_windows_host_ip()
                return f"http://{host_ip}:{info.port}"
        return "http://localhost:18765"
    
    def _use_default_embedding_url(self):
        """使用默认的 Embedding URL"""
        self.embedding_url_edit.setText(self._get_default_embedding_url())

    def _new_config(self):
        self._current_config = None
        self.config_title.setText(tr("config.details", "配置详情"))
        self._reset_form()

        distros = self._wsl_manager.list_distros()
        default_distro = next((d for d in distros if d.is_default), None)
        if default_distro:
            self.distro_combo.setCurrentText(default_distro.name)

        self.name_edit.setFocus()

    def _import_config(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("config.msg.import_config", "导入配置"), "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                config = ClawbotConfig.from_dict(data)
                
                # 验证唯一性
                all_configs = self._config_manager.get_all()
                
                # 检查配置名称
                if config.name in all_configs:
                    QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.name_exists", "配置名称 '{name}' 已存在，无法导入").format(name=config.name))
                    return
                
                # 检查WSL分发
                if config.distro_name:
                    for existing_config in all_configs.values():
                        if existing_config.distro_name == config.distro_name:
                            QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.distro_in_use", "WSL 分发 '{distro}' 已被配置 '{name}' 使用，无法导入").format(distro=config.distro_name, name=existing_config.name))
                            return
                
                self._config_manager.save(config)
                self._load_configs()
                QMessageBox.information(self, tr("error.success", "成功"), tr("config.msg.imported", "已导入配置: {name}").format(name=config.name))
            except Exception as e:
                QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.import_failed", "导入失败: {error}").format(error=e))

    def _save_config(self):
        if not self._current_config:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.select_config_first", "请先选择一个配置"))
            return

        # 配置名称等于WSL分发名称，不允许修改
        name = self._current_config.name
        distro_name = self._current_config.distro_name

        windows_ws = self.windows_ws_edit.text().strip()
        wsl_ws = ""
        if self.sync_mnt_check.isChecked() and windows_ws:
            wsl_ws = self._wsl_manager.convert_windows_to_wsl_path(windows_ws)
        
        gateway_port = 18790
        try:
            gateway_port = int(self.gateway_port_edit.text())
        except ValueError:
            pass

        logger.info("========== 开始保存配置流程 ==========")
        logger.info(f"配置名称: {name}")
        logger.info(f"分发名称: {distro_name}")
        logger.info(f"Windows 工作空间: {windows_ws}")
        logger.info(f"WSL 工作空间: {wsl_ws}")
        logger.info(f"Enable Memory: {self.memory_check.isChecked()}")
        logger.info(f"Enable Web Search: {self.web_search_check.isChecked()}")
        logger.info(f"Gateway Port: {gateway_port}")

        # 获取多模型配置
        providers, multi_model = self.multi_model_widget.get_config()
        
        # 根据模型数量自动判断模式
        # 0 个模型 = 需要用户添加模型
        # 1 个模型 = 单一模型模式（始终使用该模型）
        # 多个模型 = 多模型智能路由模式
        model_count = len(multi_model.models)
        
        if model_count == 0:
            # 没有模型配置，提示用户添加模型
            QMessageBox.warning(
                self, 
                tr("error.title", "错误"), 
                tr("error.no_model_config", "请至少添加一个模型配置")
            )
            return
        
        if model_count == 1:
            # 单一模型模式
            multi_model.enabled = False
            logger.info("模式: 单一模型（1 个模型配置）")
        else:
            # 多模型智能路由模式
            multi_model.enabled = True
            logger.info(f"模式: 多模型智能路由（{model_count} 个模型配置）")
        
        # 获取第一个模型的 provider 作为默认 provider（向后兼容）
        first_model = multi_model.models[0]
        default_provider = first_model.provider
        default_model = f"{first_model.provider}/{first_model.name}"
        
        config = ClawbotConfig(
            name=name,
            distro_name=distro_name,
            workspace=wsl_ws,
            windows_workspace=windows_ws,
            sync_to_mnt=self.sync_mnt_check.isChecked(),
            provider=default_provider,
            model=default_model,
            apiKey="",  # API Key 现在存储在 providers 列表中
            base_url="",
            enable_memory=self.memory_check.isChecked(),
            enable_web_search=self.web_search_check.isChecked(),
            brave_apiKey=self.brave_key_edit.text() or None,
            log_level=self.log_level_combo.currentText(),
            gateway_host=self.gateway_host_edit.text() or "0.0.0.0",
            gateway_port=gateway_port,
            embedding_url=self.embedding_url_edit.text().strip(),
            embedding_enabled=self.memory_enabled_check.isChecked(),
            channels=self._current_config.channels if self._current_config else ChannelsConfig(),
            skills=self._skills_widget.get_config(),
            providers=providers,
            multi_model=multi_model,
        )

        logger.info("步骤1: 保存配置到本地文件")

        if self._config_manager.save(config):
            logger.info(f"✓ 本地配置保存成功: {name}")
            self._current_config = config
            
            # 只更新配置列表的显示，不重新加载（避免覆盖配置）
            logger.info("步骤2: 更新配置列表显示")
            self._update_config_list_display()
            self.config_saved.emit(name)
            
            # 同步配置到 WSL 分发
            sync_success = False
            sync_message = ""
            if self._clawbot_controller:
                logger.info(f"步骤3: 同步配置到 WSL 分发: {config.distro_name}")
                sync_success = self._clawbot_controller.sync_config_to_wsl(config)
                if sync_success:
                    sync_message = "\n✓ 配置已同步到 WSL 分发"
                    logger.info(f"✓ WSL 配置同步成功: {config.distro_name}")
                else:
                    sync_message = "\n⚠ 配置同步到 WSL 分发失败"
                    logger.warning(f"✗ WSL 配置同步失败: {config.distro_name}")
            
            logger.info("========== 配置保存流程完成 ==========")
            
            # 检查是否有正在运行的 clawbot 实例
            need_restart = False
            if self._clawbot_controller:
                instance = self._clawbot_controller.get_instance(name)
                if instance and instance.status.value == "running":
                    need_restart = True
            
            if need_restart:
                reply = QMessageBox.question(
                    self, tr("config.msg.restart_prompt_title", "重启提示"),
                    tr("config.msg.restart_prompt", "配置 '{name}' 对应的 clawbot 正在运行，是否需要重启以应用新配置？{sync_message}").format(name=name, sync_message=sync_message),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    logger.info(f"正在重启 clawbot: {name}")
                    success = self._clawbot_controller.restart(name)
                    if success:
                        QMessageBox.information(self, tr("error.success", "成功"), tr("config.msg.saved_and_restarted", "已保存配置并重启 clawbot: {name}{sync_message}").format(name=name, sync_message=sync_message))
                    else:
                        QMessageBox.warning(self, tr("error.warning", "警告"), tr("config.msg.saved_but_restart_failed", "配置已保存，但重启 clawbot 失败{sync_message}").format(sync_message=sync_message))
                else:
                    QMessageBox.information(self, tr("error.success", "成功"), tr("config.msg.saved", "已保存配置: {name}{sync_message}").format(name=name, sync_message=sync_message))
            else:
                QMessageBox.information(self, tr("error.success", "成功"), tr("config.msg.saved", "已保存配置: {name}{sync_message}").format(name=name, sync_message=sync_message))
        else:
            logger.error(f"✗ 本地配置保存失败: {name}")
            QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.save_failed", "保存配置失败"))
    
    def _update_config_list_display(self):
        """仅更新配置列表的显示，不重新加载"""
        logger.info("更新配置列表显示")
        current_row = self.config_list.currentRow()
        current_text = self.config_list.currentItem().text() if self.config_list.currentItem() else ""
        
        self.config_list.clear()
        
        distros = self._wsl_manager.list_distros()
        default_name = self._config_manager.get_default_name()
        
        for distro in distros:
            item_text = distro.name
            if distro.name == default_name:
                item_text = f"{distro.name}{tr('config.msg.default_suffix', ' (默认)')}"
            self.config_list.addItem(item_text)
        
        # 恢复之前的选择
        if current_text:
            for i in range(self.config_list.count()):
                if self.config_list.item(i).text() == current_text:
                    self.config_list.setCurrentRow(i)
                    break
        elif current_row >= 0 and current_row < self.config_list.count():
            self.config_list.setCurrentRow(current_row)
    
    def _set_default_config(self):
        if not self._current_config:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.select_config_first", "请先选择一个配置"))
            return
        
        success = self._config_manager.set_default(self._current_config.name)
        if success:
            if self._current_config.distro_name:
                self._wsl_manager.set_default_distro(self._current_config.distro_name)
            self._load_configs()
            QMessageBox.information(self, tr("error.success", "成功"), tr("config.msg.set_default_success", "已设置 '{name}' 为默认配置，同时设置 WSL 分发 '{distro}' 为默认").format(name=self._current_config.name, distro=self._current_config.distro_name))
        else:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.set_default_failed", "设置默认配置失败"))
    
    def _copy_apiKey(self):
        apiKey = self.apiKey_edit.text()
        if apiKey:
            clipboard = QApplication.clipboard()
            clipboard.setText(apiKey)
            QMessageBox.information(self, tr("error.success", "成功"), tr("config.msg.api_key_copied", "API Key 已复制到剪贴板"))
        else:
            QMessageBox.warning(self, tr("error.hint", "提示"), tr("config.msg.no_api_key", "没有可复制的 API Key"))

    def _verify_config(self):
        if not self._current_config:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.select_or_create_config", "请先选择或创建一个配置"))
            return
        
        errors = []
        warnings = []
        successes = []
        
        if self._current_config.distro_name:
            successes.append(tr("config.verify.distro_ok", "✓ WSL 分发: {distro}").format(distro=self._current_config.distro_name))
        else:
            errors.append(tr("config.verify.no_distro", "✗ 未选择 WSL 分发"))
        
        if self._current_config.windows_workspace:
            successes.append(tr("config.verify.workspace_ok", "✓ Windows 工作空间: {workspace}").format(workspace=self._current_config.windows_workspace))
        else:
            errors.append(tr("config.verify.no_workspace", "✗ 未设置 Windows 工作空间"))
        
        if self._current_config.apiKey:
            successes.append(tr("config.verify.api_key_ok", "✓ API Key 已设置"))
        else:
            warnings.append(tr("config.verify.no_api_key", "⚠ 未设置 API Key"))
        
        message_parts = []
        if successes:
            message_parts.append(tr("config.msg.success_items", "【成功项】") + "\n" + "\n".join(successes))
        if warnings:
            message_parts.append("\n" + tr("config.msg.warning_items", "【警告项】") + "\n" + "\n".join(warnings))
        if errors:
            message_parts.append("\n" + tr("config.msg.error_items", "【错误项】") + "\n" + "\n".join(errors))
        
        full_message = "\n".join(message_parts)
        
        if errors:
            QMessageBox.warning(self, tr("config.msg.verify_failed_title", "配置验证失败"), full_message)
        elif warnings:
            QMessageBox.information(self, tr("config.msg.verify_passed_with_warnings_title", "配置验证通过（有警告）"), full_message)
        else:
            QMessageBox.information(self, tr("config.msg.verify_passed_title", "配置验证通过"), full_message)

    def _show_loading(self, message: str = None):
        """显示加载状态"""
        if message is None:
            message = tr("config.msg.loading", "加载中...")
        if self._loading_overlay is None:
            self._loading_overlay = QLabel(self)
            self._loading_overlay.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 0, 0, 150);
                    color: white;
                    font-size: 14px;
                    padding: 20px;
                    border-radius: 8px;
                }
            """)
            self._loading_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._loading_overlay.setText(message)
        self._loading_overlay.setGeometry(self.rect())
        self._loading_overlay.show()
        self._loading_overlay.raise_()
        self._is_loading = True

    def _hide_loading(self):
        """隐藏加载状态"""
        if self._loading_overlay:
            self._loading_overlay.hide()
        self._is_loading = False

    def _reset_form(self):
        """重置表单 - 异步从 WSL 读取配置"""
        if self._is_loading:
            return

        if not self._current_config:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.select_config_first", "请先选择一个配置"))
            return
        
        distro_name = self._current_config.distro_name
        logger.info(f"重置配置，从 WSL 分发 '{distro_name}' 读取")

        # 显示加载状态
        self._show_loading(tr("config.msg.reading_from_wsl", "正在从 WSL 读取配置..."))

        def reset_operation():
            distro = self._wsl_manager.get_distro(distro_name)
            distro_running = distro and distro.is_running
            
            if not distro_running:
                logger.info(f"WSL 分发 '{distro_name}' 未运行，尝试启动")
                start_success = self._wsl_manager.start_distro(distro_name)
                if not start_success:
                    return {"success": False, "error": f"WSL 分发 '{distro_name}' 无法启动"}
            
            if self._clawbot_controller:
                # 不在这里调用 _sync_providers_from_wsl，避免在后台线程修改 UI
                wsl_config = self._clawbot_controller.read_config_from_wsl(distro_name)
                
                if wsl_config and wsl_config != {}:
                    return {"success": True, "config": wsl_config, "distro_name": distro_name}
                else:
                    return {"success": False, "error": "WSL 中没有配置或配置为空"}
            
            return {"success": False, "error": "Clawbot 控制器未初始化"}
        
        def on_result(result):
            # 隐藏加载状态
            self._hide_loading()

            # 检查错误结果
            if isinstance(result, AsyncResult) and not result.success:
                logger.error(f"重置配置失败: {result.error}")
                QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.reset_failed", "重置配置失败: {error}").format(error=result.error))
                return

            if result.get("success"):
                # 在主线程中同步提供商
                self._sync_providers_from_wsl(result["distro_name"])
                self._populate_from_clawbot_config(result["config"])
                QMessageBox.information(self, tr("error.success", "成功"), tr("config.msg.reset_success", "已从 WSL 分发 '{name}' 重置配置").format(name=result['distro_name']))
            else:
                error_msg = result.get("error", "未知错误")
                if "无法启动" in error_msg:
                    QMessageBox.warning(self, tr("config.msg.wsl_not_running_title", "WSL 分发未运行"), error_msg)
                else:
                    QMessageBox.information(self, tr("error.hint", "提示"), error_msg)
        
        op = AsyncOperation(self)
        op.execute(reset_operation, on_result)

    def save_current_config(self):
        self._save_config()

    def _import_from_wsl(self):
        """从 WSL 导入配置"""
        if not self._clawbot_controller:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.controller_not_initialized", "clawbot 控制器未初始化"))
            return
        
        distro_name = self.distro_combo.currentText()
        if not distro_name:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.select_distro_first", "请先选择 WSL 分发"))
            return
        
        logger.info(f"从 WSL 导入配置: {distro_name}")
        
        wsl_config = self._clawbot_controller.read_config_from_wsl(distro_name)
        if not wsl_config:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.cannot_read_wsl_config", "无法从 WSL 分发 '{distro}' 读取配置").format(distro=distro_name))
            return
        
        logger.info("成功读取 WSL 配置")
        self._populate_from_clawbot_config(wsl_config)
        QMessageBox.information(self, tr("error.success", "成功"), tr("config.msg.imported_from_wsl", "已从 WSL 分发 '{distro}' 导入配置").format(distro=distro_name))
    
    def _sync_providers_from_wsl(self, distro_name: str):
        """从 WSL 配置同步提供商选项"""
        wsl_config = self._clawbot_controller.read_config_from_wsl(distro_name)
        if not wsl_config:
            return
        
        providers = wsl_config.get("providers", {})
        if not providers:
            return
        
        logger.info(f"从 WSL 找到的提供商: {list(providers.keys())}")
        
        # 获取当前提供商列表
        current_providers = [self.provider_combo.itemText(i) for i in range(self.provider_combo.count())]
        
        # 添加 WSL 中有的但当前列表没有的提供商
        for provider_name in providers.keys():
            if provider_name not in current_providers and provider_name != "":
                self.provider_combo.addItem(provider_name)
                logger.info(f"添加新提供商: {provider_name}")
    
    def _populate_from_clawbot_config(self, clawbot_config: dict):
        """从 clawbot 配置填充表单"""
        logger.info(f"_populate_from_clawbot_config: {clawbot_config}")
        
        agents = clawbot_config.get("agents", {}).get("defaults", {})
        if "model" in agents:
            # 如果模型不在下拉列表中，添加它
            model_text = agents["model"]
            if self.model_combo.findText(model_text) < 0:
                self.model_combo.addItem(model_text)
            self.model_combo.setCurrentText(model_text)
            logger.info(f"设置 model: {model_text}")
        if "workspace" in agents:
            pass
        
        providers = clawbot_config.get("providers", {})
        for provider_name, provider_cfg in providers.items():
            # 只要有 provider 就处理，不只是有 apiKey
            logger.info(f"处理 provider: {provider_name}, cfg: {provider_cfg}")
            
            index = self.provider_combo.findText(provider_name)
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)
            else:
                # 如果 provider 不在列表中，添加它
                self.provider_combo.addItem(provider_name)
                self.provider_combo.setCurrentText(provider_name)
            
            self.apiKey_edit.setText(provider_cfg.get("apiKey", ""))
            self.base_url_edit.setText(provider_cfg.get("apiBase", ""))
            
            # 如果 provider 中有 model，也设置它
            if "model" in provider_cfg:
                model_text = provider_cfg["model"]
                if self.model_combo.findText(model_text) < 0:
                    self.model_combo.addItem(model_text)
                self.model_combo.setCurrentText(model_text)
            
            self._on_provider_changed(self.provider_combo.currentText())
            break
        
        gateway = clawbot_config.get("gateway", {})
        if "host" in gateway:
            self.gateway_host_edit.setText(gateway["host"])
            logger.info(f"设置 gateway_host: {gateway['host']}")
        if "port" in gateway:
            self.gateway_port_edit.setText(str(gateway["port"]))
            logger.info(f"设置 gateway_port: {gateway['port']}")
            self._validate_gateway_port()
        
        tools = clawbot_config.get("tools", {})
        web_search = tools.get("web", {}).get("search", {})
        if web_search.get("apiKey"):
            self.web_search_check.setChecked(True)
            self.brave_key_edit.setText(web_search["apiKey"])
            logger.info("设置 web_search 和 brave_apiKey")
        elif tools.get("web"):
            self.web_search_check.setChecked(True)
            logger.info("设置 enable_web_search=True")
    
    def _on_oauth_login(self):
        """触发 OAuth 登录流程"""
        distro_name = self._current_config.distro_name if self._current_config else None
        provider = self.provider_combo.currentText()
        
        # OAuth 提供商到 clawbot 命令参数的映射
        provider_login_map = {
            "qwen_portal": "qwen-portal",
            "openai_codex": "openai-codex",
            "github_copilot": "github-copilot",
            "doubao_web": "doubao-web",
            "deepseek_web": "deepseek-web",
        }
        
        login_provider = provider_login_map.get(provider)
        if not login_provider:
            QMessageBox.warning(self, tr("error.title", "错误"), f"提供商 '{provider}' 不支持 OAuth 登录")
            return
        
        if not distro_name:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.select_distro_first", "请先选择 WSL 分发"))
            return
        
        distro = self._wsl_manager.get_distro(distro_name)
        if not distro or not distro.is_running:
            if not self._wsl_manager.start_distro(distro_name):
                QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.cannot_start_distro", "无法启动 WSL 分发: {distro}").format(distro=distro_name))
                return
        
        self.oauth_login_btn.setEnabled(False)
        self.oauth_status_label.setText(tr("config.status.logging_in", "正在登录..."))
        self.oauth_status_label.setStyleSheet("color: #58a6ff; font-size: 12px;")
        
        if not hasattr(self, '_oauth_callback_signal'):
            self._oauth_callback_signal = ThreadSafeSignal(self._on_oauth_login_finished)
        
        def run_login():
            result = self._wsl_manager.execute_command(
                distro_name,
                f"clawbot provider login {login_provider}",
                timeout=180
            )
            self._oauth_callback_signal.emit(result.success, result.stdout, result.stderr)
        
        thread = threading.Thread(target=run_login, daemon=True)
        thread.start()
    
    def _on_oauth_login_finished(self, success: bool, stdout: str, stderr: str):
        """OAuth 登录完成回调"""
        self.oauth_login_btn.setEnabled(True)
        
        is_success = success or "login successful" in stdout.lower() or "oauth login successful" in stdout.lower()
        provider = self.provider_combo.currentText()
        provider_display = provider.replace("_", " ").title()
        
        if is_success:
            self.oauth_status_label.setText(tr("config.status.logged_in", "已登录"))
            self.oauth_status_label.setStyleSheet("color: #3fb950; font-size: 12px;")
            QMessageBox.information(self, tr("error.success", "成功"), f"{provider_display} OAuth 登录成功！")
        else:
            self.oauth_status_label.setText(tr("config.status.login_failed", "登录失败"))
            self.oauth_status_label.setStyleSheet("color: #f85149; font-size: 12px;")
            error_msg = stderr if stderr else stdout
            QMessageBox.warning(self, tr("config.msg.login_failed_title", "登录失败"), tr("config.msg.oauth_failed", "OAuth 登录失败:\n{error}").format(error=error_msg))
    
    def _check_oauth_status(self):
        """异步检查 OAuth 认证状态"""
        provider = self.provider_combo.currentText()
        distro_name = self._current_config.distro_name if self._current_config else None
        
        # OAuth 提供商的认证文件路径映射
        oauth_cred_paths = {
            "qwen_portal": "~/.qwen/oauth_creds.json",
            "openai_codex": "~/.codex/oauth_creds.json",
            "github_copilot": "~/.copilot/oauth_creds.json",
            "doubao_web": "~/.doubao/oauth_creds.json",
            "deepseek_web": "~/.deepseek/oauth_creds.json",
        }
        
        cred_path = oauth_cred_paths.get(provider)
        if not distro_name or not cred_path:
            return
        
        def check_operation():
            result = self._wsl_manager.execute_command(
                distro_name,
                f"test -f {cred_path} && echo 'exists' || echo 'not_found'"
            )
            if not result.success:
                return AsyncResult(success=False, error=result.stderr or "命令执行失败")
            return "exists" in result.stdout
        
        def on_result(exists):
            # 检查错误结果
            if isinstance(exists, AsyncResult) and not exists.success:
                logger.error(f"检查 OAuth 状态失败: {exists.error}")
                return
            
            if exists:
                self.oauth_status_label.setText(tr("config.status.logged_in", "已登录"))
                self.oauth_status_label.setStyleSheet("color: #3fb950; font-size: 12px;")
            else:
                self.oauth_status_label.setText(tr("config.status.not_logged_in", "未登录"))
                self.oauth_status_label.setStyleSheet("color: #f85149; font-size: 12px;")
        
        op = AsyncOperation(self)
        op.execute(check_operation, on_result)
    
    def _delete_config(self):
        if not self._current_config:
            return

        name = self._current_config.name
        reply = QMessageBox.question(
            self, tr("config.msg.confirm_title", "确认"), tr("config.msg.confirm_delete", "确定要删除配置 '{name}' 吗？").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self._config_manager.delete(name):
                self._current_config = None
                self._load_configs()
                QMessageBox.information(self, tr("error.success", "成功"), tr("config.msg.deleted", "已删除配置: {name}").format(name=name))
    
    def on_wsl_status_changed(self, distros: List[Dict], running_count: int, stopped_count: int):
        pass
    
    def on_wsl_distro_started(self, distro_name: str):
        self._load_distros()
    
    def on_wsl_distro_stopped(self, distro_name: str):
        self._load_distros()
    
    def on_wsl_distro_removed(self, distro_name: str):
        self._load_configs()
        self._load_distros()
    
    def on_wsl_distro_imported(self, distro_name: str):
        self._load_configs()
        self._load_distros()
    
    def on_wsl_list_changed(self, distros: List[Dict], added: List[str], removed: List[str]):
        self._load_configs()
        self._load_distros()
    
    def _refresh_data(self):
        """刷新 WSL 分发列表和配置数据"""
        logger.info("用户手动刷新 WSL 分发列表")
        self._load_configs()
        self._load_distros()
