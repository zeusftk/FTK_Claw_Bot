# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple
import re
import os


@dataclass
class Skill:
    name: str
    file_path: str
    content: str = ""
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_markdown(cls, file_path: str) -> "Skill":
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Skill file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        name = os.path.splitext(os.path.basename(file_path))[0]
        description = cls._extract_description(content)
        dependencies = cls._extract_dependencies(content)

        stat = os.stat(file_path)
        created_at = datetime.fromtimestamp(stat.st_ctime)
        updated_at = datetime.fromtimestamp(stat.st_mtime)

        return cls(
            name=name,
            file_path=file_path,
            content=content,
            description=description,
            dependencies=dependencies,
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def _extract_description(content: str) -> str:
        # 首先尝试从YAML前端提取描述
        yaml_match = re.search('^---\n.*?description:\s*["\']?(.+?)["\']?\n---', content, re.DOTALL)
        if yaml_match:
            return yaml_match.group(1).strip()
        # 然后尝试从Markdown正文提取描述
        match = re.search('^#\s+.+\n+(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if match:
            desc = match.group(1).strip()
            lines = desc.split('\n')
            return lines[0] if lines else ''
        return ''

    @staticmethod
    def _extract_dependencies(content: str) -> List[str]:
        match = re.search(r"^##\s*依赖\s*\n((?:- .+\n?)+)", content, re.MULTILINE)
        if match:
            deps_text = match.group(1)
            deps = re.findall(r"-\s*(.+)", deps_text)
            return [d.strip() for d in deps if d.strip()]
        return []

    def to_markdown(self) -> str:
        return self.content

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "file_path": self.file_path,
            "content": self.content,
            "description": self.description,
            "dependencies": self.dependencies,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        return cls(
            name=data["name"],
            file_path=data["file_path"],
            content=data.get("content", ""),
            description=data.get("description", ""),
            dependencies=data.get("dependencies", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
        )

    @staticmethod
    def validate(content: str) -> Tuple[bool, List[str]]:
        errors = []
        if not content.strip():
            errors.append("技能内容不能为空")
            return False, errors

        # 检查是否有YAML前端或Markdown标题
        has_yaml_frontmatter = re.search(r"^---\n.*?---", content, re.DOTALL)
        has_markdown_title = re.search(r"^#\s+", content, re.MULTILINE)
        
        if not has_yaml_frontmatter and not has_markdown_title:
            errors.append("技能必须包含标题（# 技能名称）或YAML前端")

        # 对于没有YAML前端的技能，检查是否有描述部分
        if not has_yaml_frontmatter:
            if not re.search(r"^##\s*描述", content, re.MULTILINE | re.IGNORECASE):
                errors.append("技能应包含描述部分（## 描述）")

        return len(errors) == 0, errors

    @staticmethod
    def create_template(name: str) -> str:
        return f"""# {name}

## 描述
请在此处添加技能的详细描述，说明该技能的用途和使用场景。

## 使用说明
1. 步骤一
2. 步骤二
3. 步骤三

## 示例
用户: 请帮我执行某个任务
助手: [执行技能中的步骤]

## 依赖
- 无

## 注意事项
- 请在此处添加注意事项
"""
