# -*- coding: utf-8 -*-
import os
from typing import Dict, Any, Tuple, List, Optional, Callable

from loguru import logger

from .service_registry import (
    ServiceInfo, ServiceStatus, register_service
)


class ClawbotUpgrader:
    """Clawbot 升级服务"""
    
    def __init__(self):
        self.id = "clawbot_upgrader"
        self.name = "Clawbot 升级"
        self.description = "批量升级 WSL 中的 clawbot"
        self._wsl_manager = None
        self._status = ServiceStatus.STOPPED
    
    def set_wsl_manager(self, wsl_manager):
        self._wsl_manager = wsl_manager
        logger.info("ClawbotUpgrader: WSL 管理器已设置")
    
    def start(self) -> bool:
        self._status = ServiceStatus.RUNNING
        return True
    
    def stop(self) -> bool:
        self._status = ServiceStatus.STOPPED
        return True
    
    def get_status(self) -> ServiceInfo:
        return ServiceInfo(
            id=self.id,
            name=self.name,
            description=self.description,
            status=self._status
        )
    
    def get_config(self) -> Dict[str, Any]:
        return {}
    
    def set_config(self, config: Dict[str, Any]) -> bool:
        return True
    
    def upgrade_all(
        self,
        whl_path: str,
        distro_names: Optional[List[str]] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Tuple[bool, str]]:
        if not self._wsl_manager:
            return {"error": (False, "WSL 管理器未设置")}
        
        if not os.path.exists(whl_path):
            return {"error": (False, f"Wheel 文件不存在: {whl_path}")}
        
        if distro_names is None:
            distros = self._wsl_manager.list_distros()
            distro_names = [d.name for d in distros if d.is_running]
        
        if not distro_names:
            return {"error": (False, "没有在线的 WSL 分发")}
        
        results = {}
        total = len(distro_names)
        whl_name = os.path.basename(whl_path)
        whl_dir = os.path.dirname(whl_path).replace("\\", "/")
        
        logger.info(f"开始批量升级 clawbot，共 {total} 个分发")
        
        for i, distro_name in enumerate(distro_names):
            if progress_callback:
                progress_callback(distro_name, i + 1, total, "upgrading")
            
            success, msg = self._upgrade_one(distro_name, whl_path, whl_name, whl_dir)
            results[distro_name] = (success, msg)
            
            if progress_callback:
                progress_callback(distro_name, i + 1, total, "success" if success else "failed")
        
        success_count = sum(1 for s, _ in results.values() if s)
        logger.info(f"批量升级完成: {success_count}/{total} 成功")
        
        return results
    
    def _upgrade_one(
        self, 
        distro_name: str, 
        whl_path: str,
        whl_name: str,
        whl_dir: str
    ) -> Tuple[bool, str]:
        logger.info(f"[{distro_name}] 开始升级 clawbot")
        
        r = self._wsl_manager.execute_command(distro_name, f"wslpath '{whl_dir}'")
        if not r.success:
            logger.error(f"[{distro_name}] 路径转换失败: {r.stderr}")
            return False, f"路径转换失败: {r.stderr}"
        
        wsl_dir = r.stdout.strip()
        wsl_whl_path = f"{wsl_dir}/{whl_name}"
        
        r = self._wsl_manager.execute_command(
            distro_name, f"cp '{wsl_whl_path}' /tmp/{whl_name}"
        )
        if not r.success:
            logger.error(f"[{distro_name}] 复制失败: {r.stderr}")
            return False, f"复制失败: {r.stderr}"
        
        logger.info(f"[{distro_name}] 安装 wheel 文件...")
        r = self._wsl_manager.execute_command(
            distro_name, f"pip install --upgrade /tmp/{whl_name}", timeout=300
        )
        if not r.success:
            logger.error(f"[{distro_name}] 安装失败: {r.stderr}")
            return False, f"安装失败: {r.stderr}"
        
        self._wsl_manager.execute_command(distro_name, f"rm -f /tmp/{whl_name}")
        
        logger.info(f"[{distro_name}] 重启 clawbot 服务...")
        r = self._wsl_manager.execute_command(
            distro_name, "sudo systemctl restart clawbot", timeout=60
        )
        if not r.success:
            logger.warning(f"[{distro_name}] systemctl 重启失败，尝试直接启动")
            self._wsl_manager.execute_command(
                distro_name, "pkill -f 'clawbot gateway' || true"
            )
            self._wsl_manager.execute_command(
                distro_name, "nohup clawbot gateway > /dev/null 2>&1 &"
            )
        
        r = self._wsl_manager.execute_command(distro_name, "clawbot --version")
        if r.success:
            version = r.stdout.strip()
            logger.info(f"[{distro_name}] 升级成功: {version}")
            return True, f"升级成功: {version}"
        
        logger.info(f"[{distro_name}] 升级成功")
        return True, "升级成功"


_service = ClawbotUpgrader()
register_service(_service)
