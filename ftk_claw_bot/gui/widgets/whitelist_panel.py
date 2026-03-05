"""
白名单管理面板

功能：
1. 显示已授权应用列表
2. 添加新应用到白名单
3. 从白名单移除应用
4. 编辑应用别名
"""

import os
from datetime import datetime
from typing import Optional, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QFileDialog,
    QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
    QGroupBox, QInputDialog, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from ...services.app_whitelist import whitelist_manager, AppInfo
from ...utils.i18n import tr


class AddAppDialog(QDialog):
    """添加应用对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("whitelist.add_app.title", "添加应用到白名单"))
        self.setMinimumWidth(500)
        self._result: Optional[AppInfo] = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # 表单
        form_group = QGroupBox(tr("whitelist.add_app.form", "应用信息"))
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(12)
        
        # 应用名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(tr("whitelist.placeholder.name", "如: notepad"))
        form_layout.addRow(tr("whitelist.label.name", "名称:"), self.name_edit)
        
        # 应用路径
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(tr("whitelist.placeholder.path", "可执行文件路径"))
        self.browse_btn = QPushButton(tr("btn.browse", "浏览..."))
        self.browse_btn.clicked.connect(self._browse_file)
        path_layout.addWidget(self.path_edit, 1)
        path_layout.addWidget(self.browse_btn)
        form_layout.addRow(tr("whitelist.label.path", "路径:"), path_layout)
        
        # 别名
        self.aliases_edit = QLineEdit()
        self.aliases_edit.setPlaceholderText(tr("whitelist.placeholder.aliases", "多个别名用逗号分隔，如: notepad, 记事本"))
        form_layout.addRow(tr("whitelist.label.aliases", "别名:"), self.aliases_edit)
        
        # 描述
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText(tr("whitelist.placeholder.desc", "应用描述（可选）"))
        form_layout.addRow(tr("whitelist.label.desc", "描述:"), self.desc_edit)
        
        layout.addWidget(form_group)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _browse_file(self):
        """浏览选择可执行文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("whitelist.browse.title", "选择可执行文件"),
            "",
            tr("whitelist.browse.filter", "可执行文件 (*.exe);;所有文件 (*.*)")
        )
        if file_path:
            self.path_edit.setText(file_path)
            # 自动填充名称
            if not self.name_edit.text():
                name = os.path.splitext(os.path.basename(file_path))[0]
                self.name_edit.setText(name)
    
    def _accept(self):
        """验证并接受"""
        name = self.name_edit.text().strip()
        path = self.path_edit.text().strip()
        
        if not name:
            QMessageBox.warning(
                self, 
                tr("error.title", "错误"), 
                tr("whitelist.error.name_required", "请输入应用名称")
            )
            return
    def _accept(self):
        """验证并接受"""
        name = self.name_edit.text().strip()
        path = self.path_edit.text().strip()
        
        if not name:
            QMessageBox.warning(
                self, 
                tr("error.title", "错误"), 
                tr("whitelist.error.name_required", "请输入应用名称")
            )
            return
        
        if not path:
            QMessageBox.warning(
                self, 
                tr("error.title", "错误"), 
                tr("whitelist.error.path_required", "请选择或输入应用路径")
            )
            return
        
        # 解析别名
        aliases_text = self.aliases_edit.text().strip()
        aliases = [a.strip() for a in aliases_text.split(",") if a.strip()] if aliases_text else []
        
        # 添加名称作为默认别名
        if name not in aliases:
            aliases.insert(0, name)
        
        self._result = AppInfo(
            name=name,
            path=path,
            aliases=aliases,
            description=self.desc_edit.text().strip(),
            added_at=datetime.now().isoformat()
        )
        self.accept()
    
    def get_result(self) -> Optional[AppInfo]:
        return self._result


class AppListItem(QWidget):
    """应用列表项组件"""
    
    edit_requested = pyqtSignal(str)  # 应用名称
    delete_requested = pyqtSignal(str)  # 应用名称
    
    def __init__(self, app_info: AppInfo, parent=None):
        super().__init__(parent)
        self._app_info = app_info
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # 应用信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # 名称
        name_label = QLabel(self._app_info.name)
        name_font = QFont()
        name_font.setBold(True)
        name_label.setFont(name_font)
        info_layout.addWidget(name_label)
        
        # 路径
        path_label = QLabel(self._app_info.path)
        path_label.setStyleSheet("color: #666; font-size: 11px;")
        path_label.setWordWrap(True)
        info_layout.addWidget(path_label)
        
        # 别名
        if self._app_info.aliases:
            aliases_text = ", ".join(self._app_info.aliases)
            aliases_label = QLabel(f"别名: {aliases_text}")
            aliases_label.setStyleSheet("color: #888; font-size: 10px;")
            info_layout.addWidget(aliases_label)
        
        layout.addLayout(info_layout, 1)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        edit_btn = QPushButton(tr("btn.edit", "编辑"))
        edit_btn.setObjectName("smallButton")
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._app_info.name))
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton(tr("btn.delete", "删除"))
        delete_btn.setObjectName("smallButton")
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._app_info.name))
        btn_layout.addWidget(delete_btn)
        
        layout.addLayout(btn_layout)
    
    def get_app_info(self) -> AppInfo:
        return self._app_info


