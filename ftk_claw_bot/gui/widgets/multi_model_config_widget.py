# -*- coding: utf-8 -*-
"""
多模型配置面板组件

支持配置多个 Provider 和模型，实现智能路由。
"""
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QComboBox, QLineEdit, QCheckBox,
    QDialog, QDialogButtonBox, QFormLayout, QSpinBox,
    QDoubleSpinBox, QGroupBox, QListWidget, QListWidgetItem,
    QSizePolicy, QApplication, QInputDialog, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ...models.clawbot_config import (
    ProviderConfigItem, ModelConfigItem, RoutingRuleItem, MultiModelConfigItem
)
from ...utils.i18n import tr


# 预定义任务类型
TASK_TYPES = [
    ("simple_chat", "简单对话"),
    ("code_generation", "代码生成"),
    ("code_review", "代码审查"),
    ("complex_reasoning", "复杂推理"),
    ("file_operation", "文件操作"),
    ("web_search", "网络搜索"),
    ("data_analysis", "数据分析"),
    ("creative_writing", "创意写作"),
    ("translation", "翻译"),
]

# 预定义 Provider 列表
PROVIDER_LIST = [
    "anthropic", "openai", "deepseek", "qwen_portal", "doubao_web",
    "gemini", "zhipu", "moonshot", "minimax", "openrouter", "groq",
    "dashscope", "aihubmix", "siliconflow", "volcengine", "ollama", "custom"
]

# 成本等级
COST_TIERS = [("low", "低"), ("medium", "中"), ("high", "高")]

# 策略选项
STRATEGY_OPTIONS = [
    ("auto", "自动"),
    ("manual", "手动"),
    ("round_robin", "轮询"),
    ("priority", "优先级"),
]

# 预定义能力列表
PREDEFINED_CAPABILITIES = [
    ("chat", "对话"),
    ("code", "代码生成"),
    ("reasoning", "推理"),
    ("vision", "视觉理解"),
    ("web_search", "网络搜索"),
    ("file_operation", "文件操作"),
    ("data_analysis", "数据分析"),
    ("translation", "翻译"),
    ("creative", "创意写作"),
]


class CapabilityTagsWidget(QWidget):
    """能力标签选择组件"""
    
    tags_changed = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags: List[str] = []
        self._init_ui()
    
    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(4)
        
        self.tags_layout = QHBoxLayout()
        self.tags_layout.setSpacing(4)
        self.tags_layout.addStretch()
        self.main_layout.addLayout(self.tags_layout)
        
        self.add_btn = QPushButton(tr("dialog.model_config.add_capability", "+ 添加能力"))
        self.add_btn.setObjectName("smallButton")
        self.add_menu = QMenu(self)
        
        for cap_id, cap_label in PREDEFINED_CAPABILITIES:
            action = self.add_menu.addAction(cap_label)
            action.triggered.connect(lambda _, c=cap_id: self._add_tag(c))
        
        self.add_menu.addSeparator()
        custom_action = self.add_menu.addAction(tr("dialog.model_config.custom_capability", "自定义输入..."))
        custom_action.triggered.connect(self._custom_input)
        
        self.add_btn.setMenu(self.add_menu)
        self.main_layout.addWidget(self.add_btn)
    
    def _add_tag(self, tag: str):
        if tag and tag not in self._tags:
            self._tags.append(tag)
            self._refresh_tags()
            self.tags_changed.emit(self._tags)
    
    def _remove_tag(self, tag: str):
        if tag in self._tags:
            self._tags.remove(tag)
            self._refresh_tags()
            self.tags_changed.emit(self._tags)
    
    def _custom_input(self):
        text, ok = QInputDialog.getText(
            self,
            tr("dialog.custom_capability.title", "自定义能力"),
            tr("dialog.custom_capability.prompt", "输入能力名称:")
        )
        if ok and text.strip():
            self._add_tag(text.strip())
    
    def _refresh_tags(self):
        while self.tags_layout.count() > 1:
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for tag in self._tags:
            tag_label = QLabel(f"{tag} ×")
            tag_label.setObjectName("capabilityTag")
            tag_label.setStyleSheet("""
                QLabel#capabilityTag {
                    background-color: #e3f2fd;
                    border: 1px solid #90caf9;
                    border-radius: 12px;
                    padding: 2px 8px;
                }
            """)
            tag_label.mousePressEvent = lambda e, t=tag: self._remove_tag(t)
            self.tags_layout.insertWidget(self.tags_layout.count() - 1, tag_label)
    
    def set_tags(self, tags: List[str]):
        self._tags = list(tags)
        self._refresh_tags()
    
    def get_tags(self) -> List[str]:
        return list(self._tags)


