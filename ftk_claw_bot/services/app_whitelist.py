# -*- coding: utf-8 -*-
"""
应用白名单管理器

功能：
1. 管理授权应用列表
2. 通过快捷方式 (.lnk) 存储授权应用
3. 支持别名匹配
4. 提供 GUI 操作接口
"""

import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional

from ftk_claw_bot.utils.user_data_dir import user_data


@dataclass
class AppInfo:
    """应用信息"""
    name: str
    path: str
    aliases: List[str] = field(default_factory=list)
    description: str = ""
    icon: str = ""
    added_at: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AppInfo':
        return cls(
            name=data.get("name", ""),
            path=data.get("path", ""),
            aliases=data.get("aliases", []),
            description=data.get("description", ""),
            icon=data.get("icon", ""),
            added_at=data.get("added_at", ""),
        )


class AppWhitelistManager:
    """
    应用白名单管理器
    
    目录结构:
        authorized_apps/
        ├── .whitelist.json      # 白名单配置
        ├── notepad.lnk          # 记事本快捷方式
        ├── chrome.lnk           # Chrome 快捷方式
        └── ...
    """
    
    def __init__(self):
        self._authorized_dir = user_data.authorized_apps
        self._config_file = user_data.whitelist_config_file
        self._apps: Dict[str, AppInfo] = {}
        
        # 确保目录存在
        self._authorized_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[Whitelist] 初始化白名单管理器")
        print(f"[Whitelist] 配置文件: {self._config_file}")
        print(f"[Whitelist] 配置文件存在: {self._config_file.exists()}")
        
        self._load_config()
        print(f"[Whitelist] 已加载 {len(self._apps)} 个授权应用: {list(self._apps.keys())}")
    
    # ========================================
    # 配置管理
    # ========================================
    
    def _load_config(self) -> None:
        """加载白名单配置"""
        if self._config_file.exists():
            try:
                data = json.loads(self._config_file.read_text(encoding="utf-8"))
                version = data.get("version", 1)
                for name, info in data.get("apps", {}).items():
                    self._apps[name] = AppInfo.from_dict(info)
            except Exception as e:
                print(f"[Whitelist] 加载配置失败: {e}")
    
    def _save_config(self) -> None:
        """保存白名单配置"""
        try:
            # 确保目录存在
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "version": 1,
                "apps": {name: info.to_dict() for name, info in self._apps.items()}
            }
            self._config_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"[Whitelist] 配置已保存到: {self._config_file}")
            print(f"[Whitelist] 保存了 {len(self._apps)} 个应用: {list(self._apps.keys())}")
        except Exception as e:
            print(f"[Whitelist] 保存配置失败: {e}")
            import traceback
            traceback.print_exc()
    
    # ========================================
    # 查询方法
    # ========================================
    
    def is_allowed(self, app_name_or_path: str) -> bool:
        """
        检查应用是否在白名单
        
        支持多种匹配方式：
        1. 名称精确匹配
        2. 别名匹配
        3. 路径匹配
        4. 带扩展名的名称匹配（如 notepad.exe -> notepad）
        
        Args:
            app_name_or_path: 应用名称或路径
        
        Returns:
            是否在白名单中
        """
        if not app_name_or_path:
            return False
        
        app_name_lower = app_name_or_path.lower()
        app_path_lower = app_name_or_path.lower()
        
        # 处理带扩展名的情况：notepad.exe -> notepad
        app_name_no_ext = app_name_lower
        if '.' in app_name_no_ext:
            app_name_no_ext = app_name_no_ext.rsplit('.', 1)[0]
        
        # 调试日志
        print(f"[Whitelist] 检查白名单: '{app_name_or_path}'")
        print(f"[Whitelist]   - 小写: '{app_name_lower}'")
        print(f"[Whitelist]   - 去扩展名: '{app_name_no_ext}'")
        print(f"[Whitelist]   - 当前白名单应用: {list(self._apps.keys())}")
        
        # 先检查别名（最宽松的匹配）
        for app in self._apps.values():
            # 检查别名列表中是否包含
            if app_name_lower in [a.lower() for a in app.aliases]:
                print(f"[Whitelist]   ✓ 别名匹配: {app.aliases}")
                return True
            # 检查带扩展名的匹配
            if app_name_no_ext in [a.lower() for a in app.aliases]:
                print(f"[Whitelist]   ✓ 别名匹配(去扩展名): {app.aliases}")
                return True
        
        # 再检查名称和路径
        for name, app in self._apps.items():
            # 名称精确匹配
            if app_name_lower == name.lower():
                print(f"[Whitelist]   ✓ 名称精确匹配: {name}")
                return True
            
            # 名称匹配（去掉扩展名）
            if app_name_no_ext == name.lower():
                print(f"[Whitelist]   ✓ 名称匹配(去扩展名): {name}")
                return True
            
            # 路径匹配
            if app_path_lower == app.path.lower():
                print(f"[Whitelist]   ✓ 路径匹配: {app.path}")
                return True
            
            # 路径匹配（提取文件名）
            if app_name_no_ext and app_name_no_ext in app.path.lower():
                print(f"[Whitelist]   ✓ 路径包含匹配: {app.path}")
                return True
        
        print(f"[Whitelist]   ✗ 未匹配")
        return False
    
    def get_actual_path(self, app_name_or_path: str) -> Optional[str]:
        """
        获取实际执行路径
        
        Args:
            app_name_or_path: 应用名称、别名或路径
        
        Returns:
            实际的可执行文件路径，未找到返回 None
        """
        app_name_or_path = app_name_or_path.strip().lower()
        
        # 直接名称匹配
        for name, app in self._apps.items():
            if app_name_or_path == name.lower():
                return app.path
        
        # 别名匹配
        for app in self._apps.values():
            if app_name_or_path in [a.lower() for a in app.aliases]:
                return app.path
        
        # 路径匹配
        for app in self._apps.values():
            if app_name_or_path == app.path.lower():
                return app.path
        
        return None
    
    def get_app_info(self, name: str) -> Optional[AppInfo]:
        """获取应用信息"""
        return self._apps.get(name)
    
    def list_apps(self) -> List[AppInfo]:
        """列出所有授权应用"""
        return list(self._apps.values())
    
    def get_app_names(self) -> List[str]:
        """获取所有应用名称列表"""
        return list(self._apps.keys())
    
    def get_all_apps(self) -> Dict[str, AppInfo]:
        """获取所有授权应用（字典形式）"""
        return dict(self._apps)
    
    # ========================================
    # 管理方法
    # ========================================
    
    def add_app(
        self,
        name: str,
        path: str,
        aliases: List[str] = None,
        description: str = "",
        create_shortcut: bool = True,
        skip_path_validation: bool = False
    ) -> bool:
        """
        添加应用到白名单
        
        Args:
            name: 应用名称（唯一标识）
            path: 可执行文件路径
            aliases: 别名列表（用于模糊匹配）
            description: 应用描述
            create_shortcut: 是否创建快捷方式
            skip_path_validation: 是否跳过路径验证（用于 WSL 环境添加 Windows 路径）
        
        Returns:
            是否添加成功
        """
        # 验证路径（可选）
        if not skip_path_validation and not os.path.isfile(path):
            print(f"[Whitelist] 路径不存在: {path}")
            return False
        
        # 标准化路径
        abs_path = os.path.abspath(path) if not skip_path_validation else path
        
        # 创建 AppInfo
        from datetime import datetime
        app_info = AppInfo(
            name=name,
            path=abs_path,
            aliases=aliases or [],
            description=description,
            added_at=datetime.now().isoformat()
        )
        
        # 创建快捷方式
        if create_shortcut:
            if not self._create_shortcut(name, abs_path):
                print(f"[Whitelist] 创建快捷方式失败，但继续添加")
        
        # 添加到内存
        self._apps[name] = app_info
        
        # 保存配置
        self._save_config()
        
        print(f"[Whitelist] 已添加应用: {name} -> {abs_path}")
        return True
    
    def remove_app(self, name: str) -> bool:
        """
        从白名单移除应用
        
        Args:
            name: 应用名称
        
        Returns:
            是否移除成功
        """
        if name not in self._apps:
            print(f"[Whitelist] 应用不存在: {name}")
            return False
        
        # 删除快捷方式
        shortcut_path = self._authorized_dir / f"{name}.lnk"
        if shortcut_path.exists():
            try:
                shortcut_path.unlink()
            except Exception as e:
                print(f"[Whitelist] 删除快捷方式失败: {e}")
        
        # 从内存移除
        del self._apps[name]
        
        # 保存配置
        self._save_config()
        
        print(f"[Whitelist] 已移除应用: {name}")
        return True
    
    def update_app(
        self,
        name: str,
        path: str = None,
        aliases: List[str] = None,
        description: str = None
    ) -> bool:
        """
        更新应用信息
        
        Args:
            name: 应用名称
            path: 新路径（可选）
            aliases: 新别名列表（可选）
            description: 新描述（可选）
        
        Returns:
            是否更新成功
        """
        if name not in self._apps:
            return False
        
        app = self._apps[name]
        
        if path is not None:
            if not os.path.isfile(path):
                return False
            app.path = os.path.abspath(path)
            # 更新快捷方式
            self._create_shortcut(name, app.path)
        
        if aliases is not None:
            app.aliases = aliases
        
        if description is not None:
            app.description = description
        
        self._save_config()
        return True
    
    # ========================================
    # 快捷方式管理
    # ========================================
    
    def _create_shortcut(self, name: str, target_path: str) -> bool:
        """
        创建快捷方式到授权目录
        
        使用 Windows Script Host 创建 .lnk 文件
        """
        try:
            import pythoncom
            from win32com.shell import shell, shellcon
        except ImportError:
            # 非 Windows 环境或缺少 pywin32
            print("[Whitelist] 缺少 pywin32，跳过快捷方式创建")
            return False
        
        try:
            shortcut_path = self._authorized_dir / f"{name}.lnk"
            
            pythoncom.CoInitialize()
            
            shortcut = pythoncom.CoCreateInstance(
                shell.CLSID_ShellLink,
                None,
                pythoncom.CLSCTX_INPROC_SERVER,
                shell.IID_IShellLink
            )
            
            shortcut.SetPath(target_path)
            shortcut.SetWorkingDirectory(os.path.dirname(target_path))
            
            # 设置图标（使用可执行文件的图标）
            shortcut.SetIconLocation(target_path, 0)
            
            persist = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
            persist.Save(str(shortcut_path), 0)
            
            return True
        except Exception as e:
            print(f"[Whitelist] 创建快捷方式失败: {e}")
            return False
    
    def _resolve_shortcut(self, lnk_path: Path) -> Optional[str]:
        """
        解析快捷方式获取目标路径
        """
        try:
            import pythoncom
            from win32com.shell import shell
        except ImportError:
            return None
        
        try:
            pythoncom.CoInitialize()
            
            shortcut = pythoncom.CoCreateInstance(
                shell.CLSID_ShellLink,
                None,
                pythoncom.CLSCTX_INPROC_SERVER,
                shell.IID_IShellLink
            )
            
            persist = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
            persist.Load(str(lnk_path))
            
            return shortcut.GetPath(shell.SLGP_SHORTPATH)[0]
        except Exception:
            return None
    
    def scan_shortcuts(self) -> int:
        """
        扫描授权目录中的快捷方式，同步到配置
        
        Returns:
            新增的应用数量
        """
        new_count = 0
        
        for lnk_file in self._authorized_dir.glob("*.lnk"):
            name = lnk_file.stem
            
            if name in self._apps:
                continue
            
            # 解析快捷方式
            target = self._resolve_shortcut(lnk_file)
            if target and os.path.isfile(target):
                from datetime import datetime
                self._apps[name] = AppInfo(
                    name=name,
                    path=target,
                    added_at=datetime.now().isoformat()
                )
                new_count += 1
        
        if new_count > 0:
            self._save_config()
        
        return new_count
    
    # ========================================
    # 导入导出
    # ========================================
    
    def export_config(self, export_path: str) -> bool:
        """导出白名单配置到指定路径"""
        try:
            data = {
                "version": 1,
                "exported_at": __import__('datetime').datetime.now().isoformat(),
                "apps": {name: info.to_dict() for name, info in self._apps.items()}
            }
            Path(export_path).write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return True
        except Exception as e:
            print(f"[Whitelist] 导出失败: {e}")
            return False
    
    def import_config(self, import_path: str, merge: bool = True) -> int:
        """
        导入白名单配置
        
        Args:
            import_path: 配置文件路径
            merge: 是否合并（True）或覆盖（False）
        
        Returns:
            导入的应用数量
        """
        try:
            data = json.loads(Path(import_path).read_text(encoding="utf-8"))
            imported_apps = data.get("apps", {})
            
            if not merge:
                self._apps.clear()
            
            count = 0
            for name, info in imported_apps.items():
                if name not in self._apps:
                    self._apps[name] = AppInfo.from_dict(info)
                    count += 1
            
            self._save_config()
            return count
        except Exception as e:
            print(f"[Whitelist] 导入失败: {e}")
            return 0
    
    # ========================================
    # 统计信息
    # ========================================
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_apps": len(self._apps),
            "config_path": str(self._config_file),
            "shortcuts_dir": str(self._authorized_dir),
            "shortcuts_count": len(list(self._authorized_dir.glob("*.lnk"))),
        }


# 全局单例
whitelist_manager = AppWhitelistManager()
