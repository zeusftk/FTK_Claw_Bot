import os
import re
import threading
import subprocess
import traceback
from typing import Optional, Dict, Any
from pathlib import Path

from loguru import logger

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QSpinBox, QWidget, QStackedWidget,
    QFileDialog, QFrame, QScrollArea, QMessageBox, QProgressBar,QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ...models import (
    NanobotConfig, ChannelsConfig, SkillsConfig,
    WhatsAppConfig, TelegramConfig, DiscordConfig, FeishuConfig,
    DingTalkConfig, SlackConfig, SlackDMConfig, EmailConfig,
    QQConfig, MochatConfig, CHANNEL_INFO
)
from .message_dialog import show_warning, show_info, show_critical


WIZARD_STYLE = """
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
QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    selection-background-color: #21262d;
    color: #c9d1d9;
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
QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
}
QPushButton#primary {
    background-color: #238636;
    border-color: rgba(46, 160, 67, 0.4);
    color: #ffffff;
}
QPushButton#primary:hover {
    background-color: #2ea043;
    border-color: rgba(46, 160, 67, 0.8);
}
QPushButton#primary:pressed {
    background-color: #196c2e;
}
QPushButton#smallButton {
    padding: 4px 8px;
    font-size: 12px;
}
QProgressBar {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 4px;
    text-align: center;
    color: #c9d1d9;
}
QProgressBar::chunk {
    background-color: #238636;
    border-radius: 3px;
}
"""


