import re
from typing import Tuple, Optional


class Validators:
    @staticmethod
    def validate_config_name(name: str) -> Tuple[bool, Optional[str]]:
        if not name or not name.strip():
            return False, "配置名称不能为空"

        if len(name) > 50:
            return False, "配置名称不能超过50个字符"

        if not re.match(r"^[\w\-_\u4e00-\u9fa5]+$", name):
            return False, "配置名称只能包含字母、数字、下划线、连字符和中文"

        return True, None

    @staticmethod
    def validate_apiKey(apiKey: str) -> Tuple[bool, Optional[str]]:
        if not apiKey or not apiKey.strip():
            return False, "API Key 不能为空"

        if len(apiKey) < 10:
            return False, "API Key 格式不正确"

        return True, None

    @staticmethod
    def validate_workspace_path(path: str) -> Tuple[bool, Optional[str]]:
        if not path or not path.strip():
            return True, None

        import os
        if not os.path.isabs(path):
            return False, "工作空间路径必须是绝对路径"

        return True, None

    @staticmethod
    def validate_skill_name(name: str) -> Tuple[bool, Optional[str]]:
        if not name or not name.strip():
            return False, "技能名称不能为空"

        if len(name) > 100:
            return False, "技能名称不能超过100个字符"

        if not re.match(r"^[\w\-_\u4e00-\u9fa5\s]+$", name):
            return False, "技能名称包含非法字符"

        return True, None

    @staticmethod
    def validate_model_name(model: str) -> Tuple[bool, Optional[str]]:
        if not model or not model.strip():
            return False, "模型名称不能为空"

        return True, None

    @staticmethod
    def validate_port(port: int) -> Tuple[bool, Optional[str]]:
        if port < 1 or port > 65535:
            return False, "端口号必须在 1-65535 范围内"

        if port < 1024:
            return False, "端口号建议使用 1024 以上的值"

        return True, None

    @staticmethod
    def validate_url(url: str) -> Tuple[bool, Optional[str]]:
        if not url or not url.strip():
            return False, "URL 不能为空"

        pattern = re.compile(
            r"^https?://"
            r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"
            r"[A-Z]{2,6}"
            r"(?::\d+)?(?:/\S*)?$",
            re.IGNORECASE
        )

        if not pattern.match(url):
            return False, "URL 格式不正确"

        return True, None

    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        if not email or not email.strip():
            return True, None

        pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

        if not pattern.match(email):
            return False, "邮箱格式不正确"

        return True, None
