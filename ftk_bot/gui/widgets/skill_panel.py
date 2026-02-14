from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QSplitter, QFrame,
    QMessageBox, QFileDialog, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor

from ...core import SkillManager
from ...models import Skill


class SkillPanel(QWidget):
    skill_selected = pyqtSignal(str)

    def __init__(self, skill_manager: Optional[SkillManager] = None, parent=None):
        super().__init__(parent)
        self._skill_manager = skill_manager
        self._current_skill: Optional[Skill] = None

        self._init_ui()
        if skill_manager:
            self._load_skills()

    def set_skill_manager(self, skill_manager: SkillManager):
        self._skill_manager = skill_manager
        self._load_skills()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        left_panel = QFrame()
        left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(left_panel)

        header_layout = QHBoxLayout()
        title = QLabel("技能列表")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        header_layout.addWidget(title)
        header_layout.addStretch()

        new_btn = QPushButton("新建")
        new_btn.clicked.connect(self._new_skill)
        import_btn = QPushButton("导入")
        import_btn.clicked.connect(self._import_skill)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._load_skills)
        header_layout.addWidget(new_btn)
        header_layout.addWidget(import_btn)
        header_layout.addWidget(refresh_btn)

        left_layout.addLayout(header_layout)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索技能...")
        self.search_edit.textChanged.connect(self._search_skills)
        left_layout.addWidget(self.search_edit)

        self.skill_list = QListWidget()
        self.skill_list.currentItemChanged.connect(self._on_skill_selected)
        left_layout.addWidget(self.skill_list)

        layout.addWidget(left_panel)

        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)

        detail_header = QHBoxLayout()
        self.skill_title = QLabel("技能详情")
        self.skill_title.setObjectName("skillTitle")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.skill_title.setFont(font)
        detail_header.addWidget(self.skill_title)
        detail_header.addStretch()

        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self._toggle_edit_mode)
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save_skill)
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._export_skill)
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self._delete_skill)
        detail_header.addWidget(edit_btn)
        detail_header.addWidget(save_btn)
        detail_header.addWidget(export_btn)
        detail_header.addWidget(delete_btn)

        right_layout.addLayout(detail_header)

        self.content_edit = QTextEdit()
        self.content_edit.setReadOnly(True)
        self.content_edit.setAcceptRichText(False)
        self.content_edit.setFont(QFont("Consolas", 11))
        right_layout.addWidget(self.content_edit, 1)

        meta_group = QFrame()
        meta_layout = QHBoxLayout(meta_group)
        self.created_label = QLabel("创建时间: --")
        self.updated_label = QLabel("更新时间: --")
        self.deps_label = QLabel("依赖: --")
        meta_layout.addWidget(self.created_label)
        meta_layout.addWidget(self.updated_label)
        meta_layout.addWidget(self.deps_label)
        right_layout.addWidget(meta_group)

        layout.addWidget(right_panel, 1)

        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet("""
            QLabel#skillTitle {
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
            QLineEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #5c5c5c;
                border-radius: 4px;
                padding: 8px 10px;
            }
            QLineEdit:focus {
                border-color: #007acc;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #0e639c;
                color: #ffffff;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #0d5a8a;
            }
        """)

    def _load_skills(self):
        if not self._skill_manager:
            return

        self.skill_list.clear()
        skills = self._skill_manager.list_skills()

        for skill in skills:
            item = QListWidgetItem(skill.name)
            item.setData(Qt.ItemDataRole.UserRole, skill.name)
            self.skill_list.addItem(item)

        if skills:
            self.skill_list.setCurrentRow(0)

    def _search_skills(self, keyword: str):
        if not self._skill_manager:
            return

        self.skill_list.clear()

        if keyword:
            skills = self._skill_manager.search_skills(keyword)
        else:
            skills = self._skill_manager.list_skills()

        for skill in skills:
            item = QListWidgetItem(skill.name)
            item.setData(Qt.ItemDataRole.UserRole, skill.name)
            self.skill_list.addItem(item)

    def _on_skill_selected(self, current, previous):
        if not current or not self._skill_manager:
            return

        name = current.data(Qt.ItemDataRole.UserRole)
        skill = self._skill_manager.get_skill(name)

        if skill:
            self._current_skill = skill
            self._display_skill(skill)

    def _display_skill(self, skill: Skill):
        self.skill_title.setText(f"技能详情: {skill.name}")
        self.content_edit.setPlainText(skill.content)

        if skill.created_at:
            self.created_label.setText(f"创建时间: {skill.created_at.strftime('%Y-%m-%d %H:%M')}")
        else:
            self.created_label.setText("创建时间: --")

        if skill.updated_at:
            self.updated_label.setText(f"更新时间: {skill.updated_at.strftime('%Y-%m-%d %H:%M')}")
        else:
            self.updated_label.setText("更新时间: --")

        if skill.dependencies:
            self.deps_label.setText(f"依赖: {', '.join(skill.dependencies)}")
        else:
            self.deps_label.setText("依赖: 无")

    def _toggle_edit_mode(self):
        self.content_edit.setReadOnly(not self.content_edit.isReadOnly())
        if not self.content_edit.isReadOnly():
            self.content_edit.setFocus()

    def _new_skill(self):
        if not self._skill_manager:
            QMessageBox.warning(self, "错误", "请先配置技能目录")
            return

        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "新建技能", "技能名称:")
        if ok and name:
            try:
                skill = self._skill_manager.create_skill(name)
                self._load_skills()
                self.skill_selected.emit(name)
                QMessageBox.information(self, "成功", f"已创建技能: {name}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建失败: {e}")

    def _import_skill(self):
        if not self._skill_manager:
            QMessageBox.warning(self, "错误", "请先配置技能目录")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入技能", "", "Markdown Files (*.md)"
        )
        if file_path:
            try:
                skill = self._skill_manager.import_skill(file_path)
                self._load_skills()
                QMessageBox.information(self, "成功", f"已导入技能: {skill.name}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导入失败: {e}")

    def _save_skill(self):
        if not self._current_skill or not self._skill_manager:
            return

        content = self.content_edit.toPlainText()
        valid, errors = self._skill_manager.validate_skill(content)

        if not valid:
            QMessageBox.warning(self, "验证失败", "\n".join(errors))
            return

        try:
            skill = self._skill_manager.update_skill(self._current_skill.name, content)
            self._current_skill = skill
            self._display_skill(skill)
            self.content_edit.setReadOnly(True)
            QMessageBox.information(self, "成功", "技能已保存")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {e}")

    def _export_skill(self):
        if not self._current_skill:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出技能",
            f"{self._current_skill.name}.md",
            "Markdown Files (*.md)"
        )
        if file_path:
            if self._skill_manager.export_skill(self._current_skill.name, file_path):
                QMessageBox.information(self, "成功", f"已导出到: {file_path}")
            else:
                QMessageBox.warning(self, "错误", "导出失败")

    def _delete_skill(self):
        if not self._current_skill or not self._skill_manager:
            return

        name = self._current_skill.name
        reply = QMessageBox.question(
            self, "确认", f"确定要删除技能 '{name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self._skill_manager.delete_skill(name):
                self._current_skill = None
                self._load_skills()
                QMessageBox.information(self, "成功", f"已删除技能: {name}")
