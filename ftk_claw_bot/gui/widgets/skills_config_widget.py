from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QLineEdit, QFrame, QScrollArea, QFileDialog,
    QGroupBox, QMessageBox, QSplitter, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ...models import SkillsConfig, BUILTIN_SKILLS, get_all_builtin_skills


class SkillItemWidget(QFrame):
    toggled = pyqtSignal(str, bool)
    selected = pyqtSignal(str)

    def __init__(self, skill_name: str, skill_info: dict, enabled: bool = True, parent=None):
        super().__init__(parent)
        self._skill_name = skill_name
        self._skill_info = skill_info
        self._enabled = enabled
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

        name_label = QLabel(self._skill_info.get("name", self._skill_name))
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        info_layout.addWidget(name_label)

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


class SkillDetailWidget(QFrame):
    config_changed = pyqtSignal()

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

    def set_skill(self, skill_name: str, skill_info: dict):
        self._current_skill_name = skill_name
        self._skill_info = skill_info

        self.icon_label.setText(skill_info.get("icon", "📄"))
        self.name_label.setText(skill_info.get("name", skill_name))
        self.desc_label.setText(skill_info.get("description", ""))

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


class SkillsConfigWidget(QWidget):
    config_changed = pyqtSignal()

    def __init__(self, config: SkillsConfig = None, parent=None):
        super().__init__(parent)
        self._config = config or SkillsConfig()
        self._skill_widgets: dict[str, SkillItemWidget] = {}
        self._current_selected_skill: Optional[str] = None
        self._init_ui()
        self._load_skills()

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

        enable_all_btn = QPushButton("全部启用")
        enable_all_btn.setObjectName("smallButton")
        enable_all_btn.clicked.connect(self._enable_all)

        disable_all_btn = QPushButton("全部禁用")
        disable_all_btn.setObjectName("smallButton")
        disable_all_btn.clicked.connect(self._disable_all)

        search_row.addWidget(enable_all_btn)
        search_row.addWidget(disable_all_btn)
        layout.addLayout(search_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QFrame()
        left_panel.setObjectName("skillsListPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        builtin_label = QLabel("内置技能")
        builtin_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #58a6ff;")
        left_layout.addWidget(builtin_label)

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
        right_layout.addWidget(self._detail_widget)

        splitter.addWidget(right_panel)
        splitter.setSizes([400, 300])

        layout.addWidget(splitter, 1)

        custom_group = QGroupBox("自定义技能")
        custom_layout = QVBoxLayout(custom_group)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)

        dir_label = QLabel("技能目录:")
        dir_label.setFixedWidth(80)
        dir_row.addWidget(dir_label)

        self.custom_dir_edit = QLineEdit()
        self.custom_dir_edit.setText(self._config.custom_skills_dir)
        self.custom_dir_edit.setPlaceholderText("自定义技能目录路径")
        self.custom_dir_edit.textChanged.connect(self._on_config_changed)
        dir_row.addWidget(self.custom_dir_edit)

        browse_btn = QPushButton("浏览")
        browse_btn.setObjectName("smallButton")
        browse_btn.clicked.connect(self._browse_custom_dir)
        dir_row.addWidget(browse_btn)

        custom_layout.addLayout(dir_row)
        layout.addWidget(custom_group)

    def _load_skills(self):
        for skill_info in get_all_builtin_skills():
            skill_name = skill_info.get("name", "")
            enabled = self._config.is_skill_enabled(skill_name)

            widget = SkillItemWidget(skill_name, skill_info, enabled)
            widget.toggled.connect(self._on_skill_toggled)
            widget.selected.connect(self._on_skill_selected)

            self._skill_widgets[skill_name] = widget
            self.skills_layout.addWidget(widget)

        self.skills_layout.addStretch()

    def _on_skill_selected(self, skill_name: str):
        if self._current_selected_skill and self._current_selected_skill in self._skill_widgets:
            self._skill_widgets[self._current_selected_skill].set_selected(False)

        self._current_selected_skill = skill_name

        if skill_name in self._skill_widgets:
            self._skill_widgets[skill_name].set_selected(True)
            skill_info = BUILTIN_SKILLS.get(skill_name, {})
            self._detail_widget.set_skill(skill_name, skill_info)

    def _filter_skills(self, keyword: str):
        keyword = keyword.lower().strip()
        for skill_name, widget in self._skill_widgets.items():
            skill_info = BUILTIN_SKILLS.get(skill_name, {})
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

    def _on_config_changed(self):
        self._config.custom_skills_dir = self.custom_dir_edit.text()
        self.config_changed.emit()

    def _enable_all(self):
        for widget in self._skill_widgets.values():
            widget.checkbox.setChecked(True)

    def _disable_all(self):
        for widget in self._skill_widgets.values():
            widget.checkbox.setChecked(False)

    def _browse_custom_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择自定义技能目录")
        if folder:
            self.custom_dir_edit.setText(folder)

    def get_config(self) -> SkillsConfig:
        self._config.enabled_skills = [
            name for name, widget in self._skill_widgets.items()
            if widget.is_enabled()
        ]
        self._config.custom_skills_dir = self.custom_dir_edit.text()
        return self._config

    def set_config(self, config: SkillsConfig):
        self._config = config
        self.custom_dir_edit.setText(config.custom_skills_dir)

        for skill_name, widget in self._skill_widgets.items():
            enabled = config.is_skill_enabled(skill_name)
            widget.checkbox.setChecked(enabled)