class WhitelistPanel(QWidget):
    """白名单管理面板"""
    
    config_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load_apps()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # 标题和操作按钮
        header = QHBoxLayout()
        
        title = QLabel(tr("whitelist.title", "应用白名单"))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        header.addWidget(title)
        
        header.addStretch()
        
        # 添加按钮
        add_btn = QPushButton(tr("whitelist.btn.add", "+ 添加应用"))
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._add_app)
        header.addWidget(add_btn)
        
        # 刷新按钮
        refresh_btn = QPushButton(tr("btn.refresh", "刷新"))
        refresh_btn.clicked.connect(self._load_apps)
        header.addWidget(refresh_btn)
        
        layout.addLayout(header)
        
        # 说明
        desc = QLabel(
            tr("whitelist.desc", "白名单中的应用可以被 AI 助手启动。请只添加您信任的应用。")
        )
        desc.setStyleSheet("color: #666; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # 应用列表
        list_group = QGroupBox(tr("whitelist.group.authorized", "已授权应用"))
        list_layout = QVBoxLayout(list_group)
        list_layout.setContentsMargins(8, 8, 8, 8)
        list_layout.setSpacing(8)
        
        self.app_list = QListWidget()
        self.app_list.setAlternatingRowColors(True)
        self.app_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.app_list.setMinimumHeight(300)
        list_layout.addWidget(self.app_list)
        
        # 空状态提示
        self.empty_label = QLabel(tr("whitelist.empty", "暂无授权应用，点击上方按钮添加"))
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; padding: 40px;")
        list_layout.addWidget(self.empty_label)
        
        layout.addWidget(list_group, 1)
        
        # 快速添加常用应用
        quick_group = QGroupBox(tr("whitelist.group.quick_add", "快速添加常用应用"))
        quick_layout = QHBoxLayout(quick_group)
        quick_layout.setSpacing(8)
        
        common_apps = [
            ("notepad", "C:\\Windows\\System32\\notepad.exe"),
            ("chrome", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"),
            ("edge", "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"),
            ("explorer", "C:\\Windows\\explorer.exe"),
        ]
        
        for app_name, app_path in common_apps:
            btn = QPushButton(app_name)
            btn.setObjectName("smallButton")
            btn.clicked.connect(lambda checked, n=app_name, p=app_path: self._quick_add_app(n, p))
            quick_layout.addWidget(btn)
        
        quick_layout.addStretch()
        layout.addWidget(quick_group)
    
    def _load_apps(self):
        """加载应用列表"""
        self.app_list.clear()
        
        apps = whitelist_manager.get_all_apps()
        
        self.empty_label.setVisible(len(apps) == 0)
        
        for name, app_info in apps.items():
            item = QListWidgetItem(self.app_list)
            widget = AppListItem(app_info)
            widget.edit_requested.connect(self._edit_app)
            widget.delete_requested.connect(self._delete_app)
            item.setSizeHint(widget.sizeHint())
            self.app_list.setItemWidget(item, widget)
    
    def _add_app(self):
        """添加应用"""
        dialog = AddAppDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            app_info = dialog.get_result()
            if app_info:
                if whitelist_manager.add_app(
                    name=app_info.name,
                    path=app_info.path,
                    aliases=app_info.aliases,
                    description=app_info.description,
                    create_shortcut=False,  # 不创建快捷方式，只保存配置
                    skip_path_validation=True  # WSL 环境无法验证 Windows 路径
                ):
                    self._load_apps()
                    self.config_changed.emit()
                else:
                    QMessageBox.warning(
                        self,
                        tr("error.title", "错误"),
                        tr("whitelist.error.add_failed", "添加失败，应用可能已存在或路径无效")
                    )
    
    def _quick_add_app(self, name: str, path: str):
        """快速添加常用应用"""
        # 检查是否已存在
        if whitelist_manager.is_allowed(name):
            QMessageBox.information(
                self,
                tr("info.title", "提示"),
                tr("whitelist.info.already_exists", "应用已在白名单中")
            )
            return
        
        # 检查路径是否存在（Windows 端检查）
        # 由于我们在 WSL 环境，路径检查在 Windows 端进行
        if whitelist_manager.add_app(
            name=name,
            path=path,
            aliases=[name, name.lower()],
            description=f"快速添加: {name}",
            create_shortcut=False,
            skip_path_validation=True  # WSL 环境无法验证 Windows 路径
        ):
            self._load_apps()
            self.config_changed.emit()
        else:
            QMessageBox.warning(
                self,
                tr("error.title", "错误"),
                tr("whitelist.error.quick_add_failed", "快速添加失败，应用可能已存在")
            )
    
    def _edit_app(self, name: str):
        """编辑应用别名"""
        app_info = whitelist_manager.get_app_info(name)
        if not app_info:
            return
        
        # 弹出对话框编辑别名
        current_aliases = ", ".join(app_info.aliases)
        text, ok = QInputDialog.getText(
            self,
            tr("whitelist.edit_aliases.title", "编辑别名"),
            tr("whitelist.edit_aliases.prompt", "输入别名（多个用逗号分隔）:"),
            QLineEdit.EchoMode.Normal,
            current_aliases
        )
        
        if ok:
            new_aliases = [a.strip() for a in text.split(",") if a.strip()]
            # 确保名称在别名中
            if name not in new_aliases:
                new_aliases.insert(0, name)
            
            app_info.aliases = new_aliases
            whitelist_manager._save_config()
            self._load_apps()
            self.config_changed.emit()
    
    def _delete_app(self, name: str):
        """删除应用"""
        reply = QMessageBox.question(
            self,
            tr("whitelist.delete.title", "确认删除"),
            tr("whitelist.delete.message", "确定要从白名单移除 '{name}' 吗？").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if whitelist_manager.remove_app(name):
                self._load_apps()
                self.config_changed.emit()
    
    def get_config(self) -> dict:
        """获取当前配置"""
        return {
            "apps": {name: info.to_dict() for name, info in whitelist_manager.get_all_apps().items()}
        }
    
    def set_config(self, config: dict):
        """设置配置"""
        # 白名单配置由 whitelist_manager 管理，这里不需要额外处理
        self._load_apps()
