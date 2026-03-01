# -*- coding: utf-8 -*-
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont

from ...models import Skill
from ...core import SkillManager


class SkillEditorDialog(QDialog):
    skill_saved = pyqtSignal(str)

    def __init__(self, skill_manager: SkillManager, skill: Optional[Skill] = None, parent=None):
        super().__init__(parent)
        self._skill_manager = skill_manager
        self._skill = skill
        self._is_new = skill is None

        self.setWindowTitle("编辑技能" if skill else "新建技能")
        self.setMinimumSize(800, 600)

        self._init_ui()
        if skill:
            self._load_skill(skill)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 名称输入
        name_layout = QHBoxLayout()
        name_label = QLabel("技能名称:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入技能名称...")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit, 1)
        layout.addLayout(name_layout)

        # 内容编辑
        content_label = QLabel("技能内容 (Markdown格式):")
        layout.addWidget(content_label)

        self.content_edit = QTextEdit()
        self.content_edit.setFont(QFont("Consolas", 11))
        layout.addWidget(self.content_edit, 1)

        # 预览区域
        preview_label = QLabel("预览:")
        layout.addWidget(preview_label)

        self.preview_edit = QTextEdit()
        self.preview_edit.setReadOnly(True)
        layout.addWidget(self.preview_edit)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        preview_btn = QPushButton("预览")
        preview_btn.clicked.connect(self._update_preview)

        template_btn = QPushButton("加载模板")
        template_btn.clicked.connect(self._load_template)

        validate_btn = QPushButton("验证")
        validate_btn.clicked.connect(self._validate_skill)

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save_skill)
        save_btn.setDefault(True)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(preview_btn)
        btn_layout.addWidget(template_btn)
        btn_layout.addWidget(validate_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

        self._apply_styles()

    def _apply_styles(self):
        # 样式已在全局样式表中定义
        pass

    def _load_skill(self, skill: Skill):
        self.name_edit.setText(skill.name)
        self.name_edit.setReadOnly(True)
        self.content_edit.setPlainText(skill.content)
        self._update_preview()

    def _load_template(self):
        name = self.name_edit.text() or "新技能"
        template = Skill.create_template(name)
        self.content_edit.setPlainText(template)

    def _update_preview(self):
        content = self.content_edit.toPlainText()
        # 简单的Markdown预览（可以扩展为完整的Markdown渲染）
        preview = content.replace("# ", "📌 ").replace("## ", "▶ ")
        self.preview_edit.setPlainText(preview)

    def _validate_skill(self):
        content = self.content_edit.toPlainText()
        valid, errors = self._skill_manager.validate_skill(content)

        if valid:
            QMessageBox.information(self, "验证成功", "技能格式正确！")
        else:
            QMessageBox.warning(self, "验证失败", "\n".join(errors))

    def _save_skill(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "请输入技能名称")
            return

        content = self.content_edit.toPlainText()
        valid, errors = self._skill_manager.validate_skill(content)

        if not valid:
            QMessageBox.warning(self, "验证失败", "\n".join(errors))
            return

        try:
            if self._is_new:
                skill = self._skill_manager.create_skill(name, content)
            else:
                skill = self._skill_manager.update_skill(self._skill.name, content)

            self.skill_saved.emit(skill.name)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", str(e))

    def get_skill_name(self) -> str:
        return self.name_edit.text().strip()
