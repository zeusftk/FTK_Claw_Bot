# -*- coding: utf-8 -*-
from typing import Optional, List, Callable
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QSpinBox, QGroupBox, QScrollArea,
    QWidget, QFrame, QMessageBox, QListWidget, QListWidgetItem,
    QComboBox, QFormLayout, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ...models import (
    WhatsAppConfig, TelegramConfig, DiscordConfig, FeishuConfig,
    DingTalkConfig, SlackConfig, SlackDMConfig, EmailConfig,
    QQConfig, MochatConfig, CHANNEL_INFO
)


DIALOG_STYLE = """
QDialog {
    background-color: #0d1117;
}
QLabel {
    color: #c9d1d9;
    font-size: 13px;
}
QLineEdit {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
    color: #c9d1d9;
    font-size: 13px;
}
QLineEdit:focus {
    border: 1px solid #58a6ff;
}
QLineEdit::placeholder {
    color: #6e7681;
}
QCheckBox {
    color: #c9d1d9;
    font-size: 13px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #30363d;
    background-color: #161b22;
}
QCheckBox::indicator:checked {
    background-color: #238636;
    border-color: #238636;
}
QCheckBox::indicator:hover {
    border-color: #58a6ff;
}
QSpinBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    color: #c9d1d9;
    font-size: 13px;
}
QSpinBox:focus {
    border: 1px solid #58a6ff;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #21262d;
    border: none;
    width: 20px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #30363d;
}
QComboBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
    color: #c9d1d9;
    font-size: 13px;
}
QComboBox:focus {
    border: 1px solid #58a6ff;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #8b949e;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    selection-background-color: #21262d;
    color: #c9d1d9;
}
QGroupBox {
    color: #c9d1d9;
    font-weight: 600;
    font-size: 13px;
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    top: -8px;
    padding: 0 8px;
    background-color: #0d1117;
}
QPushButton {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 16px;
    color: #c9d1d9;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #30363d;
    border-color: #484f58;
}
QPushButton:pressed {
    background-color: #161b22;
}
QPushButton#primaryButton {
    background-color: #238636;
    border-color: rgba(46, 160, 67, 0.4);
    color: #ffffff;
}
QPushButton#primaryButton:hover {
    background-color: #2ea043;
    border-color: rgba(46, 160, 67, 0.8);
}
QPushButton#primaryButton:pressed {
    background-color: #196c2e;
}
QPushButton#smallButton {
    padding: 4px 10px;
    font-size: 12px;
}
QListWidget {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px;
    color: #c9d1d9;
    font-size: 13px;
}
QListWidget::item {
    padding: 6px 8px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background-color: #21262d;
}
QListWidget::item:hover {
    background-color: #21262d;
}
QScrollBar:vertical {
    background-color: #161b22;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #30363d;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #484f58;
}
"""


class AllowFromListWidget(QFrame):
    def __init__(self, allow_from: List[str] = None, parent=None):
        super().__init__(parent)
        self._allow_from = allow_from or []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        label = QLabel("允许的用户/ID:")
        label.setStyleSheet("font-weight: 500;")
        header.addWidget(label)
        header.addStretch()

        add_btn = QPushButton("+ 添加")
        add_btn.setObjectName("smallButton")
        add_btn.clicked.connect(self._add_item)
        header.addWidget(add_btn)
        layout.addLayout(header)

        self.list_widget = QListWidget()
        self.list_widget.setMaximumHeight(120)
        for item in self._allow_from:
            self._add_list_item(item)
        layout.addWidget(self.list_widget)

    def _add_item(self):
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "添加用户", "输入用户ID或用户名:")
        if ok and text.strip():
            self._add_list_item(text.strip())

    def _add_list_item(self, text: str):
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.list_widget.addItem(item)

        delete_btn = QPushButton("×")
        delete_btn.setObjectName("smallButton")
        delete_btn.setFixedSize(24, 24)
        delete_btn.clicked.connect(lambda: self.list_widget.takeItem(self.list_widget.row(item)))

    def get_values(self) -> List[str]:
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]


