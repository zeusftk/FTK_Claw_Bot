# -*- coding: utf-8 -*-
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QLineEdit, QFrame, QScrollArea,
    QGroupBox, QSplitter, QTextEdit, QSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from ...models import SkillsConfig, BUILTIN_SKILLS, get_all_builtin_skills, DEFAULT_PRIORITY


class SkillSyncWorker(QThread):
    """后台线程从WSL同步技能列表"""
    finished = pyqtSignal(list)  # List[Dict[str, Any]]
    error = pyqtSignal(str)

    def __init__(self, wsl_manager=None, distro_name: str = "", workspace: str = ""):
        super().__init__()
        self._wsl_manager = wsl_manager
        self._distro_name = distro_name
        self._workspace = workspace

    def run(self):
        if not self._wsl_manager or not self._distro_name:
            self.error.emit("未配置WSL管理器或分发名称")
            return

        if not self._workspace:
            self.error.emit("未配置工作空间路径")
            return

        try:
            # 执行 Python 脚本获取技能列表
            # 注意：不能使用 __file__，因为 -c 执行时不存在
            cmd = f'''
import json
import sys
import subprocess
from pathlib import Path

workspace = Path("{self._workspace}").expanduser()

# 查找 clawbot 内置技能目录
builtin_skills_dir = None
try:
    # 方法1: 通过 pip show 查找
    result = subprocess.run(["pip", "show", "clawbot"], capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        for line in result.stdout.split("\\n"):
            if line.startswith("Location:"):
                location = line.split(":", 1)[1].strip()
                builtin_skills_dir = Path(location) / "clawbot" / "skills"
                break
except Exception:
    pass

# 方法2: 尝试导入 clawbot 查找
if not builtin_skills_dir or not builtin_skills_dir.exists():
    try:
        import clawbot
        builtin_skills_dir = Path(clawbot.__file__).parent / "skills"
    except Exception:
        pass

skills = []

# 扫描工作空间技能
ws_skills_dir = workspace / "skills"
if ws_skills_dir.exists():
    for skill_dir in ws_skills_dir.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                skills.append({{"name": skill_dir.name, "source": "workspace", "path": str(skill_file)}})

# 扫描内置技能
if builtin_skills_dir and builtin_skills_dir.exists():
    for skill_dir in builtin_skills_dir.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists() and not any(s["name"] == skill_dir.name for s in skills):
                skills.append({{"name": skill_dir.name, "source": "builtin", "path": str(skill_file)}})

print(json.dumps(skills))
'''
            result = self._wsl_manager.execute_command(
                self._distro_name,
                f"python3 -c '{cmd}'",
                timeout=30
            )
            
            if result.success:
                import json
                stdout = result.stdout.strip()
                if not stdout:
                    self.finished.emit([])
                    return
                try:
                    skills = json.loads(stdout)
                    if not isinstance(skills, list):
                        self.error.emit(f"返回数据格式错误: 期望列表，得到 {type(skills).__name__}")
                        return
                    self.finished.emit(skills)
                except json.JSONDecodeError as e:
                    self.error.emit(f"解析技能列表失败: {e}")
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                self.error.emit(f"获取技能列表失败: {error_msg}")
        except Exception as e:
            self.error.emit(f"同步异常: {str(e)}")


