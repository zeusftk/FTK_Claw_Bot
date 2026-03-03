# -*- coding: utf-8 -*-
"""
统一用户数据目录管理

所有运行时生成的文件统一存放在 user_data/ 目录下，便于：
1. 打包为 exe 后数据文件与程序分离
2. 方便备份和迁移
3. 清晰的文件组织结构
"""

import os
import sys
from pathlib import Path
from typing import Optional


class UserDataDir:
    """统一的用户数据目录管理（单例模式）"""
    
    _instance: Optional['UserDataDir'] = None
    _base_dir: Optional[Path] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, custom_path: str = None) -> Path:
        """
        初始化数据目录
        
        Args:
            custom_path: 自定义路径（用于测试或特殊配置）
        
        Returns:
            数据目录的 Path 对象
        """
        if self._initialized and not custom_path:
            return self._base_dir
        
        if custom_path:
            self._base_dir = Path(custom_path)
        elif getattr(sys, 'frozen', False):
            self._base_dir = Path(sys.executable).parent / "user_data"
        elif sys.argv and sys.argv[0]:
            exe_path = Path(sys.argv[0])
            if exe_path.exists() and exe_path.suffix.lower() == '.exe':
                self._base_dir = exe_path.parent / "user_data"
            else:
                self._base_dir = Path(__file__).parent.parent.parent / "user_data"
        else:
            self._base_dir = Path(__file__).parent.parent.parent / "user_data"
        
        # 先标记为已初始化，防止 _ensure_dirs 中的属性访问导致递归
        self._initialized = True
        
        # 确保目录存在
        self._ensure_dirs()
        
        return self._base_dir
    
    @property
    def base(self) -> Path:
        """获取数据目录根路径"""
        if self._base_dir is None or not self._initialized:
            self.initialize()
        return self._base_dir
    
    # ========================================
    # 一级子目录
    # ========================================
    
    @property
    def config(self) -> Path:
        """配置文件目录"""
        return self.base / "config"
    
    @property
    def logs(self) -> Path:
        """日志文件目录"""
        return self.base / "logs"
    
    @property
    def web(self) -> Path:
        """Web 自动化相关目录"""
        return self.base / "web"
    
    @property
    def authorized_apps(self) -> Path:
        """授权应用目录（白名单）"""
        return self.base / "authorized_apps"
    
    @property
    def skills(self) -> Path:
        """技能目录"""
        return self.base / "skills"
    
    @property
    def workspace(self) -> Path:
        """工作空间目录"""
        return self.base / "workspace"
    
    # ========================================
    # 二级子目录
    # ========================================
    
    @property
    def clawbot_configs(self) -> Path:
        """Clawbot 实例配置目录"""
        return self.config / "clawbot_configs"
    
    @property
    def crash_logs(self) -> Path:
        """崩溃日志目录"""
        return self.logs / "crash"
    
    @property
    def web_sessions(self) -> Path:
        """浏览器会话目录"""
        return self.web / "sessions"
    
    @property
    def web_cookies(self) -> Path:
        """Cookie 目录"""
        return self.web / "cookies"
    
    @property
    def web_cookies_domain(self) -> Path:
        """按域名存储的 Cookie 目录"""
        return self.web_cookies / "domain"
    
    # ========================================
    # 配置文件路径
    # ========================================
    
    @property
    def main_config_file(self) -> Path:
        """主配置文件路径"""
        return self.config / "main_config.json"
    
    @property
    def whitelist_config_file(self) -> Path:
        """白名单配置文件路径"""
        return self.authorized_apps / ".whitelist.json"
    
    # ========================================
    # 工具方法
    # ========================================
    
    def _ensure_dirs(self) -> None:
        """确保所有必要目录存在"""
        dirs = [
            # 一级目录
            self.config,
            self.logs,
            self.web,
            self.authorized_apps,
            self.skills,
            self.workspace,
            # 二级目录
            self.clawbot_configs,
            self.crash_logs,
            self.web_sessions,
            self.web_cookies,
            self.web_cookies_domain,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    def get_relative_path(self, path: Path | str) -> str:
        """获取相对于 base 目录的相对路径"""
        path = Path(path)
        try:
            return str(path.relative_to(self.base))
        except ValueError:
            return str(path)
    
    def clear_all(self) -> bool:
        """
        清空所有用户数据（谨慎使用！）
        
        Returns:
            是否成功
        """
        import shutil
        try:
            if self._base_dir and self._base_dir.exists():
                shutil.rmtree(self._base_dir)
            self._initialized = False
            return True
        except Exception:
            return False
    
    def get_storage_info(self) -> dict:
        """获取存储信息"""
        def get_dir_size(path: Path) -> int:
            total = 0
            if path.exists():
                for entry in path.rglob("*"):
                    if entry.is_file():
                        total += entry.stat().st_size
            return total
        
        return {
            "base_path": str(self.base),
            "config_size": get_dir_size(self.config),
            "logs_size": get_dir_size(self.logs),
            "web_size": get_dir_size(self.web),
            "authorized_apps_size": get_dir_size(self.authorized_apps),
            "skills_size": get_dir_size(self.skills),
            "workspace_size": get_dir_size(self.workspace),
        }


# 全局单例实例
user_data = UserDataDir()