class ModelConfigItemWidget(QFrame):
    """单个模型配置项（可展开）"""
    
    delete_requested = pyqtSignal(str)  # model_name
    edit_requested = pyqtSignal(str)    # model_name
    toggled = pyqtSignal(str, bool)      # model_name, enabled
    
    def __init__(self, config: ModelConfigItem, provider_config: ProviderConfigItem = None, parent=None):
        super().__init__(parent)
        self._config = config
        self._provider_config = provider_config  # 用于显示 API Key 和 Base URL
        self._expanded = False
        self._init_ui()
    
    def _init_ui(self):
        self.setObjectName("modelConfigItem")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 8, 12, 8)
        self.main_layout.setSpacing(8)
        
        # 标题行（始终显示）
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(8)
        
        # 展开按钮
        self.expand_btn = QPushButton("▶")
        self.expand_btn.setFixedSize(24, 24)
        self.expand_btn.setObjectName("expandBtn")
        self.expand_btn.clicked.connect(self._toggle_expand)
        self.header_layout.addWidget(self.expand_btn)
        
        # 模型名称
        self.name_label = QLabel(self._config.name or "未命名模型")
        self.name_label.setObjectName("modelName")
        font = QFont()
        font.setBold(True)
        self.name_label.setFont(font)
        self.header_layout.addWidget(self.name_label, 1)
        
        # 状态标签
        self.status_label = QLabel("✓" if self._config.enabled else "✗")
        self.status_label.setObjectName("statusLabel")
        self.header_layout.addWidget(self.status_label)
        
        # 编辑按钮
        self.edit_btn = QPushButton(tr("btn.edit", "编辑"))
        self.edit_btn.setObjectName("smallButton")
        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._config.name))
        self.header_layout.addWidget(self.edit_btn)
        
        # 删除按钮
        self.delete_btn = QPushButton(tr("btn.delete", "删除"))
        self.delete_btn.setObjectName("smallButton")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        self.header_layout.addWidget(self.delete_btn)
        
        self.main_layout.addLayout(self.header_layout)
        
        # 简要信息行
        self.summary_layout = QHBoxLayout()
        self.summary_layout.setSpacing(16)
        
        self.provider_label = QLabel(f"Provider: {self._config.provider}")
        self.provider_label.setObjectName("summaryLabel")
        self.summary_layout.addWidget(self.provider_label)
        
        # 别名已移到详情区域显示
        self.alias_label = QLabel(f"别名: {self._config.alias or '-'}")
        self.alias_label.setObjectName("summaryLabel")
        self.alias_label.setVisible(False)  # 保留但隐藏，便于代码兼容
        self.summary_layout.addWidget(self.alias_label)
        
        # 启用状态（简要信息行显示）
        self.enabled_label = QLabel("✓ 启用" if self._config.enabled else "✗ 禁用")
        self.enabled_label.setObjectName("summaryLabel")
        self.enabled_label.setStyleSheet("color: #3fb950;" if self._config.enabled else "color: #f85149;")
        self.summary_layout.addWidget(self.enabled_label)
        
        self.cost_label = QLabel(f"成本: {self._config.cost_tier}")
        self.cost_label.setObjectName("summaryLabel")
        self.summary_layout.addWidget(self.cost_label)
        
        self.summary_layout.addStretch()
        self.main_layout.addLayout(self.summary_layout)
        
        # 详情区域（默认隐藏）
        self.details_widget = QWidget()
        self.details_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
            QLabel {
                color: #8b949e;
            }
        """)
        self.details_layout = QFormLayout(self.details_widget)
        self.details_layout.setContentsMargins(28, 12, 0, 8)
        self.details_layout.setSpacing(8)
        
        # 显示所有字段
        self._detail_labels = {}
        self._init_detail_rows()
        
        self.details_widget.setVisible(False)
        self.main_layout.addWidget(self.details_widget)
    
    def _init_detail_rows(self):
        """初始化详情行"""
        # 别名（从简要信息移到详情）
        self._detail_labels["alias"] = QLabel(self._config.alias or "-")
        self.details_layout.addRow(tr("dialog.model_config.alias", "别名:"), self._detail_labels["alias"])
        
        # 最大 Tokens
        self._detail_labels["max_tokens"] = QLabel(str(self._config.max_tokens))
        self.details_layout.addRow(tr("dialog.model_config.max_tokens", "最大 Tokens:"), self._detail_labels["max_tokens"])
        
        # 优先级
        self._detail_labels["priority"] = QLabel(str(self._config.priority))
        self.details_layout.addRow(tr("dialog.model_config.priority", "优先级:"), self._detail_labels["priority"])
        
        # 成本等级
        cost_tier_labels = {"low": tr("capability.low", "低"), "medium": tr("capability.medium", "中"), "high": tr("capability.high", "高")}
        self._detail_labels["cost_tier"] = QLabel(cost_tier_labels.get(self._config.cost_tier, self._config.cost_tier))
        self.details_layout.addRow(tr("dialog.model_config.cost_tier", "成本等级:"), self._detail_labels["cost_tier"])
        
        # 能力
        capabilities_text = ", ".join(self._config.capabilities) if self._config.capabilities else "-"
        self._detail_labels["capabilities"] = QLabel(capabilities_text)
        self._detail_labels["capabilities"].setWordWrap(True)
        self.details_layout.addRow(tr("dialog.model_config.capabilities", "能力:"), self._detail_labels["capabilities"])
        
        # Temperature
        temp_text = str(self._config.temperature) if self._config.temperature is not None else "-"
        self._detail_labels["temperature"] = QLabel(temp_text)
        self.details_layout.addRow("Temperature:", self._detail_labels["temperature"])
        
        # API Key（从 provider 配置获取）
        api_key_text = "******" if (self._provider_config and self._provider_config.api_key) else "-"
        self._detail_labels["api_key"] = QLabel(api_key_text)
        self.details_layout.addRow("API Key:", self._detail_labels["api_key"])
        
        # Base URL（从 provider 配置获取）
        base_url_text = self._provider_config.base_url if (self._provider_config and self._provider_config.base_url) else "-"
        self._detail_labels["base_url"] = QLabel(base_url_text)
        self._detail_labels["base_url"].setWordWrap(True)
        self.details_layout.addRow("Base URL:", self._detail_labels["base_url"])
    
    def _toggle_expand(self):
        self._expanded = not self._expanded
        self.expand_btn.setText("▼" if self._expanded else "▶")
        self.details_widget.setVisible(self._expanded)
    
    def get_config(self) -> ModelConfigItem:
        return self._config
    
    def set_config(self, config: ModelConfigItem):
        self._config = config
        # 更新标题行
        self.name_label.setText(config.name or "未命名模型")
        self.status_label.setText("✓" if config.enabled else "✗")
        # 更新简要信息行
        self.provider_label.setText(f"Provider: {config.provider}")
        self.alias_label.setVisible(False)  # 隐藏别名标签
        # 更新启用状态标签
        self.enabled_label.setText("✓ 启用" if config.enabled else "✗ 禁用")
        self.enabled_label.setStyleSheet("color: #3fb950;" if config.enabled else "color: #f85149;")
        self.cost_label.setText(f"成本: {config.cost_tier}")
        # 更新详情区域
        self._update_details()
    
    def _update_details(self):
        """更新详情区域的标签"""
        # 别名
        self._detail_labels["alias"].setText(self._config.alias or "-")
        # 最大 Tokens
        self._detail_labels["max_tokens"].setText(str(self._config.max_tokens))
        # 优先级
        self._detail_labels["priority"].setText(str(self._config.priority))
        # 成本等级
        cost_tier_labels = {"low": tr("capability.low", "低"), "medium": tr("capability.medium", "中"), "high": tr("capability.high", "高")}
        self._detail_labels["cost_tier"].setText(cost_tier_labels.get(self._config.cost_tier, self._config.cost_tier))
        # 能力
        capabilities_text = ", ".join(self._config.capabilities) if self._config.capabilities else "-"
        self._detail_labels["capabilities"].setText(capabilities_text)
        # Temperature
        temp_text = str(self._config.temperature) if self._config.temperature is not None else "-"
        self._detail_labels["temperature"].setText(temp_text)
        # API Key（从 provider 配置获取）
        api_key_text = "******" if (self._provider_config and self._provider_config.api_key) else "-"
        self._detail_labels["api_key"].setText(api_key_text)
        # Base URL（从 provider 配置获取）
        base_url_text = self._provider_config.base_url if (self._provider_config and self._provider_config.base_url) else "-"
        self._detail_labels["base_url"].setText(base_url_text)
    
    def set_provider_config(self, provider_config: ProviderConfigItem):
        """设置 provider 配置（用于更新 API Key 和 Base URL 显示）"""
        self._provider_config = provider_config
        self._update_details()
    
    def _on_delete_clicked(self):
        """删除按钮点击处理"""
        reply = QMessageBox.question(
            self,
            tr("dialog.delete.title", "确认删除"),
            tr("dialog.delete.message", "确定要删除模型 '{name}' 吗？").format(name=self._config.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(self._config.name)


# OAuth 提供商列表（与 clawbot registry.py 保持一致）
OAUTH_PROVIDERS = {"qwen_portal", "openai_codex", "github_copilot", "doubao_web", "deepseek_web"}

# OAuth 提供商到 clawbot 命令参数的映射
OAUTH_LOGIN_MAP = {
    "qwen_portal": "qwen-portal",
    "openai_codex": "openai-codex",
    "github_copilot": "github-copilot",
    "doubao_web": "doubao-web",
    "deepseek_web": "deepseek-web",
}

# OAuth 提供商的认证文件路径映射
OAUTH_CRED_PATHS = {
    "qwen_portal": "~/.qwen/oauth_creds.json",
    "openai_codex": "~/.codex/oauth_creds.json",
    "github_copilot": "~/.copilot/oauth_creds.json",
    "doubao_web": "~/.doubao/oauth_creds.json",
    "deepseek_web": "~/.deepseek/oauth_creds.json",
}

# 本地部署提供商
LOCAL_PROVIDERS = {"custom", "vllm", "ollama"}


class ModelConfigDialog(QDialog):
    """添加/编辑模型配置对话框"""
    
    def __init__(self, config: Optional[ModelConfigItem] = None, providers: List[str] = None, provider_configs: List[ProviderConfigItem] = None, existing_models: List[str] = None, wsl_manager=None, distro_name: str = None, parent=None):
        super().__init__(parent)
        self._config = config or ModelConfigItem(name="", provider="")
        self._providers = providers or PROVIDER_LIST
        self._provider_configs = provider_configs or []  # 用于查找 API Key 和 Base URL
        self._existing_models = existing_models or []  # 用于检查重复模型
        self._original_name = config.name if config else None  # 原始模型名称（编辑时）
        self._wsl_manager = wsl_manager  # 用于 OAuth 登录
        self._distro_name = distro_name  # 用于 OAuth 登录
        self._result: Optional[ModelConfigItem] = None
        
        self.setWindowTitle(tr("dialog.model_config.title", "模型配置") if config else tr("dialog.model_config.add", "添加模型"))
        self.setMinimumWidth(480)
        self.setMinimumHeight(280)  # 确保基本内容能完整显示
        
        # 设置深色背景样式
        self.setStyleSheet("""
            QDialog {
                background-color: #1c2128;
            }
            QGroupBox {
                background-color: #22272e;
                border: 1px solid #444c56;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
                color: #adbac7;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #adbac7;
            }
            QLabel {
                color: #adbac7;
            }
            QLineEdit {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #c9d1d9;
                selection-background-color: #388bfd;
            }
            QLineEdit:focus {
                border-color: #58a6ff;
            }
            QLineEdit::placeholder {
                color: #6e7681;
            }
            QComboBox {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #c9d1d9;
            }
            QComboBox:focus {
                border-color: #58a6ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #8b949e;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #21262d;
                border: 1px solid #30363d;
                color: #c9d1d9;
                selection-background-color: #388bfd;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
                color: #c9d1d9;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #58a6ff;
            }
            QCheckBox {
                color: #adbac7;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #30363d;
                background-color: #21262d;
            }
            QCheckBox::indicator:checked {
                background-color: #388bfd;
                border-color: #388bfd;
            }
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #c9d1d9;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #8b949e;
            }
            QPushButton:pressed {
                background-color: #161b22;
            }
            QPushButton#smallButton {
                padding: 4px 12px;
                font-size: 12px;
            }
            QPushButton#primaryButton {
                background-color: #238636;
                border-color: #238636;
                color: white;
            }
            QPushButton#primaryButton:hover {
                background-color: #2ea043;
            }
            QDialogButtonBox QPushButton {
                min-width: 80px;
            }
        """)
        
        self._init_ui()
        self._load_config()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)  # 增加边距
        layout.setSpacing(12)
        
        # 基本配置区域
        basic_group = QGroupBox(tr("dialog.model_config.basic_section", "基本配置"))
        basic_layout = QFormLayout(basic_group)
        basic_layout.setContentsMargins(12, 16, 12, 12)  # 增加内边距
        basic_layout.setSpacing(10)
        
        self.provider_combo = QComboBox()
        self.provider_combo.setEditable(True)
        self.provider_combo.addItems(self._providers)
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        basic_layout.addRow(tr("dialog.model_config.provider", "提供商:"), self.provider_combo)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(tr("placeholder.model_name", "模型名称，如 deepseek-chat"))
        basic_layout.addRow(tr("dialog.model_config.name", "模型:"), self.name_edit)
        
        # API Key 行（普通 provider）
        self.api_key_widget = QWidget()
        api_key_layout = QHBoxLayout(self.api_key_widget)
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText(tr("placeholder.api_key", "API Key (可选)"))
        api_key_layout.addWidget(self.api_key_edit)
        basic_layout.addRow("API Key:", self.api_key_widget)
        
        # OAuth 状态行（OAuth provider）
        self.oauth_widget = QWidget()
        oauth_layout = QHBoxLayout(self.oauth_widget)
        oauth_layout.setContentsMargins(0, 0, 0, 0)
        self.oauth_status_label = QLabel(tr("config.status.checking", "检查中..."))
        self.oauth_status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        oauth_layout.addWidget(self.oauth_status_label)
        self.oauth_login_btn = QPushButton(tr("config.label.login", "登录"))
        self.oauth_login_btn.setObjectName("smallButton")
        self.oauth_login_btn.clicked.connect(self._on_oauth_login)
        oauth_layout.addWidget(self.oauth_login_btn)
        oauth_layout.addStretch()
        basic_layout.addRow("", self.oauth_widget)
        self.oauth_widget.setVisible(False)
        
        # Base URL 行
        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText(tr("placeholder.base_url", "自定义 URL (可选)"))
        basic_layout.addRow("Base URL:", self.base_url_edit)
        
        layout.addWidget(basic_group)
        
        # 高级配置区域（可折叠）
        self.advanced_header = QPushButton(f"▶ {tr('dialog.model_config.advanced_section', '高级配置')}")
        self.advanced_header.setObjectName("collapsibleHeader")
        self.advanced_header.setStyleSheet("""
            QPushButton#collapsibleHeader {
                text-align: left;
                padding: 8px;
                background-color: #2d333b;
                border: 1px solid #444c56;
                border-radius: 4px;
                color: #adbac7;
            }
            QPushButton#collapsibleHeader:hover {
                background-color: #373e47;
            }
        """)
        self.advanced_header.clicked.connect(self._toggle_advanced)
        layout.addWidget(self.advanced_header)
        
        self.advanced_content = QWidget()
        self.advanced_content.setVisible(False)
        advanced_layout = QFormLayout(self.advanced_content)
        advanced_layout.setContentsMargins(12, 12, 12, 12)  # 增加内边距
        advanced_layout.setSpacing(10)
        
        self.alias_edit = QLineEdit()
        self.alias_edit.setPlaceholderText(tr("placeholder.alias", "别名，如 fast/balanced/powerful"))
        advanced_layout.addRow(tr("dialog.model_config.alias", "别名:"), self.alias_edit)
        
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 1000000)
        self.max_tokens_spin.setValue(4096)
        advanced_layout.addRow(tr("dialog.model_config.max_tokens", "最大 Tokens:"), self.max_tokens_spin)
        
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 100)
        self.priority_spin.setValue(1)
        advanced_layout.addRow(tr("dialog.model_config.priority", "优先级:"), self.priority_spin)
        
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setSpecialValueText(tr("dialog.model_config.default", "默认"))
        advanced_layout.addRow("Temperature:", self.temp_spin)
        
        self.cost_combo = QComboBox()
        for tier, label in COST_TIERS:
            self.cost_combo.addItem(label, tier)
        advanced_layout.addRow(tr("dialog.model_config.cost_tier", "成本等级:"), self.cost_combo)
        
        self.capabilities_widget = CapabilityTagsWidget()
        advanced_layout.addRow(tr("dialog.model_config.capabilities", "能力:"), self.capabilities_widget)
        
        self.enabled_check = QCheckBox(tr("dialog.model_config.enabled", "启用此模型"))
        self.enabled_check.setChecked(True)
        advanced_layout.addRow(self.enabled_check)
        
        layout.addWidget(self.advanced_content)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _toggle_advanced(self):
        """切换高级配置区域的显示状态"""
        visible = self.advanced_content.isVisible()
        self.advanced_content.setVisible(not visible)
        title = tr("dialog.model_config.advanced_section", "高级配置")
        self.advanced_header.setText(f"{'▼' if not visible else '▶'} {title}")
    
    def _on_provider_changed(self, provider: str):
        """当提供商变更时切换 UI"""
        is_oauth = provider in OAUTH_PROVIDERS
        is_local = provider in LOCAL_PROVIDERS
        
        # 切换 API Key 和 OAuth 控件的显示
        self.api_key_widget.setVisible(not is_oauth)
        self.oauth_widget.setVisible(is_oauth)
        
        # 处理 Base URL（仅在用户手动切换时设置默认值，不清空已有值）
        if is_local:
            self.base_url_edit.setEnabled(True)
            # 只在本地 provider 且值为空时设置默认值
            if not self.base_url_edit.text():
                if provider == "ollama":
                    self.base_url_edit.setText("http://localhost:11434/v1")
                elif provider == "vllm":
                    self.base_url_edit.setPlaceholderText("http://localhost:8000/v1")
        else:
            self.base_url_edit.setEnabled(False)
        
        # 如果是 OAuth provider，检查登录状态
        if is_oauth:
            self._check_oauth_status()
    
    def _check_oauth_status(self):
        """异步检查 OAuth 认证状态"""
        provider = self.provider_combo.currentText()
        
        cred_path = OAUTH_CRED_PATHS.get(provider)
        if not self._wsl_manager or not self._distro_name or not cred_path:
            self.oauth_status_label.setText(tr("config.status.not_logged_in", "未登录"))
            self.oauth_status_label.setStyleSheet("color: #f85149; font-size: 12px;")
            return
        
        self.oauth_status_label.setText(tr("config.status.checking", "检查中..."))
        self.oauth_status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        
        def check_operation():
            result = self._wsl_manager.execute_command(
                self._distro_name,
                f"test -f {cred_path} && echo 'exists' || echo 'not_found'"
            )
            return result.success and "exists" in result.stdout
        
        def on_result(exists):
            if exists:
                self.oauth_status_label.setText(tr("config.status.logged_in", "已登录"))
                self.oauth_status_label.setStyleSheet("color: #3fb950; font-size: 12px;")
            else:
                self.oauth_status_label.setText(tr("config.status.not_logged_in", "未登录"))
                self.oauth_status_label.setStyleSheet("color: #f85149; font-size: 12px;")
        
        # 使用定时器延迟执行，避免阻塞 UI
        from PyQt6.QtCore import QTimer
        import threading
        
        def run_check():
            result = check_operation()
            QTimer.singleShot(0, lambda: on_result(result))
        
        thread = threading.Thread(target=run_check, daemon=True)
        thread.start()
    
    def _on_oauth_login(self):
        """触发 OAuth 登录流程"""
        provider = self.provider_combo.currentText()
        
        login_provider = OAUTH_LOGIN_MAP.get(provider)
        if not login_provider:
            QMessageBox.warning(self, tr("error.title", "错误"), f"提供商 '{provider}' 不支持 OAuth 登录")
            return
        
        if not self._wsl_manager or not self._distro_name:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.select_distro_first", "请先选择 WSL 分发"))
            return
        
        distro = self._wsl_manager.get_distro(self._distro_name)
        if not distro or not distro.is_running:
            if not self._wsl_manager.start_distro(self._distro_name):
                QMessageBox.warning(self, tr("error.title", "错误"), tr("config.msg.cannot_start_distro", "无法启动 WSL 分发: {distro}").format(distro=self._distro_name))
                return
        
        self.oauth_login_btn.setEnabled(False)
        self.oauth_status_label.setText(tr("config.status.logging_in", "正在登录..."))
        self.oauth_status_label.setStyleSheet("color: #58a6ff; font-size: 12px;")
        
        from PyQt6.QtCore import QTimer
        import threading
        
        def run_login():
            result = self._wsl_manager.execute_command(
                self._distro_name,
                f"clawbot provider login {login_provider}",
                timeout=180
            )
            return result.success, result.stdout, result.stderr
        
        def on_login_finished(result):
            success, stdout, stderr = result
            self.oauth_login_btn.setEnabled(True)
            
            is_success = success or "login successful" in stdout.lower() or "oauth login successful" in stdout.lower()
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
        
        def run_and_callback():
            result = run_login()
            QTimer.singleShot(0, lambda: on_login_finished(result))
        
        thread = threading.Thread(target=run_and_callback, daemon=True)
        thread.start()
    
    def _load_config(self):
        if not self._config:
            return
        
        # 设置 provider
        index = self.provider_combo.findText(self._config.provider)
        if index >= 0:
            self.provider_combo.setCurrentIndex(index)
        else:
            self.provider_combo.setCurrentText(self._config.provider)
        
        # 触发 provider 变更以更新 UI 状态（OAuth 控件等）
        self._on_provider_changed(self.provider_combo.currentText())
        
        self.name_edit.setText(self._config.name)
        
        # 从 provider_configs 中查找 API Key 和 Base URL
        provider_config = next(
            (p for p in self._provider_configs if p.name == self._config.provider),
            None
        )
        if provider_config:
            self.api_key_edit.setText(provider_config.api_key)
            self.base_url_edit.setText(provider_config.base_url)
        
        self.alias_edit.setText(self._config.alias)
        self.max_tokens_spin.setValue(self._config.max_tokens)
        self.priority_spin.setValue(self._config.priority)
        self.enabled_check.setChecked(self._config.enabled)
        
        # 设置成本等级
        for i in range(self.cost_combo.count()):
            if self.cost_combo.itemData(i) == self._config.cost_tier:
                self.cost_combo.setCurrentIndex(i)
                break
        
        if self._config.temperature is not None:
            self.temp_spin.setValue(self._config.temperature)
        
        self.capabilities_widget.set_tags(self._config.capabilities)
    
    def _accept(self):
        # 验证必填字段
        name = self.name_edit.text().strip()
        provider = self.provider_combo.currentText().strip()
        
        if not name:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("error.model_name_required", "请输入模型名称"))
            return
        
        if not provider:
            QMessageBox.warning(self, tr("error.title", "错误"), tr("error.provider_required", "请选择或输入提供商"))
            return
        
        # 检查重复模型（使用 provider/name 作为唯一标识）
        model_key = f"{provider}/{name}"
        original_key = f"{self._config.provider}/{self._original_name}" if self._original_name else None
        
        for existing in self._existing_models:
            if existing == model_key and existing != original_key:
                QMessageBox.warning(
                    self, 
                    tr("error.title", "错误"), 
                    tr("error.model_exists", "模型 '{key}' 已存在").format(key=model_key)
                )
                return
        
        # 构建 config
        self._result = ModelConfigItem(
            name=name,
            provider=provider,
            alias=self.alias_edit.text().strip(),
            capabilities=self.capabilities_widget.get_tags(),
            cost_tier=self.cost_combo.currentData(),
            max_tokens=self.max_tokens_spin.value(),
            priority=self.priority_spin.value(),
            temperature=self.temp_spin.value() if self.temp_spin.value() > 0 else None,
            enabled=self.enabled_check.isChecked(),
        )
        self.accept()
    
    def get_result(self) -> Optional[ModelConfigItem]:
        return self._result
    
    def get_api_key(self) -> str:
        return self.api_key_edit.text().strip()
    
    def get_base_url(self) -> str:
        return self.base_url_edit.text().strip()


class MultiModelConfigWidget(QWidget):
    """多模型配置面板"""
    
    config_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._providers: List[ProviderConfigItem] = []
        self._multi_model_config = MultiModelConfigItem()
        self._model_widgets: Dict[str, ModelConfigItemWidget] = {}
        self._wsl_manager = None  # 用于 OAuth 登录
        self._distro_name: str = ""  # 用于 OAuth 登录
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 策略选择
        strategy_layout = QHBoxLayout()
        strategy_layout.setSpacing(8)
        
        strategy_layout.addWidget(QLabel(tr("multi_model.strategy", "策略:")))
        
        self.strategy_combo = QComboBox()
        for value, label in STRATEGY_OPTIONS:
            self.strategy_combo.addItem(label, value)
        self.strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)
        strategy_layout.addWidget(self.strategy_combo)
        
        strategy_layout.addStretch()
        layout.addLayout(strategy_layout)
        
        # 模型列表区域
        self.models_group = QGroupBox(tr("multi_model.models", "模型列表"))
        models_layout = QVBoxLayout(self.models_group)
        models_layout.setContentsMargins(8, 12, 8, 8)
        models_layout.setSpacing(8)
        
        # 模型容器（不使用 ScrollArea，直接布局实现自适应高度）
        self.models_container = QWidget()
        self.models_layout = QVBoxLayout(self.models_container)
        self.models_layout.setContentsMargins(0, 0, 0, 0)
        self.models_layout.setSpacing(8)
        
        models_layout.addWidget(self.models_container)
        
        # 空状态提示
        self.empty_label = QLabel(tr("multi_model.no_models", "暂无模型配置，点击下方按钮添加"))
        self.empty_label.setStyleSheet("color: #666; font-style: italic;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        models_layout.addWidget(self.empty_label)
        
        # 添加按钮
        self.add_model_btn = QPushButton(tr("btn.add_model", "+ 添加模型配置"))
        self.add_model_btn.clicked.connect(self._add_model)
        models_layout.addWidget(self.add_model_btn)
        
        layout.addWidget(self.models_group)
        
        # 初始状态
        self._update_empty_state()
    
    def set_enabled_state(self, enabled: bool):
        """设置启用状态（由外部调用）"""
        self._multi_model_config.enabled = enabled
        self.config_changed.emit()
    
    def _on_strategy_changed(self, index: int):
        self._multi_model_config.strategy = self.strategy_combo.currentData()
        self.config_changed.emit()
    
    def _update_empty_state(self):
        """更新空状态提示显示"""
        has_models = len(self._multi_model_config.models) > 0
        self.empty_label.setVisible(not has_models)
    
    def _get_available_providers(self) -> List[str]:
        """获取所有可用的 provider 名称（预定义 + 已配置）"""
        # 从预定义列表开始
        all_providers = list(PROVIDER_LIST)
        # 添加已配置但不在预定义列表中的 provider
        for p in self._providers:
            if p.name and p.name not in all_providers:
                all_providers.append(p.name)
        return all_providers
    
    def _get_existing_model_keys(self) -> List[str]:
        """获取已存在的模型标识列表（provider/name）"""
        return [f"{m.provider}/{m.name}" for m in self._multi_model_config.models]
    
    def _add_model(self):
        dialog = ModelConfigDialog(
            providers=self._get_available_providers(),
            provider_configs=self._providers,
            existing_models=self._get_existing_model_keys(),
            wsl_manager=self._wsl_manager,
            distro_name=self._distro_name,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_result()
            if config:
                # 获取 API Key 和 Base URL
                api_key = dialog.get_api_key()
                base_url = dialog.get_base_url()
                
                # 更新或创建 ProviderConfigItem
                provider_name = config.provider
                existing_provider = next(
                    (p for p in self._providers if p.name == provider_name),
                    None
                )
                if existing_provider:
                    # 更新现有的 provider 配置（允许清空值）
                    existing_provider.api_key = api_key
                    existing_provider.base_url = base_url
                else:
                    # 创建新的 provider 配置
                    self._providers.append(ProviderConfigItem(
                        name=provider_name,
                        api_key=api_key,
                        base_url=base_url,
                        enabled=True,
                    ))
                
                self._multi_model_config.models.append(config)
                self._add_model_widget(config)
                self._update_empty_state()
                self.config_changed.emit()
    
    def _add_model_widget(self, config: ModelConfigItem):
        # 查找对应的 provider 配置
        provider_config = next(
            (p for p in self._providers if p.name == config.provider),
            None
        )
        widget = ModelConfigItemWidget(config, provider_config)
        widget.edit_requested.connect(self._edit_model)
        widget.delete_requested.connect(self._delete_model)
        
        # 添加到布局
        self.models_layout.addWidget(widget)
        self._model_widgets[config.name] = widget
    
    def _edit_model(self, name: str):
        # 查找配置
        config = next((m for m in self._multi_model_config.models if m.name == name), None)
        if not config:
            return
        
        dialog = ModelConfigDialog(
            config=config,
            providers=self._get_available_providers(),
            provider_configs=self._providers,
            existing_models=self._get_existing_model_keys(),
            wsl_manager=self._wsl_manager,
            distro_name=self._distro_name,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_config = dialog.get_result()
            if new_config:
                # 获取 API Key 和 Base URL
                api_key = dialog.get_api_key()
                base_url = dialog.get_base_url()
                
                # 更新或创建 ProviderConfigItem
                provider_name = new_config.provider
                existing_provider = next(
                    (p for p in self._providers if p.name == provider_name),
                    None
                )
                if existing_provider:
                    # 更新现有的 provider 配置（允许清空值）
                    existing_provider.api_key = api_key
                    existing_provider.base_url = base_url
                else:
                    # 创建新的 provider 配置
                    self._providers.append(ProviderConfigItem(
                        name=provider_name,
                        api_key=api_key,
                        base_url=base_url,
                        enabled=True,
                    ))
                
                # 更新配置
                idx = next((i for i, m in enumerate(self._multi_model_config.models) if m.name == name), -1)
                if idx >= 0:
                    self._multi_model_config.models[idx] = new_config
                    
                    # 更新 widget
                    if name in self._model_widgets:
                        widget = self._model_widgets[name]
                        widget.set_config(new_config)
                        # 更新 provider 配置显示
                        widget.set_provider_config(existing_provider or next(
                            (p for p in self._providers if p.name == provider_name),
                            None
                        ))
                        if new_config.name != name:
                            # 名称变了，更新 key
                            self._model_widgets[new_config.name] = self._model_widgets.pop(name)
                    
                    self.config_changed.emit()
    
    def _delete_model(self, name: str):
        # 从配置中移除
        self._multi_model_config.models = [m for m in self._multi_model_config.models if m.name != name]
        
        # 移除 widget
        if name in self._model_widgets:
            widget = self._model_widgets.pop(name)
            self.models_layout.removeWidget(widget)
            widget.deleteLater()
        
        self._update_empty_state()
        self.config_changed.emit()
    
    def set_config(self, providers: List[ProviderConfigItem], multi_model: MultiModelConfigItem, wsl_manager=None, distro_name: str = ""):
        """设置配置"""
        self._providers = providers
        self._multi_model_config = multi_model
        self._wsl_manager = wsl_manager
        self._distro_name = distro_name
        
        # 设置策略
        for i in range(self.strategy_combo.count()):
            if self.strategy_combo.itemData(i) == multi_model.strategy:
                self.strategy_combo.setCurrentIndex(i)
                break
        
        # 清空现有 widgets
        for widget in self._model_widgets.values():
            self.models_layout.removeWidget(widget)
            widget.deleteLater()
        self._model_widgets.clear()
        
        # 添加模型 widgets
        for model in multi_model.models:
            self._add_model_widget(model)
        
        self._update_empty_state()
    
    def get_config(self) -> tuple[List[ProviderConfigItem], MultiModelConfigItem]:
        """获取配置"""
        return self._providers, self._multi_model_config