class BasicInfoPage(QWidget):
    """Step 1: 基本信息"""
    
    def __init__(self, wsl_manager, parent=None):
        super().__init__(parent)
        self._wsl_manager = wsl_manager
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title_label = QLabel("设置分发基本信息")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #c9d1d9;")
        layout.addWidget(title_label)
        
        name_layout = QHBoxLayout()
        name_layout.setSpacing(12)
        name_label = QLabel("分发名称:")
        name_label.setFixedWidth(100)
        name_layout.addWidget(name_label)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: my-nanobot")
        name_layout.addWidget(self.name_edit, 1)
        
        self.name_hint_label = QLabel("")
        self.name_hint_label.setStyleSheet("font-size: 12px;")
        self.name_hint_label.setFixedWidth(120)
        name_layout.addWidget(self.name_hint_label)
        
        layout.addLayout(name_layout)
        
        location_layout = QHBoxLayout()
        location_layout.setSpacing(12)
        location_label = QLabel("安装位置:")
        location_label.setFixedWidth(100)
        location_layout.addWidget(location_label)
        
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("选择存放 WSL 分发的目录（可选）")
        location_layout.addWidget(self.location_edit, 1)
        
        browse_btn = QPushButton("浏览")
        browse_btn.setObjectName("smallButton")
        browse_btn.clicked.connect(self._browse_location)
        location_layout.addWidget(browse_btn)
        
        layout.addLayout(location_layout)
        
        hint_label = QLabel(
            "提示:\n"
            "• 分发名称只能包含字母、数字、下划线和横杠\n"
            "• 安装位置可选，留空则使用默认位置"
        )
        hint_label.setStyleSheet("color: #8b949e; font-size: 12px; line-height: 1.6;")
        layout.addWidget(hint_label)
        
        layout.addStretch()
        
        self.name_edit.textChanged.connect(self._validate_name)
    
    def _browse_location(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择 WSL 安装目录")
        if dir_path:
            self.location_edit.setText(dir_path)
    
    def _validate_name(self):
        name = self.name_edit.text().strip()
        
        if not name:
            self.name_hint_label.setText("")
            self.name_hint_label.setStyleSheet("color: #8b949e; font-size: 12px;")
            return
        
        if not re.match(r'^[a-zA-Z0-9_.-]+$', name):
            self.name_hint_label.setText("⚠ 格式无效")
            self.name_hint_label.setStyleSheet("color: #f85149; font-size: 12px;")
            return
        
        existing_distros = self._wsl_manager.list_distros()
        if any(d.name == name for d in existing_distros):
            self.name_hint_label.setText("⚠ 名称已存在")
            self.name_hint_label.setStyleSheet("color: #f85149; font-size: 12px;")
        else:
            self.name_hint_label.setText("✓ 名称可用")
            self.name_hint_label.setStyleSheet("color: #3fb950; font-size: 12px;")
    
    def validate(self) -> bool:
        name = self.name_edit.text().strip()
        
        if not name:
            show_warning(self, "错误", "请输入分发名称")
            return False
        
        if not re.match(r'^[a-zA-Z0-9_.-]+$', name):
            show_warning(self, "错误", "分发名称只能包含字母、数字、下划线和横杠")
            return False
        
        existing_distros = self._wsl_manager.list_distros()
        if any(d.name == name for d in existing_distros):
            show_warning(self, "错误", f"分发名称 '{name}' 已存在")
            return False
        
        return True
    
    def get_data(self) -> Dict[str, str]:
        return {
            "distro_name": self.name_edit.text().strip(),
            "install_location": self.location_edit.text().strip() or None
        }


class InitProgressPage(QWidget):
    """Step 2: 初始化 WSL（后台执行）"""
    
    init_completed = pyqtSignal(bool, str)
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int)
    step_status_changed = pyqtSignal(int, str)
    
    def __init__(self, wsl_manager, parent=None):
        super().__init__(parent)
        self._wsl_manager = wsl_manager
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title_label = QLabel("正在初始化 WSL 分发")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #c9d1d9;")
        layout.addWidget(title_label)
        
        self.status_label = QLabel("准备中...")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 13px;")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)
        
        steps_frame = QFrame()
        steps_frame.setStyleSheet("QFrame { background-color: #161b22; border-radius: 6px; }")
        steps_layout = QVBoxLayout(steps_frame)
        steps_layout.setSpacing(8)
        steps_layout.setContentsMargins(16, 16, 16, 16)
        
        self.step_labels = []
        steps = [
            "导入 Ubuntu 镜像",
            "配置 nanobot 环境"
        ]
        for i, step in enumerate(steps):
            step_label = QLabel(f"{'○' if i > 0 else '●'} {step}")
            step_label.setStyleSheet("color: #8b949e; font-size: 12px;")
            steps_layout.addWidget(step_label)
            self.step_labels.append(step_label)
        
        layout.addWidget(steps_frame)
        layout.addStretch()
        
        self.status_changed.connect(self._update_status, Qt.ConnectionType.QueuedConnection)
        self.progress_changed.connect(self._update_progress, Qt.ConnectionType.QueuedConnection)
        self.step_status_changed.connect(self._update_step_status, Qt.ConnectionType.QueuedConnection)
    
    def _update_status(self, status: str):
        self.status_label.setText(status)
    
    def _update_progress(self, value: int):
        self.progress_bar.setValue(value)
    
    def _update_step_status(self, step_index: int, status: str):
        if step_index < len(self.step_labels):
            step_text = self.step_labels[step_index].text()
            step_name = step_text.split(" ", 1)[1] if " " in step_text else step_text
            if status == "running":
                self.step_labels[step_index].setText(f"● {step_name}")
                self.step_labels[step_index].setStyleSheet("color: #58a6ff; font-size: 12px;")
            elif status == "done":
                self.step_labels[step_index].setText(f"✓ {step_name}")
                self.step_labels[step_index].setStyleSheet("color: #3fb950; font-size: 12px;")
            elif status == "error":
                self.step_labels[step_index].setText(f"✗ {step_name}")
                self.step_labels[step_index].setStyleSheet("color: #f85149; font-size: 12px;")
            elif status == "pending":
                self.step_labels[step_index].setText(f"○ {step_name}")
                self.step_labels[step_index].setStyleSheet("color: #8b949e; font-size: 12px;")
    
    def _set_step_status(self, step_index: int, status: str):
        self.step_status_changed.emit(step_index, status)
    
    def start_init(self, distro_name: str, install_location: Optional[str]):
        self._distro_name = distro_name
        self._install_location = install_location
        
        self.progress_bar.setValue(0)
        self._set_step_status(0, "running")
        self._set_step_status(1, "pending")
        
        thread = threading.Thread(
            target=self._run_init,
            daemon=True
        )
        thread.start()
    
    def _get_init_wsl_path(self) -> str:
        ## 获取 init_wsl 目录在项目根目录下
        script_dir = Path(__file__).parent.parent.parent.parent
        return str(script_dir / "init_wsl")
    
    def _run_init(self):
        try:
            init_wsl_path = self._get_init_wsl_path()
            tar_path = os.path.join(init_wsl_path, "Ubuntu_22.tar")
            bat_path = os.path.join(init_wsl_path, "make_nanobot_distro.bat")
            
            if not os.path.exists(tar_path):
                self.init_completed.emit(False, f"Ubuntu 镜像文件不存在: {tar_path}")
                return
            
            self.status_changed.emit("正在导入 Ubuntu 镜像...")
            self.progress_changed.emit(10)
            
            result = self._wsl_manager.import_distro(
                tar_path, 
                self._distro_name, 
                self._install_location
            )
            
            if not result.success:
                self._set_step_status(0, "error")
                self.init_completed.emit(False, f"导入失败: {result.stderr}")
                return
            
            self._set_step_status(0, "done")
            self.progress_changed.emit(50)
            
            self.status_changed.emit("正在配置 nanobot 环境...")
            self._set_step_status(1, "running")
            
            process = subprocess.Popen(
                [bat_path, self._distro_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=init_wsl_path
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self._set_step_status(1, "error")
                error_msg = stderr if stderr else "配置脚本执行失败"
                self.init_completed.emit(False, error_msg)
                return
            
            self._set_step_status(1, "done")
            self.progress_changed.emit(100)
            self.status_changed.emit("初始化完成")
            
            self.init_completed.emit(True, "初始化成功")
            
        except Exception as e:
            self.init_completed.emit(False, str(e))


class WorkspacePage(QWidget):
    """Step 3: 工作空间设置"""
    
    def __init__(self, wsl_manager, config_manager, parent=None):
        super().__init__(parent)
        self._wsl_manager = wsl_manager
        self._config_manager = config_manager
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title_label = QLabel("设置工作空间")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #c9d1d9;")
        layout.addWidget(title_label)
        
        ws_layout = QHBoxLayout()
        ws_layout.setSpacing(12)
        ws_label = QLabel("Windows 路径:")
        ws_label.setFixedWidth(100)
        ws_layout.addWidget(ws_label)
        
        self.windows_ws_edit = QLineEdit()
        self.windows_ws_edit.setPlaceholderText("D:\\clawbot_workspace")
        self.windows_ws_edit.textChanged.connect(self._update_wsl_path)
        ws_layout.addWidget(self.windows_ws_edit, 1)
        
        browse_btn = QPushButton("浏览")
        browse_btn.setObjectName("smallButton")
        browse_btn.clicked.connect(self._browse_workspace)
        ws_layout.addWidget(browse_btn)
        
        layout.addLayout(ws_layout)
        
        wsl_layout = QHBoxLayout()
        wsl_layout.setSpacing(12)
        wsl_label = QLabel("WSL 路径:")
        wsl_label.setFixedWidth(100)
        wsl_layout.addWidget(wsl_label)
        
        self.wsl_ws_label = QLabel("--")
        self.wsl_ws_label.setStyleSheet("color: #8b949e; font-size: 13px;")
        wsl_layout.addWidget(self.wsl_ws_label, 1)
        
        layout.addLayout(wsl_layout)
        
        self.sync_mnt_check = QCheckBox("同步到 /mnt 目录")
        self.sync_mnt_check.setChecked(True)
        layout.addWidget(self.sync_mnt_check)
        
        gateway_label = QLabel("Gateway 设置")
        gateway_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #c9d1d9; margin-top: 16px;")
        layout.addWidget(gateway_label)
        
        port_layout = QHBoxLayout()
        port_layout.setSpacing(12)
        port_label = QLabel("端口:")
        port_label.setFixedWidth(100)
        port_layout.addWidget(port_label)
        
        self.gateway_port_spin = QSpinBox()
        self.gateway_port_spin.setRange(1024, 65535)
        self.gateway_port_spin.setValue(18888)
        port_layout.addWidget(self.gateway_port_spin, 1)
        
        self.port_hint_label = QLabel("")
        self.port_hint_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        self.port_hint_label.setFixedWidth(150)
        port_layout.addWidget(self.port_hint_label)
        
        layout.addLayout(port_layout)
        
        self.gateway_port_spin.valueChanged.connect(self._validate_gateway_port)
        
        hint_label = QLabel(
            "提示:\n"
            "• 工作空间用于存储 nanobot 的数据和配置\n"
            "• Gateway 端口用于 API 访问"
        )
        hint_label.setStyleSheet("color: #8b949e; font-size: 12px; line-height: 1.6;")
        layout.addWidget(hint_label)
        
        layout.addStretch()
    
    def _browse_workspace(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择工作空间目录")
        if dir_path:
            self.windows_ws_edit.setText(dir_path)
    
    def _update_wsl_path(self):
        windows_path = self.windows_ws_edit.text().strip()
        if windows_path:
            wsl_path = self._wsl_manager.convert_windows_to_wsl_path(windows_path)
            self.wsl_ws_label.setText(wsl_path)
        else:
            self.wsl_ws_label.setText("--")
    
    def _validate_gateway_port(self):
        port = self.gateway_port_spin.value()
        
        existing_ports = {}
        for config in self._config_manager.get_all().values():
            if config.gateway_port:
                existing_ports[config.gateway_port] = config.distro_name
        
        if port in existing_ports:
            self.port_hint_label.setText(f"⚠ 已被 '{existing_ports[port]}' 使用")
            self.port_hint_label.setStyleSheet("color: #f85149; font-size: 12px;")
        else:
            self.port_hint_label.setText("✓ 端口可用")
            self.port_hint_label.setStyleSheet("color: #3fb950; font-size: 12px;")
    
    def get_data(self) -> Dict[str, Any]:
        return {
            "windows_workspace": self.windows_ws_edit.text().strip(),
            "workspace": self.wsl_ws_label.text() if self.wsl_ws_label.text() != "--" else "",
            "sync_to_mnt": self.sync_mnt_check.isChecked(),
            "gateway_port": self.gateway_port_spin.value()
        }


class LLMConfigPage(QWidget):
    """Step 4: LLM 配置"""
    
    def __init__(self, wsl_manager, distro_name_getter, parent=None):
        super().__init__(parent)
        self._wsl_manager = wsl_manager
        self._distro_name_getter = distro_name_getter
        self._oauth_callback = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title_label = QLabel("配置 LLM")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #c9d1d9;")
        layout.addWidget(title_label)
        
        provider_layout = QHBoxLayout()
        provider_layout.setSpacing(12)
        provider_label = QLabel("提供商:")
        provider_label.setFixedWidth(100)
        provider_layout.addWidget(provider_label)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems([
            "qwen_portal", "custom", "anthropic", "openai", "openrouter",
            "deepseek", "groq", "zhipu", "dashscope",
            "vllm", "gemini", "moonshot", "minimax", "aihubmix"
        ])
        self.provider_combo.currentTextChanged.connect(self._update_models)
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.provider_combo, 1)
        
        layout.addLayout(provider_layout)
        
        model_layout = QHBoxLayout()
        model_layout.setSpacing(12)
        model_label = QLabel("模型:")
        model_label.setFixedWidth(100)
        model_layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        model_layout.addWidget(self.model_combo, 1)
        
        layout.addLayout(model_layout)
        
        key_layout = QHBoxLayout()
        key_layout.setSpacing(12)
        key_label = QLabel("API Key:")
        key_label.setFixedWidth(100)
        key_layout.addWidget(key_label)
        
        self.apiKey_edit = QLineEdit()
        self.apiKey_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.apiKey_edit.setPlaceholderText("输入 API Key")
        key_layout.addWidget(self.apiKey_edit, 1)
        
        show_key_btn = QPushButton("👁")
        show_key_btn.setObjectName("smallButton")
        show_key_btn.setCheckable(True)
        show_key_btn.setToolTip("显示/隐藏 API Key")
        show_key_btn.toggled.connect(lambda checked: self.apiKey_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        ))
        key_layout.addWidget(show_key_btn)
        
        layout.addLayout(key_layout)
        
        url_layout = QHBoxLayout()
        url_layout.setSpacing(12)
        url_label = QLabel("自定义 URL:")
        url_label.setFixedWidth(100)
        url_layout.addWidget(url_label)
        
        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("https://api.example.com/v1")
        self.base_url_edit.setEnabled(False)
        url_layout.addWidget(self.base_url_edit, 1)
        
        layout.addLayout(url_layout)
        
        oauth_row = QHBoxLayout()
        oauth_row.setSpacing(8)
        self.oauth_status_label = QLabel("未登录")
        self.oauth_status_label.setStyleSheet("color: #f85149; font-size: 12px;")
        oauth_row.addWidget(self.oauth_status_label)
        
        self.oauth_login_btn = QPushButton("OAuth 登录")
        self.oauth_login_btn.setObjectName("smallButton")
        self.oauth_login_btn.setToolTip("使用 OAuth 登录 Qwen Portal")
        self.oauth_login_btn.clicked.connect(self._on_oauth_login)
        oauth_row.addWidget(self.oauth_login_btn)
        oauth_row.addStretch()
        
        oauth_container = QWidget()
        oauth_container.setLayout(oauth_row)
        oauth_container.setVisible(False)
        self._oauth_container = oauth_container
        layout.addWidget(oauth_container)
        
        hint_label = QLabel(
            "提示:\n"
            "• qwen_portal 支持 OAuth 登录\n"
            "• custom 提供商需要填写自定义 URL"
        )
        hint_label.setStyleSheet("color: #8b949e; font-size: 12px; line-height: 1.6;")
        layout.addWidget(hint_label)
        
        layout.addStretch()
        
        self._update_models()
    
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
            "vllm": [],
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
        }
        self.model_combo.clear()
        self.model_combo.addItems(models.get(provider, []))
    
    def _on_provider_changed(self, provider: str):
        oauth_providers = {"qwen_portal", "openai_codex"}
        is_oauth = provider in oauth_providers
        
        self.apiKey_edit.setVisible(not is_oauth)
        self._oauth_container.setVisible(is_oauth)
        
        if provider == "custom":
            self.base_url_edit.setEnabled(True)
        else:
            self.base_url_edit.setEnabled(False)
            self.base_url_edit.setText("")
        
        if is_oauth:
            self._check_oauth_status()
    
    def _check_oauth_status(self):
        """检查 OAuth 认证状态"""
        from ...utils.async_ops import AsyncOperation, AsyncResult
        
        provider = self.provider_combo.currentText()
        distro_name = self._distro_name_getter()
        
        if not distro_name or provider != "qwen_portal":
            return
        
        def check_operation():
            result = self._wsl_manager.execute_command(
                distro_name,
                "test -f ~/.qwen/oauth_creds.json && echo 'exists' || echo 'not_found'"
            )
            if not result.success:
                return AsyncResult(success=False, error=result.stderr or "命令执行失败")
            return "exists" in result.stdout
        
        def on_result(exists):
            if isinstance(exists, AsyncResult) and not exists.success:
                return
            
            if exists:
                self.oauth_status_label.setText("已登录")
                self.oauth_status_label.setStyleSheet("color: #3fb950; font-size: 12px;")
            else:
                self.oauth_status_label.setText("未登录")
                self.oauth_status_label.setStyleSheet("color: #f85149; font-size: 12px;")
        
        op = AsyncOperation(self)
        op.execute(check_operation, on_result)
    
    def _on_oauth_login(self):
        """触发 OAuth 登录流程"""
        import threading
        from ...utils.thread_safe import ThreadSafeSignal
        
        distro_name = self._distro_name_getter()
        
        if not distro_name:
            show_warning(self, "错误", "分发名称未设置")
            return
        
        distro = self._wsl_manager.get_distro(distro_name)
        if not distro or not distro.is_running:
            if not self._wsl_manager.start_distro(distro_name):
                show_warning(self, "错误", f"无法启动 WSL 分发: {distro_name}")
                return
        
        self.oauth_login_btn.setEnabled(False)
        self.oauth_status_label.setText("正在登录...")
        self.oauth_status_label.setStyleSheet("color: #58a6ff; font-size: 12px;")
        
        if not hasattr(self, '_oauth_signal'):
            self._oauth_signal = ThreadSafeSignal(self._on_oauth_login_finished)
        
        def run_login():
            result = self._wsl_manager.execute_command(
                distro_name,
                "nanobot provider login qwen-portal",
                timeout=180
            )
            self._oauth_signal.emit(result.success, result.stdout, result.stderr)
        
        thread = threading.Thread(target=run_login, daemon=True)
        thread.start()
    
    def _on_oauth_login_finished(self, success: bool, stdout: str, stderr: str):
        """OAuth 登录完成回调"""
        self.oauth_login_btn.setEnabled(True)
        
        if success:
            self.oauth_status_label.setText("已登录")
            self.oauth_status_label.setStyleSheet("color: #3fb950; font-size: 12px;")
        else:
            self.oauth_status_label.setText("登录失败")
            self.oauth_status_label.setStyleSheet("color: #f85149; font-size: 12px;")
    
    def needs_oauth(self) -> bool:
        """检查是否需要 OAuth 认证"""
        provider = self.provider_combo.currentText()
        if provider != "qwen_portal":
            return False
        return self.oauth_status_label.text() != "已登录"
    
    def start_oauth_if_needed(self, callback):
        """如果需要则启动 OAuth 登录"""
        self._oauth_callback = callback
        self._do_oauth_login()
    
    def _do_oauth_login(self):
        """执行 OAuth 登录（用于下一步时自动触发）"""
        import threading
        from ...utils.thread_safe import ThreadSafeSignal
        
        distro_name = self._distro_name_getter()
        if not distro_name:
            if self._oauth_callback:
                self._oauth_callback(False)
            return
        
        distro = self._wsl_manager.get_distro(distro_name)
        if not distro or not distro.is_running:
            if not self._wsl_manager.start_distro(distro_name):
                if self._oauth_callback:
                    self._oauth_callback(False)
                return
        
        self.oauth_login_btn.setEnabled(False)
        self.oauth_status_label.setText("正在登录...")
        self.oauth_status_label.setStyleSheet("color: #58a6ff; font-size: 12px;")
        
        if not hasattr(self, '_oauth_signal'):
            self._oauth_signal = ThreadSafeSignal(self._on_auto_oauth_finished)
        
        def run_login():
            result = self._wsl_manager.execute_command(
                distro_name,
                "nanobot provider login qwen-portal",
                timeout=180
            )
            self._oauth_signal.emit(result.success, result.stdout, result.stderr)
        
        thread = threading.Thread(target=run_login, daemon=True)
        thread.start()
    
    def _on_auto_oauth_finished(self, success: bool, stdout: str, stderr: str):
        """自动 OAuth 登录完成回调"""
        self.oauth_login_btn.setEnabled(True)
        
        if success:
            self.oauth_status_label.setText("已登录")
            self.oauth_status_label.setStyleSheet("color: #3fb950; font-size: 12px;")
        else:
            self.oauth_status_label.setText("登录失败")
            self.oauth_status_label.setStyleSheet("color: #f85149; font-size: 12px;")
        
        if self._oauth_callback:
            self._oauth_callback(success)
    
    def get_data(self) -> Dict[str, str]:
        return {
            "provider": self.provider_combo.currentText(),
            "model": self.model_combo.currentText(),
            "apiKey": self.apiKey_edit.text(),
            "base_url": self.base_url_edit.text()
        }