class SkillItemWidget(QFrame):
    toggled = pyqtSignal(str, bool)
    selected = pyqtSignal(str)

    def __init__(self, skill_name: str, skill_info: dict, enabled: bool = True, priority: int = DEFAULT_PRIORITY, source: str = "builtin", parent=None):
        super().__init__(parent)
        self._skill_name = skill_name
        self._skill_info = skill_info
        self._enabled = enabled
        self._priority = priority
        self._source = source  # "builtin" or "workspace"
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("skillItem")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self._enabled)
        self.checkbox.stateChanged.connect(self._on_toggled)
        layout.addWidget(self.checkbox)

        icon_label = QLabel(self._skill_info.get("icon", "📄"))
        icon_label.setStyleSheet("font-size: 20px;")
        icon_label.setFixedWidth(28)
        layout.addWidget(icon_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # 名称行（包含来源标签）
        name_row = QHBoxLayout()
        name_label = QLabel(self._skill_info.get("name", self._skill_name))
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        name_row.addWidget(name_label)
        
        # 来源标签
        source_label = QLabel("内置" if self._source == "builtin" else "工作空间")
        source_color = "#238636" if self._source == "builtin" else "#a371f7"
        source_label.setStyleSheet(f"""
            QLabel {{
                background-color: {source_color};
                color: white;
                padding: 1px 6px;
                border-radius: 3px;
                font-size: 10px;
            }}
        """)
        name_row.addWidget(source_label)
        name_row.addStretch()
        info_layout.addLayout(name_row)

        desc_label = QLabel(self._skill_info.get("description", ""))
        desc_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label)

        layout.addLayout(info_layout, 1)

        requires = self._skill_info.get("requires", [])
        if requires:
            req_label = QLabel(f"依赖: {', '.join(requires)}")
            req_label.setStyleSheet("color: #f0883e; font-size: 11px;")
            layout.addWidget(req_label)

        # 优先级显示
        priority_label = QLabel(f"P{self._priority}")
        priority_label.setStyleSheet("""
            QLabel {
                background-color: #238636;
                color: white;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        priority_label.setToolTip(f"优先级: {self._priority} (值越大优先级越高)")
        layout.addWidget(priority_label)

        self.setProperty("selected", False)

    def _on_toggled(self, state):
        self._enabled = state == Qt.CheckState.Checked.value
        self.toggled.emit(self._skill_name, self._enabled)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self._skill_name)
        super().mousePressEvent(event)

    def is_enabled(self) -> bool:
        return self._enabled

    def get_skill_name(self) -> str:
        return self._skill_name

    def set_selected(self, selected: bool):
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def get_priority(self) -> int:
        return self._priority

    def set_priority(self, priority: int):
        self._priority = priority
        # 更新优先级标签
        for child in self.findChildren(QLabel):
            if child.text().startswith("P") and child.text()[1:].isdigit():
                child.setText(f"P{priority}")
                child.setToolTip(f"优先级: {priority} (值越大优先级越高)")
                break


class SkillDetailWidget(QFrame):
    config_changed = pyqtSignal()
    priority_changed = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_skill_name: Optional[str] = None
        self._skill_info: Optional[dict] = None
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("skillDetailWidget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self.icon_label = QLabel("📄")
        self.icon_label.setStyleSheet("font-size: 24px;")
        header.addWidget(self.icon_label)

        self.name_label = QLabel("选择技能查看详情")
        self.name_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        header.addWidget(self.name_label, 1)
        layout.addLayout(header)

        self.desc_label = QLabel("点击左侧技能列表中的技能项查看详细信息")
        self.desc_label.setStyleSheet("color: #8b949e; font-size: 13px;")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        # 优先级设置
        priority_group = QGroupBox("优先级设置")
        priority_layout = QHBoxLayout(priority_group)
        priority_layout.setSpacing(12)

        priority_hint = QLabel("优先级:")
        priority_hint.setFixedWidth(60)
        priority_layout.addWidget(priority_hint)

        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 1000)
        self.priority_spin.setValue(DEFAULT_PRIORITY)
        self.priority_spin.setToolTip("值越大优先级越高 (1-1000)，高优先级技能将优先执行")
        self.priority_spin.valueChanged.connect(self._on_priority_changed)
        priority_layout.addWidget(self.priority_spin)

        priority_desc = QLabel("(值越大优先级越高，范围 1-1000)")
        priority_desc.setStyleSheet("color: #8b949e; font-size: 12px;")
        priority_layout.addWidget(priority_desc)
        priority_layout.addStretch()

        layout.addWidget(priority_group)

        self.params_group = QGroupBox("参数配置")
        self.params_layout = QVBoxLayout(self.params_group)
        self.params_layout.setSpacing(8)
        self.params_group.hide()
        layout.addWidget(self.params_group)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("在此输入技能相关的备注或配置说明...")
        self.notes_edit.setMaximumHeight(100)
        self.notes_edit.setVisible(False)
        layout.addWidget(self.notes_edit)

        layout.addStretch()

    def _on_priority_changed(self, value: int):
        if self._current_skill_name:
            self.priority_changed.emit(self._current_skill_name, value)
            self.config_changed.emit()

    def set_skill(self, skill_name: str, skill_info: dict, priority: int = DEFAULT_PRIORITY):
        self._current_skill_name = skill_name
        self._skill_info = skill_info

        self.icon_label.setText(skill_info.get("icon", "📄"))
        self.name_label.setText(skill_info.get("name", skill_name))
        self.desc_label.setText(skill_info.get("description", ""))

        # 设置优先级（暂时断开信号避免触发）
        self.priority_spin.blockSignals(True)
        self.priority_spin.setValue(priority)
        self.priority_spin.blockSignals(False)

        params = skill_info.get("params", {})
        self._clear_params()

        if params:
            self.params_group.show()
            for param_name, param_info in params.items():
                param_row = QHBoxLayout()
                param_label = QLabel(f"{param_info.get('label', param_name)}:")
                param_label.setFixedWidth(100)
                param_row.addWidget(param_label)

                param_edit = QLineEdit()
                param_edit.setPlaceholderText(param_info.get("placeholder", ""))
                param_edit.setObjectName(f"param_{param_name}")
                param_row.addWidget(param_edit, 1)

                self.params_layout.addLayout(param_row)
        else:
            self.params_group.hide()

        self.notes_edit.setVisible(True)

    def _clear_params(self):
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_sublayout(item.layout())

    def _clear_sublayout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_sublayout(item.layout())

    def clear(self):
        self._current_skill_name = None
        self._skill_info = None
        self.icon_label.setText("📄")
        self.name_label.setText("选择技能查看详情")
        self.desc_label.setText("点击左侧技能列表中的技能项查看详细信息")
        self._clear_params()
        self.params_group.hide()
        self.notes_edit.setVisible(False)
        self.notes_edit.clear()
        self.priority_spin.blockSignals(True)
        self.priority_spin.setValue(DEFAULT_PRIORITY)
        self.priority_spin.blockSignals(False)


class SkillsConfigWidget(QWidget):
    config_changed = pyqtSignal()
    skills_synced = pyqtSignal()  # 技能列表同步完成信号

    def __init__(self, config: SkillsConfig = None, wsl_manager=None, distro_name: str = "", workspace: str = "", parent=None):
        super().__init__(parent)
        self._config = config or SkillsConfig()
        self._wsl_manager = wsl_manager
        self._distro_name = distro_name
        self._workspace = workspace
        self._skill_widgets: dict[str, SkillItemWidget] = {}
        self._current_selected_skill: Optional[str] = None
        self._all_skills: List[Dict[str, Any]] = []  # 缓存所有技能数据
        self._sync_worker: Optional[SkillSyncWorker] = None
        self._init_ui()
        self._load_skills()

    def set_wsl_context(self, wsl_manager, distro_name: str, workspace: str, auto_sync: bool = False):
        """设置 WSL 上下文，用于同步技能
        
        Args:
            wsl_manager: WSL 管理器实例
            distro_name: WSL 分发名称
            workspace: 工作空间路径
            auto_sync: 是否自动触发同步
        """
        self._wsl_manager = wsl_manager
        self._distro_name = distro_name
        self._workspace = workspace
        
        if auto_sync and wsl_manager and distro_name and workspace:
            self._sync_from_wsl()

    def cleanup(self):
        """清理资源，在 widget 销毁前调用"""
        if self._sync_worker and self._sync_worker.isRunning():
            self._sync_worker.terminate()
            self._sync_worker.wait(1000)  # 等待最多1秒

    def closeEvent(self, event):
        """重写关闭事件，确保清理线程"""
        self.cleanup()
        super().closeEvent(event)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 搜索技能...")
        self.search_edit.textChanged.connect(self._filter_skills)
        search_row.addWidget(self.search_edit, 1)

        # 同步WSL技能按钮
        self.sync_btn = QPushButton("📤 同步WSL")
        self.sync_btn.setToolTip("从WSL同步技能列表")
        self.sync_btn.setObjectName("smallButton")
        self.sync_btn.clicked.connect(self._sync_from_wsl)
        search_row.addWidget(self.sync_btn)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("刷新技能列表")
        refresh_btn.setObjectName("smallButton")
        refresh_btn.setFixedSize(50, 32)
        refresh_btn.clicked.connect(self._refresh_skills)
        search_row.addWidget(refresh_btn)

        enable_all_btn = QPushButton("全部启用")
        enable_all_btn.setObjectName("smallButton")
        enable_all_btn.clicked.connect(self._enable_all)

        disable_all_btn = QPushButton("全部禁用")
        disable_all_btn.setObjectName("smallButton")
        disable_all_btn.clicked.connect(self._disable_all)

        # 打开工作空间技能文件夹按钮
        open_skills_btn = QPushButton("📂 技能目录")
        open_skills_btn.setToolTip("打开工作空间技能文件夹")
        open_skills_btn.setObjectName("smallButton")
        open_skills_btn.clicked.connect(self._open_skills_folder)

        search_row.addWidget(enable_all_btn)
        search_row.addWidget(disable_all_btn)
        search_row.addWidget(open_skills_btn)
        layout.addLayout(search_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QFrame()
        left_panel.setObjectName("skillsListPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # 技能列表（使用单个滚动区域，分组显示）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        skills_container = QWidget()
        self.skills_layout = QVBoxLayout(skills_container)
        self.skills_layout.setContentsMargins(0, 0, 0, 0)
        self.skills_layout.setSpacing(4)

        scroll.setWidget(skills_container)
        left_layout.addWidget(scroll)

        splitter.addWidget(left_panel)

        right_panel = QFrame()
        right_panel.setObjectName("skillDetailPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._detail_widget = SkillDetailWidget()
        self._detail_widget.priority_changed.connect(self._on_priority_changed)
        right_layout.addWidget(self._detail_widget)

        splitter.addWidget(right_panel)
        splitter.setSizes([400, 300])

        layout.addWidget(splitter, 1)

        # 同步状态标签
        self.sync_status_label = QLabel("")
        self.sync_status_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(self.sync_status_label)

    def _load_skills(self):
        """加载技能列表，合并内置技能和 WSL 同步的技能"""
        # 清空现有 widgets
        for widget in self._skill_widgets.values():
            widget.deleteLater()
        self._skill_widgets.clear()

        # 彻底清空所有控件（包括分组标签）
        while self.skills_layout.count() > 0:
            item = self.skills_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # 递归清理子布局
                self._clear_layout(item.layout())

        # 分组：内置技能和工作空间技能
        builtin_skills = []
        workspace_skills = []

        # 首先添加内置技能
        for skill_info in get_all_builtin_skills():
            skill_name = skill_info.get("name", "")
            builtin_skills.append({
                "name": skill_name,
                "info": skill_info,
                "source": "builtin"
            })

        # 然后添加从 WSL 同步的技能（如果有）
        for skill_data in self._all_skills:
            skill_name = skill_data.get("name", "")
            source = skill_data.get("source", "builtin")
            
            # 跳过已经在内置技能中的
            if source == "builtin" and any(s["name"] == skill_name for s in builtin_skills):
                continue
            
            # 工作空间技能
            if source == "workspace":
                skill_info = {
                    "name": skill_name,
                    "description": skill_data.get("description", f"工作空间技能: {skill_name}"),
                    "icon": skill_data.get("icon", "📁"),
                    "requires": skill_data.get("requires", []),
                }
                workspace_skills.append({
                    "name": skill_name,
                    "info": skill_info,
                    "source": "workspace"
                })

        # 添加内置技能分组
        if builtin_skills:
            builtin_label = QLabel("内置技能")
            builtin_label.setObjectName("skillGroupLabel")  # 添加对象名便于清理
            builtin_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #58a6ff; margin-top: 8px;")
            self.skills_layout.addWidget(builtin_label)

            for skill in builtin_skills:
                self._add_skill_widget(skill["name"], skill["info"], skill["source"])

        # 添加工作空间技能分组
        if workspace_skills:
            ws_label = QLabel("工作空间技能")
            ws_label.setObjectName("skillGroupLabel")  # 添加对象名便于清理
            ws_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #a371f7; margin-top: 12px;")
            self.skills_layout.addWidget(ws_label)

            for skill in workspace_skills:
                self._add_skill_widget(skill["name"], skill["info"], skill["source"])

        self.skills_layout.addStretch()

    def _clear_layout(self, layout):
        """递归清理布局"""
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _add_skill_widget(self, skill_name: str, skill_info: dict, source: str):
        """添加单个技能 widget"""
        enabled = self._config.is_skill_enabled(skill_name)
        priority = self._config.get_skill_priority(skill_name)

        widget = SkillItemWidget(skill_name, skill_info, enabled, priority, source)
        widget.toggled.connect(self._on_skill_toggled)
        widget.selected.connect(self._on_skill_selected)

        self._skill_widgets[skill_name] = widget
        self.skills_layout.addWidget(widget)

    def _sync_from_wsl(self):
        """从 WSL 同步技能列表"""
        if not self._wsl_manager or not self._distro_name:
            QMessageBox.warning(self, "同步失败", "未配置 WSL 管理器或分发名称，无法同步技能列表")
            return

        if not self._workspace:
            QMessageBox.warning(self, "同步失败", "未配置工作空间路径，无法同步技能列表")
            return

        self.sync_btn.setEnabled(False)
        self.sync_status_label.setText("正在同步技能列表...")

        # 创建后台工作线程
        self._sync_worker = SkillSyncWorker(
            self._wsl_manager,
            self._distro_name,
            self._workspace
        )
        self._sync_worker.finished.connect(self._on_sync_finished)
        self._sync_worker.error.connect(self._on_sync_error)
        self._sync_worker.start()

    def _on_sync_finished(self, skills: List[Dict[str, Any]]):
        """同步完成"""
        self._all_skills = skills
        self.sync_btn.setEnabled(True)
        self.sync_status_label.setText(f"同步完成，共 {len(skills)} 个技能")
        self._load_skills()
        self.skills_synced.emit()

    def _on_sync_error(self, error_msg: str):
        """同步失败"""
        self.sync_btn.setEnabled(True)
        self.sync_status_label.setText(f"同步失败: {error_msg}")
        QMessageBox.warning(self, "同步失败", error_msg)

    def _refresh_skills(self):
        self._load_skills()

    def _on_skill_selected(self, skill_name: str):
        if self._current_selected_skill and self._current_selected_skill in self._skill_widgets:
            self._skill_widgets[self._current_selected_skill].set_selected(False)

        self._current_selected_skill = skill_name

        if skill_name in self._skill_widgets:
            self._skill_widgets[skill_name].set_selected(True)
            # 从内置技能或缓存数据获取技能信息
            skill_info = BUILTIN_SKILLS.get(skill_name, {})
            if not skill_info:
                # 从缓存数据中查找
                for s in self._all_skills:
                    if s.get("name") == skill_name:
                        skill_info = {
                            "name": skill_name,
                            "description": s.get("description", ""),
                            "icon": s.get("icon", "📄"),
                        }
                        break
            priority = self._config.get_skill_priority(skill_name)
            self._detail_widget.set_skill(skill_name, skill_info, priority)

    def _filter_skills(self, keyword: str):
        keyword = keyword.lower().strip()
        for skill_name, widget in self._skill_widgets.items():
            # 从内置技能获取信息
            skill_info = BUILTIN_SKILLS.get(skill_name, {})
            if not skill_info:
                # 从缓存数据中查找
                for s in self._all_skills:
                    if s.get("name") == skill_name:
                        skill_info = s
                        break
            
            name = skill_info.get("name", skill_name).lower()
            desc = skill_info.get("description", "").lower()

            if keyword:
                visible = keyword in name or keyword in desc
                widget.setVisible(visible)
            else:
                widget.setVisible(True)

    def _on_skill_toggled(self, skill_name: str, enabled: bool):
        if enabled:
            self._config.enable_skill(skill_name)
        else:
            self._config.disable_skill(skill_name)
        self._on_config_changed()

    def _on_priority_changed(self, skill_name: str, priority: int):
        self._config.set_skill_priority(skill_name, priority)
        # 更新列表中的优先级显示
        if skill_name in self._skill_widgets:
            self._skill_widgets[skill_name].set_priority(priority)
        self._on_config_changed()

    def _on_config_changed(self):
        self.config_changed.emit()

    def _enable_all(self):
        for widget in self._skill_widgets.values():
            widget.checkbox.setChecked(True)

    def _disable_all(self):
        for widget in self._skill_widgets.values():
            widget.checkbox.setChecked(False)

    def _open_skills_folder(self):
        """打开工作空间技能文件夹"""
        import subprocess
        import platform
        
        if not self._workspace:
            QMessageBox.warning(self, "无法打开", "未配置工作空间路径")
            return
        
        # 构建技能目录路径
        from pathlib import Path
        skills_path = Path(self._workspace).expanduser() / "skills"
        
        # 确保目录存在
        skills_path.mkdir(parents=True, exist_ok=True)
        
        # 根据平台打开文件夹
        system = platform.system()
        try:
            if system == "Windows":
                # Windows 下转换 WSL 路径到 Windows 路径
                if str(skills_path).startswith("/mnt/"):
                    # /mnt/d/... -> D:\...
                    windows_path = str(skills_path).replace("/mnt/", "")
                    drive = windows_path[0].upper() + ":"
                    windows_path = drive + windows_path[1:].replace("/", "\\")
                    subprocess.run(["explorer", windows_path])
                else:
                    subprocess.run(["explorer", str(skills_path)])
            elif system == "Darwin":  # macOS
                subprocess.run(["open", str(skills_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(skills_path)])
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法打开技能目录: {e}")

    def get_config(self) -> SkillsConfig:
        self._config.enabled_skills = [
            name for name, widget in self._skill_widgets.items()
            if widget.is_enabled()
        ]
        return self._config

    def set_config(self, config: SkillsConfig):
        """设置配置并刷新显示"""
        self._config = config
        
        # 更新现有 widgets 的状态
        for skill_name, widget in self._skill_widgets.items():
            enabled = config.is_skill_enabled(skill_name)
            priority = config.get_skill_priority(skill_name)
            widget.checkbox.setChecked(enabled)
            widget.set_priority(priority)