class BaseChannelDialog(QDialog):
    def __init__(self, channel_name: str, channel_info: dict, parent=None):
        super().__init__(parent)
        self._channel_name = channel_name
        self._channel_info = channel_info
        self._init_base_ui()

    def _init_base_ui(self):
        self.setWindowTitle(f"{self._channel_info.get('name', self._channel_name)} 配置")
        self.setMinimumWidth(520)
        self.setMinimumHeight(420)
        self.setStyleSheet(DIALOG_STYLE)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(16)
        self.main_layout.setContentsMargins(24, 24, 24, 24)

        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(12)

        icon_label = QLabel(self._channel_info.get("icon", "📡"))
        icon_label.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_label)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        
        title = QLabel(self._channel_info.get("name", self._channel_name))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f0f6fc;")
        title_layout.addWidget(title)

        desc = QLabel(self._channel_info.get("description", ""))
        desc.setStyleSheet("color: #8b949e; font-size: 12px;")
        title_layout.addWidget(desc)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        self.main_layout.addWidget(header_frame)

    def add_form_row(self, label: str, widget, tooltip: str = None):
        row_frame = QFrame()
        row_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(0, 4, 0, 4)
        row_layout.setSpacing(16)

        label_widget = QLabel(label)
        label_widget.setFixedWidth(120)
        label_widget.setStyleSheet("color: #8b949e; font-weight: 500;")
        row_layout.addWidget(label_widget)

        row_layout.addWidget(widget, 1)
        self.main_layout.addWidget(row_frame)

        if tooltip:
            widget.setToolTip(tooltip)

    def add_enabled_checkbox(self, enabled: bool = False) -> QCheckBox:
        enabled_frame = QFrame()
        enabled_frame.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        enabled_layout = QHBoxLayout(enabled_frame)
        enabled_layout.setContentsMargins(16, 12, 16, 12)
        
        self.enabled_check = QCheckBox("启用此渠道")
        self.enabled_check.setChecked(enabled)
        enabled_layout.addWidget(self.enabled_check)
        enabled_layout.addStretch()
        
        self.main_layout.addWidget(enabled_frame)
        return self.enabled_check

    def add_buttons(self):
        btn_frame = QFrame()
        btn_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border-top: 1px solid #30363d;
                padding-top: 16px;
            }
        """)
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 16, 0, 0)
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setObjectName("primaryButton")
        save_btn.setMinimumWidth(80)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        self.main_layout.addWidget(btn_frame)

    def get_config(self):
        raise NotImplementedError


class TelegramDialog(BaseChannelDialog):
    def __init__(self, config: TelegramConfig = None, parent=None):
        self._config = config or TelegramConfig()
        super().__init__("telegram", CHANNEL_INFO["telegram"], parent)
        self._setup_fields()
        self.add_buttons()

    def _setup_fields(self):
        self.add_enabled_checkbox(self._config.enabled)

        self.token_edit = QLineEdit()
        self.token_edit.setText(self._config.token)
        self.token_edit.setPlaceholderText("从 @BotFather 获取")
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.add_form_row("Bot Token:", self.token_edit, "Telegram Bot Token")

        self.proxy_edit = QLineEdit()
        self.proxy_edit.setText(self._config.proxy or "")
        self.proxy_edit.setPlaceholderText("http://127.0.0.1:7890")
        self.add_form_row("Proxy:", self.proxy_edit, "可选代理地址")

        self.allow_from_widget = AllowFromListWidget(self._config.allow_from)
        self.main_layout.addWidget(self.allow_from_widget)

    def get_config(self) -> TelegramConfig:
        return TelegramConfig(
            enabled=self.enabled_check.isChecked(),
            token=self.token_edit.text(),
            proxy=self.proxy_edit.text() or None,
            allow_from=self.allow_from_widget.get_values(),
        )


class DiscordDialog(BaseChannelDialog):
    def __init__(self, config: DiscordConfig = None, parent=None):
        self._config = config or DiscordConfig()
        super().__init__("discord", CHANNEL_INFO["discord"], parent)
        self._setup_fields()
        self.add_buttons()

    def _setup_fields(self):
        self.add_enabled_checkbox(self._config.enabled)

        self.token_edit = QLineEdit()
        self.token_edit.setText(self._config.token)
        self.token_edit.setPlaceholderText("Discord Bot Token")
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.add_form_row("Bot Token:", self.token_edit)

        self.allow_from_widget = AllowFromListWidget(self._config.allow_from)
        self.main_layout.addWidget(self.allow_from_widget)

    def get_config(self) -> DiscordConfig:
        return DiscordConfig(
            enabled=self.enabled_check.isChecked(),
            token=self.token_edit.text(),
            allow_from=self.allow_from_widget.get_values(),
        )


class FeishuDialog(BaseChannelDialog):
    def __init__(self, config: FeishuConfig = None, parent=None):
        self._config = config or FeishuConfig()
        super().__init__("feishu", CHANNEL_INFO["feishu"], parent)
        self._setup_fields()
        self.add_buttons()

    def _setup_fields(self):
        self.add_enabled_checkbox(self._config.enabled)

        self.app_id_edit = QLineEdit()
        self.app_id_edit.setText(self._config.app_id)
        self.app_id_edit.setPlaceholderText("App ID")
        self.add_form_row("App ID:", self.app_id_edit)

        self.app_secret_edit = QLineEdit()
        self.app_secret_edit.setText(self._config.app_secret)
        self.app_secret_edit.setPlaceholderText("App Secret")
        self.app_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.add_form_row("App Secret:", self.app_secret_edit)

        self.allow_from_widget = AllowFromListWidget(self._config.allow_from)
        self.main_layout.addWidget(self.allow_from_widget)

    def get_config(self) -> FeishuConfig:
        return FeishuConfig(
            enabled=self.enabled_check.isChecked(),
            app_id=self.app_id_edit.text(),
            app_secret=self.app_secret_edit.text(),
            allow_from=self.allow_from_widget.get_values(),
        )


class DingTalkDialog(BaseChannelDialog):
    def __init__(self, config: DingTalkConfig = None, parent=None):
        self._config = config or DingTalkConfig()
        super().__init__("dingtalk", CHANNEL_INFO["dingtalk"], parent)
        self._setup_fields()
        self.add_buttons()

    def _setup_fields(self):
        self.add_enabled_checkbox(self._config.enabled)

        self.client_id_edit = QLineEdit()
        self.client_id_edit.setText(self._config.client_id)
        self.client_id_edit.setPlaceholderText("AppKey")
        self.add_form_row("Client ID:", self.client_id_edit)

        self.client_secret_edit = QLineEdit()
        self.client_secret_edit.setText(self._config.client_secret)
        self.client_secret_edit.setPlaceholderText("AppSecret")
        self.client_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.add_form_row("Client Secret:", self.client_secret_edit)

        self.allow_from_widget = AllowFromListWidget(self._config.allow_from)
        self.main_layout.addWidget(self.allow_from_widget)

    def get_config(self) -> DingTalkConfig:
        return DingTalkConfig(
            enabled=self.enabled_check.isChecked(),
            client_id=self.client_id_edit.text(),
            client_secret=self.client_secret_edit.text(),
            allow_from=self.allow_from_widget.get_values(),
        )


class SlackDialog(BaseChannelDialog):
    def __init__(self, config: SlackConfig = None, parent=None):
        self._config = config or SlackConfig()
        super().__init__("slack", CHANNEL_INFO["slack"], parent)
        self._setup_fields()
        self.add_buttons()

    def _setup_fields(self):
        self.add_enabled_checkbox(self._config.enabled)

        self.bot_token_edit = QLineEdit()
        self.bot_token_edit.setText(self._config.bot_token)
        self.bot_token_edit.setPlaceholderText("xoxb-...")
        self.bot_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.add_form_row("Bot Token:", self.bot_token_edit)

        self.app_token_edit = QLineEdit()
        self.app_token_edit.setText(self._config.app_token)
        self.app_token_edit.setPlaceholderText("xapp-...")
        self.app_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.add_form_row("App Token:", self.app_token_edit)

        self.group_policy_combo = QComboBox()
        self.group_policy_combo.addItems(["mention", "open", "allowlist"])
        self.group_policy_combo.setCurrentText(self._config.group_policy)
        self.add_form_row("群组策略:", self.group_policy_combo)

    def get_config(self) -> SlackConfig:
        return SlackConfig(
            enabled=self.enabled_check.isChecked(),
            bot_token=self.bot_token_edit.text(),
            app_token=self.app_token_edit.text(),
            group_policy=self.group_policy_combo.currentText(),
        )


class EmailDialog(BaseChannelDialog):
    def __init__(self, config: EmailConfig = None, parent=None):
        self._config = config or EmailConfig()
        super().__init__("email", CHANNEL_INFO["email"], parent)
        self._setup_fields()
        self.add_buttons()

    def _setup_fields(self):
        self.add_enabled_checkbox(self._config.enabled)

        imap_group = QGroupBox("IMAP (接收)")
        imap_layout = QFormLayout(imap_group)

        self.imap_host_edit = QLineEdit()
        self.imap_host_edit.setText(self._config.imap_host)
        self.imap_host_edit.setPlaceholderText("imap.example.com")
        imap_layout.addRow("主机:", self.imap_host_edit)

        self.imap_port_spin = QSpinBox()
        self.imap_port_spin.setRange(1, 65535)
        self.imap_port_spin.setValue(self._config.imap_port)
        imap_layout.addRow("端口:", self.imap_port_spin)

        self.imap_username_edit = QLineEdit()
        self.imap_username_edit.setText(self._config.imap_username)
        imap_layout.addRow("用户名:", self.imap_username_edit)

        self.imap_password_edit = QLineEdit()
        self.imap_password_edit.setText(self._config.imap_password)
        self.imap_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        imap_layout.addRow("密码:", self.imap_password_edit)

        self.main_layout.addWidget(imap_group)

        smtp_group = QGroupBox("SMTP (发送)")
        smtp_layout = QFormLayout(smtp_group)

        self.smtp_host_edit = QLineEdit()
        self.smtp_host_edit.setText(self._config.smtp_host)
        self.smtp_host_edit.setPlaceholderText("smtp.example.com")
        smtp_layout.addRow("主机:", self.smtp_host_edit)

        self.smtp_port_spin = QSpinBox()
        self.smtp_port_spin.setRange(1, 65535)
        self.smtp_port_spin.setValue(self._config.smtp_port)
        smtp_layout.addRow("端口:", self.smtp_port_spin)

        self.smtp_username_edit = QLineEdit()
        self.smtp_username_edit.setText(self._config.smtp_username)
        smtp_layout.addRow("用户名:", self.smtp_username_edit)

        self.smtp_password_edit = QLineEdit()
        self.smtp_password_edit.setText(self._config.smtp_password)
        self.smtp_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        smtp_layout.addRow("密码:", self.smtp_password_edit)

        self.from_address_edit = QLineEdit()
        self.from_address_edit.setText(self._config.from_address)
        smtp_layout.addRow("发件人:", self.from_address_edit)

        self.main_layout.addWidget(smtp_group)

    def get_config(self) -> EmailConfig:
        return EmailConfig(
            enabled=self.enabled_check.isChecked(),
            imap_host=self.imap_host_edit.text(),
            imap_port=self.imap_port_spin.value(),
            imap_username=self.imap_username_edit.text(),
            imap_password=self.imap_password_edit.text(),
            smtp_host=self.smtp_host_edit.text(),
            smtp_port=self.smtp_port_spin.value(),
            smtp_username=self.smtp_username_edit.text(),
            smtp_password=self.smtp_password_edit.text(),
            from_address=self.from_address_edit.text(),
        )


class QQDialog(BaseChannelDialog):
    def __init__(self, config: QQConfig = None, parent=None):
        self._config = config or QQConfig()
        super().__init__("qq", CHANNEL_INFO["qq"], parent)
        self._setup_fields()
        self.add_buttons()

    def _setup_fields(self):
        self.add_enabled_checkbox(self._config.enabled)

        self.app_id_edit = QLineEdit()
        self.app_id_edit.setText(self._config.app_id)
        self.app_id_edit.setPlaceholderText("机器人 ID (AppID)")
        self.add_form_row("App ID:", self.app_id_edit)

        self.secret_edit = QLineEdit()
        self.secret_edit.setText(self._config.secret)
        self.secret_edit.setPlaceholderText("机器人密钥 (AppSecret)")
        self.secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.add_form_row("Secret:", self.secret_edit)

        self.allow_from_widget = AllowFromListWidget(self._config.allow_from)
        self.main_layout.addWidget(self.allow_from_widget)

    def get_config(self) -> QQConfig:
        return QQConfig(
            enabled=self.enabled_check.isChecked(),
            app_id=self.app_id_edit.text(),
            secret=self.secret_edit.text(),
            allow_from=self.allow_from_widget.get_values(),
        )


class WhatsAppDialog(BaseChannelDialog):
    def __init__(self, config: WhatsAppConfig = None, parent=None):
        self._config = config or WhatsAppConfig()
        super().__init__("whatsapp", CHANNEL_INFO["whatsapp"], parent)
        self._setup_fields()
        self.add_buttons()

    def _setup_fields(self):
        self.add_enabled_checkbox(self._config.enabled)

        self.bridge_url_edit = QLineEdit()
        self.bridge_url_edit.setText(self._config.bridge_url)
        self.bridge_url_edit.setPlaceholderText("ws://localhost:3001")
        self.add_form_row("Bridge URL:", self.bridge_url_edit)

        self.bridge_token_edit = QLineEdit()
        self.bridge_token_edit.setText(self._config.bridge_token)
        self.bridge_token_edit.setPlaceholderText("可选的桥接认证令牌")
        self.add_form_row("Bridge Token:", self.bridge_token_edit)

        self.allow_from_widget = AllowFromListWidget(self._config.allow_from)
        self.main_layout.addWidget(self.allow_from_widget)

    def get_config(self) -> WhatsAppConfig:
        return WhatsAppConfig(
            enabled=self.enabled_check.isChecked(),
            bridge_url=self.bridge_url_edit.text(),
            bridge_token=self.bridge_token_edit.text(),
            allow_from=self.allow_from_widget.get_values(),
        )


DIALOG_MAP = {
    "telegram": TelegramDialog,
    "discord": DiscordDialog,
    "feishu": FeishuDialog,
    "dingtalk": DingTalkDialog,
    "slack": SlackDialog,
    "email": EmailDialog,
    "qq": QQDialog,
    "whatsapp": WhatsAppDialog,
}


def get_channel_dialog(channel_name: str, config=None, parent=None) -> Optional[BaseChannelDialog]:
    dialog_class = DIALOG_MAP.get(channel_name)
    if dialog_class:
        return dialog_class(config, parent)
    return None
