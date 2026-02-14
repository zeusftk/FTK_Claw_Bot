import os
import re
from pathlib import Path
from typing import Optional, Tuple


class PathUtils:
    @staticmethod
    def windows_to_wsl(windows_path: str) -> str:
        windows_path = windows_path.replace("\\", "/")

        if len(windows_path) >= 2 and windows_path[1] == ":":
            drive = windows_path[0].lower()
            rest = windows_path[2:]
            return f"/mnt/{drive}{rest}"

        return windows_path

    @staticmethod
    def wsl_to_windows(wsl_path: str) -> str:
        if wsl_path.startswith("/mnt/"):
            parts = wsl_path[5:].split("/", 1)
            if len(parts) >= 1:
                drive = parts[0].upper()
                rest = parts[1] if len(parts) > 1 else ""
                return f"{drive}:\\{rest.replace('/', '\\')}"

        return wsl_path

    @staticmethod
    def is_valid_windows_path(path: str) -> bool:
        pattern = r"^[A-Za-z]:\\(?:[^<>:\"/\\|?*\r\n]+\\?)*$"
        return bool(re.match(pattern, path))

    @staticmethod
    def is_valid_wsl_path(path: str) -> bool:
        if not path.startswith("/"):
            return False

        pattern = r"^/(?:mnt/[a-z]/)?(?:[^<>:\"\\|?*\r\n]+/?)*$"
        return bool(re.match(pattern, path))

    @staticmethod
    def ensure_dir(path: str) -> bool:
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    @staticmethod
    def get_app_data_dir() -> str:
        app_data = os.environ.get("APPDATA", "")
        if app_data:
            return os.path.join(app_data, "FTK_Bot")
        return os.path.expanduser("~/.ftk_bot")

    @staticmethod
    def get_default_workspace() -> str:
        return os.path.join(PathUtils.get_app_data_dir(), "workspace")

    @staticmethod
    def get_default_skills_dir() -> str:
        return os.path.join(PathUtils.get_app_data_dir(), "skills")

    @staticmethod
    def normalize_path(path: str) -> str:
        return os.path.normpath(path)

    @staticmethod
    def join_paths(*paths: str) -> str:
        return os.path.join(*paths)

    @staticmethod
    def get_relative_path(path: str, base: str) -> str:
        try:
            return os.path.relpath(path, base)
        except ValueError:
            return path

    @staticmethod
    def file_exists(path: str) -> bool:
        return os.path.isfile(path)

    @staticmethod
    def dir_exists(path: str) -> bool:
        return os.path.isdir(path)

    @staticmethod
    def get_file_size(path: str) -> int:
        try:
            return os.path.getsize(path)
        except Exception:
            return 0

    @staticmethod
    def format_size(size_bytes: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