class ChannelsPage(QWidget):
    """Step 5: Channels 配置"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._channel_configs: Dict[str, Any] = {}
        self._channel_items: Dict[str, dict] = {}
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title_label = QLabel("配置 Channels")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #c9d1d9;")
        layout.addWidget(title_label)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        for channel_name, channel_info in CHANNEL_INFO.items():
            item_widget = QFrame()
            item_widget.setStyleSheet("QFrame { background-color: #161b22; border-radius: 6px; }")
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(12, 8, 12, 8)
            item_layout.setSpacing(12)
            
            icon_label = QLabel(channel_info.get("icon", "📡"))
            icon_label.setStyleSheet("font-size: 16px;")
            icon_label.setFixedWidth(24)
            item_layout.addWidget(icon_label)
            
            info_layout = QVBoxLayout()
            info_layout.setSpacing(2)
            
            name_label = QLabel(channel_info.get("name", channel_name))
            name_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #c9d1d9;")
            info_layout.addWidget(name_label)
            
            desc_label = QLabel(channel_info.get("description", ""))
            desc_label.setStyleSheet("color: #8b949e; font-size: 10px;")
            info_layout.addWidget(desc_label)
            
            item_layout.addLayout(info_layout, 1)
            
            enable_check = QCheckBox("启用")
            enable_check.setObjectName("channelEnableCheck")
            item_layout.addWidget(enable_check)
            
            config_btn = QPushButton("配置")
            config_btn.setObjectName("smallButton")
            config_btn.setFixedWidth(60)
            config_btn.clicked.connect(
                lambda checked, cn=channel_name: self._on_channel_config(cn)
            )
            item_layout.addWidget(config_btn)
            
            self._channel_items[channel_name] = {
                "enable_check": enable_check,
                "config_btn": config_btn,
            }
            
            self._init_channel_config(channel_name)
            
            content_layout.addWidget(item_widget)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        hint_label = QLabel("提示: 可以稍后在配置面板中详细配置各 Channel")
        hint_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(hint_label)
    
    def _init_channel_config(self, channel_name: str):
        config_classes = {
            "whatsapp": WhatsAppConfig,
            "telegram": TelegramConfig,
            "discord": DiscordConfig,
            "feishu": FeishuConfig,
            "dingtalk": DingTalkConfig,
            "slack": SlackConfig,
            "email": EmailConfig,
            "qq": QQConfig,
            "mochat": MochatConfig,
        }
        config_class = config_classes.get(channel_name)
        if config_class:
            self._channel_configs[channel_name] = config_class()
    
    def _on_channel_config(self, channel_name: str):
        """打开 Channel 配置对话框"""
        from ..widgets.channel_config_dialog import get_channel_dialog
        
        channel_config = self._channel_configs.get(channel_name)
        if not channel_config:
            return
        
        dialog = get_channel_dialog(channel_name, channel_config, self)
        if dialog and dialog.exec() == QDialog.DialogCode.Accepted:
            new_config = dialog.get_config()
            self._channel_configs[channel_name] = new_config
            self._channel_items[channel_name]["enable_check"].setChecked(new_config.enabled)
    
    def get_data(self) -> Dict[str, Any]:
        try:
            channels = ChannelsConfig()
            for channel_name, item in self._channel_items.items():
                enable_check = item["enable_check"]
                if channel_name in self._channel_configs:
                    config = self._channel_configs[channel_name]
                    config.enabled = enable_check.isChecked()
                    setattr(channels, channel_name, config)
            logger.info(f"ChannelsPage.get_data 成功: {channels.to_dict()}")
            return {"channels": channels}
        except Exception as e:
            logger.error(f"ChannelsPage.get_data 异常: {e}\n{traceback.format_exc()}")
            raise


class ApplyConfigPage(QWidget):
    """Step 6: 应用配置"""
    
    apply_completed = pyqtSignal(bool, str)
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int, int)
    
    def __init__(self, wsl_manager, config_manager, nanobot_controller, parent=None):
        super().__init__(parent)
        self._wsl_manager = wsl_manager
        self._config_manager = config_manager
        self._nanobot_controller = nanobot_controller
        self._config_data: Dict[str, Any] = {}
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title_label = QLabel("正在应用配置")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #c9d1d9;")
        layout.addWidget(title_label)
        
        self.status_label = QLabel("准备中...")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 13px;")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        
        self.status_changed.connect(self._update_status, Qt.ConnectionType.QueuedConnection)
        self.progress_changed.connect(self._update_progress, Qt.ConnectionType.QueuedConnection)
    
    def _update_status(self, status: str):
        self.status_label.setText(status)
    
    def _update_progress(self, min_val: int, max_val: int):
        self.progress_bar.setRange(min_val, max_val)
        if max_val > 0:
            self.progress_bar.setValue(max_val)
    
    def start_apply(self, config_data: Dict[str, Any]):
        self._config_data = config_data
        
        thread = threading.Thread(
            target=self._run_apply,
            daemon=True
        )
        thread.start()
    
    def _run_apply(self):
        try:
            distro_name = self._config_data.get("distro_name", "")
            logger.info(f"ApplyConfigPage._run_apply 开始, distro_name={distro_name}")
            
            self.status_changed.emit("创建配置对象...")
            
            channels = self._config_data.get("channels", ChannelsConfig())
            logger.info(f"channels 类型: {type(channels)}")
            
            config = NanobotConfig(
                name=distro_name,
                distro_name=distro_name,
                windows_workspace=self._config_data.get("windows_workspace", ""),
                workspace=self._config_data.get("workspace", ""),
                sync_to_mnt=self._config_data.get("sync_to_mnt", True),
                gateway_port=self._config_data.get("gateway_port", 18888),
                provider=self._config_data.get("provider", "qwen_portal"),
                model=self._config_data.get("model", ""),
                apiKey=self._config_data.get("apiKey", ""),
                base_url=self._config_data.get("base_url", ""),
                channels=channels,
                skills=SkillsConfig()
            )
            logger.info(f"NanobotConfig 创建成功: {config.name}")
            
            self.status_changed.emit("保存本地配置...")
            self._config_manager.save(config)
            logger.info("本地配置保存成功")
            
            self.status_changed.emit("写入 WSL 配置...")
            if self._nanobot_controller:
                try:
                    sync_success = self._nanobot_controller.sync_config_to_wsl(config)
                    if sync_success:
                        logger.info("WSL 配置同步成功")
                    else:
                        logger.warning("WSL 配置同步失败")
                except Exception as e:
                    logger.warning(f"WSL 配置同步失败: {e}")
            
            self.progress_changed.emit(0, 100)
            self.status_changed.emit("配置应用完成")
            
            logger.info("ApplyConfigPage._run_apply 完成")
            self.apply_completed.emit(True, "配置应用成功")
            
        except Exception as e:
            logger.error(f"ApplyConfigPage._run_apply 异常: {e}\n{traceback.format_exc()}")
            self.apply_completed.emit(False, str(e))


class SuccessPage(QWidget):
    """Step 7: 完成"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel("✓")
        icon_label.setStyleSheet("font-size: 64px; color: #3fb950;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        title_label = QLabel("创建成功！")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #c9d1d9;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #8b949e; font-size: 13px;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)
        
        self.confirm_btn = QPushButton("确认关闭")
        self.confirm_btn.setFixedWidth(120)
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #da3633;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f85149;
            }
            QPushButton:pressed {
                background-color: #b62324;
            }
        """)
        self.confirm_btn.clicked.connect(self._on_confirm)
        self.confirm_btn.setVisible(False)
        layout.addWidget(self.confirm_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def _on_confirm(self):
        wizard = self.window()
        if wizard and isinstance(wizard, QDialog):
            wizard.accept()
    
    def set_distro_name(self, name: str):
        self.info_label.setText(f"WSL 分发 '{name}' 已创建并配置完成")
        self.confirm_btn.setVisible(True)


class CreateDistroWizard(QDialog):
    """创建分发向导"""
    
    distro_created = pyqtSignal(str)
    
    def __init__(self, wsl_manager, config_manager, nanobot_controller=None, parent=None):
        super().__init__(parent)
        self._wsl_manager = wsl_manager
        self._config_manager = config_manager
        self._nanobot_controller = nanobot_controller
        self._current_step = 0
        self._config_data: Dict[str, Any] = {}
        
        self._init_ui()
        self._apply_styles()
    
    def _init_ui(self):
        self.setWindowTitle("创建 WSL 分发")
        self.setMinimumSize(600, 550)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(24, 24, 24, 0)
        
        self.step_label = QLabel("Step 1/7: 基本信息")
        self.step_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")
        header_layout.addWidget(self.step_label)
        
        layout.addLayout(header_layout)
        
        self.content_stack = QStackedWidget()
        self._create_pages()
        layout.addWidget(self.content_stack, 1)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.setContentsMargins(24, 0, 24, 24)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        btn_layout.addStretch()
        
        self.prev_btn = QPushButton("上一步")
        self.prev_btn.clicked.connect(self._on_prev)
        self.prev_btn.setVisible(False)
        btn_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("下一步")
        self.next_btn.setObjectName("primary")
        self.next_btn.clicked.connect(self._on_next)
        btn_layout.addWidget(self.next_btn)
        
        layout.addLayout(btn_layout)
        
        self._connect_signals()
    
    def _create_pages(self):
        self.basic_info_page = BasicInfoPage(self._wsl_manager, self)
        self.init_progress_page = InitProgressPage(self._wsl_manager, self)
        self.workspace_page = WorkspacePage(self._wsl_manager, self._config_manager, self)
        self.llm_config_page = LLMConfigPage(
            self._wsl_manager,
            lambda: self._config_data.get("distro_name"),
            self
        )
        self.channels_page = ChannelsPage(self)
        self.apply_config_page = ApplyConfigPage(
            self._wsl_manager, 
            self._config_manager,
            self._nanobot_controller,
            self
        )
        self.success_page = SuccessPage(self)
        
        self.content_stack.addWidget(self.basic_info_page)
        self.content_stack.addWidget(self.init_progress_page)
        self.content_stack.addWidget(self.workspace_page)
        self.content_stack.addWidget(self.llm_config_page)
        self.content_stack.addWidget(self.channels_page)
        self.content_stack.addWidget(self.apply_config_page)
        self.content_stack.addWidget(self.success_page)
    
    def _connect_signals(self):
        self.init_progress_page.init_completed.connect(self._on_init_completed, Qt.ConnectionType.QueuedConnection)
        self.apply_config_page.apply_completed.connect(self._on_apply_completed, Qt.ConnectionType.QueuedConnection)
    
    def _apply_styles(self):
        self.setStyleSheet(WIZARD_STYLE)
    
    def _update_step_label(self):
        steps = [
            "Step 1/7: 基本信息",
            "Step 2/7: 初始化 WSL",
            "Step 3/7: 工作空间设置",
            "Step 4/7: LLM 配置",
            "Step 5/7: Channels 配置",
            "Step 6/7: 应用配置",
            "Step 7/7: 完成"
        ]
        logger.info(f"_update_step_label: current_step={self._current_step}, text={steps[self._current_step]}")
        self.step_label.setText(steps[self._current_step])
    
    def _update_buttons(self):
        logger.info(f"_update_buttons: current_step={self._current_step}")
        if self._current_step == 0:
            self.prev_btn.setVisible(False)
            self.next_btn.setText("下一步")
            self.next_btn.setEnabled(True)
            self.cancel_btn.setVisible(True)
        elif self._current_step == 1:
            self.prev_btn.setVisible(False)
            self.next_btn.setVisible(False)
            self.cancel_btn.setVisible(True)
        elif self._current_step == 2:
            self.prev_btn.setVisible(False)
            self.next_btn.setVisible(True)
            self.next_btn.setText("下一步")
            self.next_btn.setEnabled(True)
            self.cancel_btn.setVisible(True)
        elif self._current_step == 6:
            self.prev_btn.setVisible(False)
            self.next_btn.setVisible(False)
            self.cancel_btn.setVisible(False)
        elif self._current_step == 5:
            self.prev_btn.setVisible(False)
            self.next_btn.setVisible(False)
            self.cancel_btn.setVisible(True)
        else:
            self.prev_btn.setVisible(True)
            self.next_btn.setVisible(True)
            self.next_btn.setText("下一步")
            self.next_btn.setEnabled(True)
            self.cancel_btn.setVisible(True)
        logger.info(f"_update_buttons 完成")
    
    def _go_to_step(self, step: int):
        logger.info(f"_go_to_step: {self._current_step} -> {step}")
        self._current_step = step
        self.content_stack.setCurrentIndex(step)
        self._update_step_label()
        self._update_buttons()
        logger.info(f"_go_to_step 完成: current_step={self._current_step}")
    
    def _on_prev(self):
        if self._current_step > 0:
            self._current_step -= 1
            self.content_stack.setCurrentIndex(self._current_step)
            self._update_step_label()
            self._update_buttons()
    
    def _on_next(self):
        try:
            if self._current_step == 0:
                if not self.basic_info_page.validate():
                    return
                self._config_data.update(self.basic_info_page.get_data())
                self._go_to_step(1)
                self.init_progress_page.start_init(
                    self._config_data.get("distro_name"),
                    self._config_data.get("install_location")
                )
            elif self._current_step == 2:
                self._config_data.update(self.workspace_page.get_data())
                self._go_to_step(3)
            elif self._current_step == 3:
                if self.llm_config_page.needs_oauth():
                    self.next_btn.setEnabled(False)
                    self.llm_config_page.start_oauth_if_needed(self._on_oauth_completed)
                else:
                    self._config_data.update(self.llm_config_page.get_data())
                    self._go_to_step(4)
            elif self._current_step == 4:
                logger.info("Step 4: 获取 Channels 配置数据...")
                channels_data = self.channels_page.get_data()
                logger.info(f"Channels 数据: {channels_data}")
                self._config_data.update(channels_data)
                logger.info("跳转到 Step 5...")
                self._go_to_step(5)
                logger.info("启动应用配置...")
                self.apply_config_page.start_apply(self._config_data)
            elif self._current_step == 6:
                self.distro_created.emit(self._config_data.get("distro_name", ""))
                self.accept()
            else:
                self._go_to_step(self._current_step + 1)
        except Exception as e:
            logger.error(f"_on_next 异常: {e}\n{traceback.format_exc()}")
            show_critical(self, "错误", f"操作失败:\n{str(e)}")
    
    def _on_init_completed(self, success: bool, message: str):
        if success:
            self._go_to_step(2)
        else:
            show_critical(self, "初始化失败", f"WSL 初始化失败:\n{message}")
            self._go_to_step(0)
    
    def _on_oauth_completed(self, success: bool):
        """OAuth 登录完成回调"""
        self.next_btn.setEnabled(True)
        if success:
            self._config_data.update(self.llm_config_page.get_data())
            self._go_to_step(4)
    
    def _on_apply_completed(self, success: bool, message: str):
        logger.info(f"_on_apply_completed 被调用: success={success}, message={message}")
        try:
            if success:
                logger.info("设置成功页面分发名称...")
                distro_name = self._config_data.get("distro_name", "")
                self.success_page.set_distro_name(distro_name)
                logger.info(f"分发名称设置完成: {distro_name}")
                logger.info("跳转到成功页面 (Step 6)...")
                self._go_to_step(6)
                logger.info("跳转完成")
            else:
                show_critical(self, "配置失败", f"配置应用失败:\n{message}")
                self._go_to_step(4)
        except Exception as e:
            logger.error(f"_on_apply_completed 异常: {e}\n{traceback.format_exc()}")
