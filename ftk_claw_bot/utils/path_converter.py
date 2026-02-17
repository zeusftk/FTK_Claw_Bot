"""Windows ↔ WSL2 path conversion utilities."""

from pathlib import Path, PureWindowsPath
from typing import Optional
import re


class PathConverter:
    """Convert paths between Windows and WSL2 formats."""

    @staticmethod
    def windows_to_wsl(windows_path: str) -> str:
        r"""Convert Windows path to WSL2 path.

        Examples:
            C:\\Users\\name\\workspace → /mnt/c/Users/name/workspace
            D:\\Projects\\code → /mnt/d/Projects/code
            \\\\wsl$\\Ubuntu\\home\\user → /home/user
        """
        if not windows_path:
            return ""

        if windows_path.startswith("\\") or windows_path.startswith("//"):
            match = re.match(r"^[\/]{2}wsl\$[\/]([^\/]+)[\/](.*)$", windows_path)
            if match:
                inner_path = match.group(2).replace("\\", "/")
                return f"/{inner_path}"

        # Use PureWindowsPath to handle Windows paths on any OS
        path = PureWindowsPath(windows_path)

        if path.drive:
            drive = path.drive.lower().rstrip(":")
            rest = path.as_posix()[len(path.drive) :]
            return f"/mnt/{drive}{rest}"

        return path.as_posix()

    @staticmethod
    def wsl_to_windows(wsl_path: str, distro: str = "Ubuntu") -> str:
        r"""Convert WSL2 path to Windows path.

        Examples:
            /mnt/c/Users/name/workspace → C:\\Users\\name\\workspace
            /home/user/projects → \\\\wsl$\\Ubuntu\\home\\user\\projects
        """
        if not wsl_path:
            return ""

        match = re.match(r"^/mnt/([a-zA-Z])/(.*)$", wsl_path)
        if match:
            drive = match.group(1).upper()
            rest = match.group(2).replace("/", "\\")
            return f"{drive}:\\{rest}"

        if wsl_path.startswith("/"):
            path_without_leading = wsl_path[1:].replace("/", "\\")
            return f"\\\\wsl$\\{distro}\\{path_without_leading}"

        return wsl_path

    @staticmethod
    def is_valid_wsl_path(wsl_path: str) -> bool:
        """Check if a path looks like a valid WSL2 path."""
        if not wsl_path:
            return False
        return wsl_path.startswith("/mnt/") or wsl_path.startswith("/")

    @staticmethod
    def normalize_windows_path(path: str) -> str:
        """Normalize Windows path."""
        if not path:
            return ""
        return str(Path(path).resolve())
