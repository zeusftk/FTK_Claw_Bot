import os
import shutil
from typing import List, Optional, Tuple
from datetime import datetime

from ..models import Skill


class SkillManager:
    def __init__(self, skills_dir: str):
        self._skills_dir = skills_dir
        self._skills: dict[str, Skill] = {}
        self._ensure_dir()

    def _ensure_dir(self):
        if self._skills_dir and not os.path.exists(self._skills_dir):
            os.makedirs(self._skills_dir, exist_ok=True)

    def list_skills(self) -> List[Skill]:
        if not os.path.exists(self._skills_dir):
            return []

        skills = []
        for filename in os.listdir(self._skills_dir):
            if filename.endswith(".md"):
                file_path = os.path.join(self._skills_dir, filename)
                try:
                    skill = Skill.from_markdown(file_path)
                    skills.append(skill)
                    self._skills[skill.name] = skill
                except Exception:
                    continue

        return sorted(skills, key=lambda s: s.name)

    def get_skill(self, name: str) -> Optional[Skill]:
        if name in self._skills:
            return self._skills[name]

        file_path = os.path.join(self._skills_dir, f"{name}.md")
        if os.path.exists(file_path):
            try:
                skill = Skill.from_markdown(file_path)
                self._skills[name] = skill
                return skill
            except Exception:
                return None
        return None

    def create_skill(self, name: str, content: Optional[str] = None) -> Skill:
        if not content:
            content = Skill.create_template(name)

        valid, errors = Skill.validate(content)
        if not valid:
            raise ValueError(f"Invalid skill content: {', '.join(errors)}")

        file_path = os.path.join(self._skills_dir, f"{name}.md")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        skill = Skill.from_markdown(file_path)
        self._skills[name] = skill
        return skill

    def update_skill(self, name: str, content: str) -> Skill:
        valid, errors = Skill.validate(content)
        if not valid:
            raise ValueError(f"Invalid skill content: {', '.join(errors)}")

        skill = self.get_skill(name)
        if not skill:
            raise FileNotFoundError(f"Skill not found: {name}")

        with open(skill.file_path, "w", encoding="utf-8") as f:
            f.write(content)

        updated_skill = Skill.from_markdown(skill.file_path)
        self._skills[name] = updated_skill
        return updated_skill

    def delete_skill(self, name: str) -> bool:
        skill = self.get_skill(name)
        if not skill:
            return False

        try:
            os.remove(skill.file_path)
            if name in self._skills:
                del self._skills[name]
            return True
        except Exception:
            return False

    def import_skill(self, source_path: str, new_name: Optional[str] = None) -> Skill:
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file not found: {source_path}")

        with open(source_path, "r", encoding="utf-8") as f:
            content = f.read()

        valid, errors = Skill.validate(content)
        if not valid:
            raise ValueError(f"Invalid skill content: {', '.join(errors)}")

        name = new_name or os.path.splitext(os.path.basename(source_path))[0]
        dest_path = os.path.join(self._skills_dir, f"{name}.md")

        shutil.copy2(source_path, dest_path)

        skill = Skill.from_markdown(dest_path)
        self._skills[name] = skill
        return skill

    def export_skill(self, name: str, export_path: str) -> bool:
        skill = self.get_skill(name)
        if not skill:
            return False

        try:
            export_dir = os.path.dirname(export_path)
            if export_dir and not os.path.exists(export_dir):
                os.makedirs(export_dir, exist_ok=True)

            shutil.copy2(skill.file_path, export_path)
            return True
        except Exception:
            return False

    def validate_skill(self, content: str) -> Tuple[bool, List[str]]:
        return Skill.validate(content)

    def search_skills(self, keyword: str) -> List[Skill]:
        keyword = keyword.lower()
        results = []

        for skill in self.list_skills():
            if (keyword in skill.name.lower() or
                keyword in skill.description.lower() or
                keyword in skill.content.lower()):
                results.append(skill)

        return results

    def rename_skill(self, old_name: str, new_name: str) -> Skill:
        skill = self.get_skill(old_name)
        if not skill:
            raise FileNotFoundError(f"Skill not found: {old_name}")

        new_path = os.path.join(self._skills_dir, f"{new_name}.md")

        shutil.move(skill.file_path, new_path)

        if old_name in self._skills:
            del self._skills[old_name]

        new_skill = Skill.from_markdown(new_path)
        self._skills[new_name] = new_skill
        return new_skill

    def get_skills_count(self) -> int:
        return len(self.list_skills())

    def set_skills_dir(self, skills_dir: str):
        self._skills_dir = skills_dir
        self._skills.clear()
        self._ensure_dir()
