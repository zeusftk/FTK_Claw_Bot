# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class SkillInfo:
    name: str
    description: str = ""
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_path: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "metadata": self.metadata,
            "file_path": self.file_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillInfo":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
            file_path=data.get("file_path", ""),
        )


# 默认优先级
DEFAULT_PRIORITY = 1


@dataclass
class SkillsConfig:
    enabled_skills: List[str] = field(default_factory=list)
    custom_skills_dir: str = ""
    skill_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    available_skills: List[SkillInfo] = field(default_factory=list)
    # 技能优先级：name -> priority，值越大优先级越高，默认为1
    skill_priorities: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "enabled_skills": self.enabled_skills,
            "custom_skills_dir": self.custom_skills_dir,
            "skill_settings": self.skill_settings,
            "available_skills": [s.to_dict() for s in self.available_skills],
            "skill_priorities": self.skill_priorities,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillsConfig":
        available_skills_data = data.get("available_skills", [])
        return cls(
            enabled_skills=data.get("enabled_skills", []),
            custom_skills_dir=data.get("custom_skills_dir", ""),
            skill_settings=data.get("skill_settings", {}),
            available_skills=[SkillInfo.from_dict(s) for s in available_skills_data],
            skill_priorities=data.get("skill_priorities", {}),
        )

    def is_skill_enabled(self, skill_name: str) -> bool:
        if not self.enabled_skills:
            return True
        return skill_name in self.enabled_skills

    def enable_skill(self, skill_name: str) -> None:
        if skill_name not in self.enabled_skills:
            self.enabled_skills.append(skill_name)

    def disable_skill(self, skill_name: str) -> None:
        if skill_name in self.enabled_skills:
            self.enabled_skills.remove(skill_name)

    def get_skill_setting(self, skill_name: str, key: str, default: Any = None) -> Any:
        skill_settings = self.skill_settings.get(skill_name, {})
        return skill_settings.get(key, default)

    def set_skill_setting(self, skill_name: str, key: str, value: Any) -> None:
        if skill_name not in self.skill_settings:
            self.skill_settings[skill_name] = {}
        self.skill_settings[skill_name][key] = value

    def get_skill_priority(self, skill_name: str) -> int:
        """获取技能优先级，默认为1"""
        return self.skill_priorities.get(skill_name, DEFAULT_PRIORITY)

    def set_skill_priority(self, skill_name: str, priority: int) -> None:
        """设置技能优先级"""
        if priority == DEFAULT_PRIORITY:
            # 默认优先级不需要存储
            self.skill_priorities.pop(skill_name, None)
        else:
            self.skill_priorities[skill_name] = priority

    def get_skills_sorted_by_priority(self) -> List[str]:
        """获取按优先级排序的启用的技能列表（高优先级在前）"""
        enabled = list(self.enabled_skills) if self.enabled_skills else []
        # 按优先级降序排序
        enabled.sort(key=lambda s: self.get_skill_priority(s), reverse=True)
        return enabled


BUILTIN_SKILLS = {
    "github": {
        "name": "github",
        "description": "GitHub CLI 交互，管理仓库、Issues、PRs",
        "icon": "🐙",
        "requires": ["gh"],
    },
    "weather": {
        "name": "weather",
        "description": "天气查询 (无需 API Key)",
        "icon": "🌤️",
        "requires": ["curl"],
    },
    "summarize": {
        "name": "summarize",
        "description": "URL/文件/视频摘要",
        "icon": "📝",
        "requires": [],
    },
    "tmux": {
        "name": "tmux",
        "description": "tmux 会话远程控制",
        "icon": "🖥️",
        "requires": ["tmux"],
    },
    "cron": {
        "name": "cron",
        "description": "定时任务管理",
        "icon": "⏰",
        "requires": [],
    },
    "memory": {
        "name": "memory",
        "description": "记忆功能",
        "icon": "🧠",
        "requires": [],
    },
    "skill-creator": {
        "name": "skill-creator",
        "description": "创建新技能",
        "icon": "✨",
        "requires": [],
    },
    "windows-gui": {
        "name": "windows-gui",
        "description": "Windows GUI 自动化控制",
        "icon": "🪟",
        "requires": [],
    },
    "clawhub": {
        "name": "clawhub",
        "description": "ClawHub 技能市场集成",
        "icon": "🌐",
        "requires": [],
    },
}


def get_builtin_skill_info(skill_name: str) -> Optional[Dict[str, Any]]:
    return BUILTIN_SKILLS.get(skill_name)


def get_all_builtin_skills() -> List[Dict[str, Any]]:
    return list(BUILTIN_SKILLS.values())
