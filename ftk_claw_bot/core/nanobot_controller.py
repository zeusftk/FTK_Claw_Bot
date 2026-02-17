import subprocess
import threading
import os
import json
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
from loguru import logger

from ..models import NanobotConfig, NanobotStatus, NanobotInstance
from .wsl_manager import WSLManager
from .config_sync_manager import ConfigSyncManager

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False


class NanobotController:
    def __init__(self, wsl_manager: WSLManager):
        self._wsl_manager = wsl_manager
        self._config_sync_manager = ConfigSyncManager(wsl_manager)
        self._instances: dict[str, NanobotInstance] = {}
        self._log_callbacks: list = []
        self._status_callbacks: list = []

    def start(self, config: NanobotConfig) -> bool:
        distro = self._wsl_manager.get_distro(config.distro_name)
        if not distro:
            return False

        if not distro.is_running:
            if not self._wsl_manager.start_distro(config.distro_name):
                return False

        workspace = config.workspace
        if config.sync_to_mnt and config.windows_workspace:
            workspace = self._wsl_manager.convert_windows_to_wsl_path(config.windows_workspace)

        self._ensure_workspace(config.distro_name, workspace)

        if config.apiKey:
            self._write_nanobot_config(config)

        args = config.to_nanobot_args()
        cmd = ["nanobot"] + args

        instance = NanobotInstance(
            config=config,
            status=NanobotStatus.STARTING,
            started_at=datetime.now()
        )
        self._instances[config.name] = instance

        thread = threading.Thread(
            target=self._run_nanobot,
            args=(config.distro_name, cmd, config.name),
            daemon=True
        )
        thread.start()

        return True

    def _ensure_workspace(self, distro_name: str, workspace: str):
        result = self._wsl_manager.execute_command(
            distro_name,
            f"mkdir -p '{workspace}'"
        )
        return result.success

    def _write_nanobot_config(self, config: NanobotConfig):
        config_content = config.to_full_nanobot_config()
        config_json = json.dumps(config_content, indent=2)
        
        # 首先写入到 Windows 一侧
        config_dir = os.path.dirname(config.config_path) if config.config_path else None
        if config_dir and config.sync_to_mnt and config.windows_workspace:
            windows_config_dir = self._wsl_manager.convert_wsl_to_windows_path(config_dir)
            Path(windows_config_dir).mkdir(parents=True, exist_ok=True)

            config_file = os.path.join(windows_config_dir, "config.json")
            with open(config_file, "w", encoding="utf-8") as f:
                f.write(config_json)
        
        # 然后同步到 WSL 分发中
        workspace = config.workspace
        if config.sync_to_mnt and config.windows_workspace:
            workspace = self._wsl_manager.convert_windows_to_wsl_path(config.windows_workspace)
        
        if workspace:
            # 在 WSL 中创建目录并写入配置文件
            self._wsl_manager.execute_command(
                config.distro_name,
                f"mkdir -p '{workspace}' && cat > '{workspace}/config.json' << 'EOF'\n{config_json}\nEOF"
            )

    def _run_nanobot(self, distro_name: str, cmd: List[str], instance_name: str):
        instance = self._instances.get(instance_name)
        if not instance:
            return

        try:
            full_cmd = ["wsl.exe", "-d", distro_name, "--"] + cmd

            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-16-le",
                errors="replace"
            )

            instance.pid = process.pid
            instance.status = NanobotStatus.RUNNING
            self._notify_status(instance_name)

            def read_output(pipe, log_type):
                for line in iter(pipe.readline, ""):
                    if line:
                        cleaned_line = line.replace('\x00', '').strip()
                        if cleaned_line:
                            # Store log in instance
                            instance.add_log(log_type, cleaned_line)
                            # Notify external callbacks
                            self._notify_log(instance_name, log_type, cleaned_line)

            stdout_thread = threading.Thread(
                target=read_output,
                args=(process.stdout, "stdout"),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=read_output,
                args=(process.stderr, "stderr"),
                daemon=True
            )
            stdout_thread.start()
            stderr_thread.start()

            process.wait()

            instance.status = NanobotStatus.STOPPED
            instance.pid = None
            self._notify_status(instance_name)

        except Exception as e:
            instance.status = NanobotStatus.ERROR
            instance.last_error = str(e)
            self._notify_status(instance_name)

    def stop(self, config_name: str) -> bool:
        instance = self._instances.get(config_name)
        if not instance or not instance.pid:
            return False

        try:
            if instance.config.distro_name:
                result = self._wsl_manager.execute_command(
                    instance.config.distro_name,
                    f"pkill -f 'nanobot.*{config_name}' || true"
                )

            instance.status = NanobotStatus.STOPPED
            instance.pid = None
            self._notify_status(config_name)
            return True
        except Exception:
            return False

    def restart(self, config_name: str) -> bool:
        instance = self._instances.get(config_name)
        if not instance:
            return False

        if self.stop(config_name):
            import time
            time.sleep(1)
            return self.start(instance.config)
        return False

    def get_instance(self, config_name: str) -> Optional[NanobotInstance]:
        return self._instances.get(config_name)

    def get_status(self, config_name: str) -> Optional[NanobotStatus]:
        instance = self._instances.get(config_name)
        return instance.status if instance else None

    def is_running(self, config_name: str, check_connectivity: bool = False) -> bool:
        """Check if nanobot instance is running.

        Args:
            config_name: The configuration name
            check_connectivity: If True, also verify WebSocket connectivity

        Returns:
            True if running (and reachable if check_connectivity is True)
        """
        instance = self._instances.get(config_name)
        if instance is None or instance.status != NanobotStatus.RUNNING:
            return False

        if not check_connectivity:
            return True

        return self._check_websocket_connectivity(instance)

    def _check_websocket_connectivity(self, instance: NanobotInstance) -> bool:
        """Check if nanobot instance is reachable via WebSocket.

        Args:
            instance: The nanobot instance to check

        Returns:
            True if WebSocket connection can be established
        """
        if not WEBSOCKETS_AVAILABLE:
            return False

        distro = self._wsl_manager.get_distro(instance.config.distro_name)
        if not distro or not distro.is_running:
            return False

        ip = self._wsl_manager.get_distro_ip(instance.config.distro_name)
        if not ip:
            return False

        gateway_url = f"ws://{ip}:{instance.config.gateway_port}/ws"

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(self._async_check_connectivity(gateway_url))
            loop.close()
            return success
        except Exception:
            return False

    async def _async_check_connectivity(self, gateway_url: str) -> bool:
        """Async method to check WebSocket connectivity."""
        try:
            async with websockets.connect(gateway_url, open_timeout=5) as ws:
                return True
        except Exception:
            return False
    
    def check_gateway_connectivity(self, distro_name: str, gateway_port: int) -> bool:
        """Check if gateway is reachable via WebSocket.
        
        This method doesn't require an in-memory instance, it directly checks
        the WebSocket connection.
        
        Args:
            distro_name: WSL distro name
            gateway_port: Gateway port number
            
        Returns:
            True if WebSocket connection can be established
        """
        if not WEBSOCKETS_AVAILABLE:
            return False
        
        distro = self._wsl_manager.get_distro(distro_name)
        if not distro or not distro.is_running:
            return False
        
        ip = self._wsl_manager.get_distro_ip(distro_name)
        if not ip:
            return False
        
        gateway_url = f"ws://{ip}:{gateway_port}/ws"
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(self._async_check_connectivity(gateway_url))
            loop.close()
            return success
        except Exception:
            return False

    def get_logs(self, config_name: str, lines: int = 100) -> List[str]:
        """Get logs for a specific nanobot instance.

        Args:
            config_name: The configuration name
            lines: Number of log lines to retrieve (default: 100)

        Returns:
            List of log lines
        """
        instance = self._instances.get(config_name)
        if instance:
            return instance.get_logs(lines)
        return []

    def register_log_callback(self, callback):
        if callback not in self._log_callbacks:
            self._log_callbacks.append(callback)

    def register_status_callback(self, callback):
        if callback not in self._status_callbacks:
            self._status_callbacks.append(callback)

    def _notify_log(self, instance_name: str, log_type: str, message: str):
        for callback in self._log_callbacks:
            try:
                callback(instance_name, log_type, message)
            except Exception:
                pass

    def _notify_status(self, instance_name: str):
        instance = self._instances.get(instance_name)
        if instance:
            for callback in self._status_callbacks:
                try:
                    callback(instance_name, instance.status)
                except Exception:
                    pass

    def install_systemd_service(self, distro_name: str) -> bool:
        """Install nanobot as systemd service in WSL2."""
        try:
            service_content = """[Unit]
Description=Nanobot Gateway Service
After=network.target

[Service]
Type=simple
User=%I
ExecStart=/usr/bin/nanobot gateway
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
            result = self._wsl_manager.execute_command(
                distro_name,
                f"cat > /etc/systemd/system/nanobot-gateway.service << 'EOF'\n{service_content}\nEOF"
            )
            if not result.success:
                return False

            self._wsl_manager.execute_command(distro_name, "sudo systemctl daemon-reload")
            self._wsl_manager.execute_command(distro_name, "sudo systemctl enable nanobot-gateway")
            return True
        except Exception:
            return False

    def uninstall_systemd_service(self, distro_name: str) -> bool:
        """Uninstall nanobot systemd service."""
        try:
            self._wsl_manager.execute_command(distro_name, "sudo systemctl stop nanobot-gateway")
            self._wsl_manager.execute_command(distro_name, "sudo systemctl disable nanobot-gateway")
            self._wsl_manager.execute_command(
                distro_name, "sudo rm -f /etc/systemd/system/nanobot-gateway.service"
            )
            self._wsl_manager.execute_command(distro_name, "sudo systemctl daemon-reload")
            return True
        except Exception:
            return False

    def is_systemd_service_installed(self, distro_name: str) -> bool:
        """Check if systemd service is installed."""
        result = self._wsl_manager.execute_command(
            distro_name, "test -f /etc/systemd/system/nanobot-gateway.service"
        )
        return result.success

    def read_config_from_wsl(self, distro_name: str, config_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """从 WSL 读取配置
        
        Args:
            distro_name: WSL 分发名称
            config_path: 配置文件路径（可选）
        
        Returns:
            配置字典，失败返回 None
        """
        return self._config_sync_manager.read_from_wsl(distro_name, config_path)
    
    def sync_config_to_wsl(self, config: NanobotConfig) -> bool:
        """将配置同步到 WSL 分发中，包含备份和重启。
        基于原有 config 只修改对应参数，不整体替换。

        Args:
            config: 要同步的配置对象

        Returns:
            bool: 同步是否成功
        """
        from datetime import datetime
        
        logger.info(f"========== 开始同步配置到 WSL ==========")
        logger.info(f"分发名称: {config.distro_name}")
        
        distro = self._wsl_manager.get_distro(config.distro_name)
        if not distro:
            logger.warning(f"✗ 未找到 WSL 分发: {config.distro_name}")
            return False

        if not distro.is_running:
            logger.info(f"启动 WSL 分发: {config.distro_name}")
            if not self._wsl_manager.start_distro(config.distro_name):
                logger.error(f"✗ 启动 WSL 分发失败: {config.distro_name}")
                return False
            logger.info(f"✓ WSL 分发启动成功: {config.distro_name}")

        # 1. 备份原有配置
        logger.info(f"步骤1: 备份原有配置")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_cmd = f"mkdir -p ~/.nanobot && [ -f ~/.nanobot/config.json ] && cp ~/.nanobot/config.json ~/.nanobot/config.json.bak_{timestamp} || true"
        logger.debug(f"执行备份命令: {backup_cmd}")
        backup_result = self._wsl_manager.execute_command(config.distro_name, backup_cmd)
        if backup_result.success:
            logger.info(f"✓ 配置备份成功: config.json.bak_{timestamp}")
        else:
            logger.warning(f"⚠ 配置备份可能失败: {backup_result.stderr}")
        
        # 2. 读取原有配置
        logger.info(f"步骤2: 读取原有配置")
        existing_config = {}
        read_cmd = "cat ~/.nanobot/config.json 2>/dev/null || echo '{}'"
        read_result = self._wsl_manager.execute_command(config.distro_name, read_cmd)
        
        if read_result.success and read_result.stdout.strip():
            try:
                existing_config = json.loads(read_result.stdout.strip())
                logger.info(f"✓ 成功读取原有配置")
                logger.debug(f"原有配置内容: {json.dumps(existing_config, indent=2)[:300]}...")
            except Exception as e:
                logger.warning(f"⚠ 解析原有配置失败: {e}，将使用空配置")
                existing_config = {}
        else:
            logger.info(f"原有配置不存在或为空，将创建新配置")
        
        # 3. 基于原有配置，只修改 FTK Bot 面板对应的字段
        logger.info(f"步骤3: 基于原有配置更新字段")
        ftp_config = config.to_full_nanobot_config()
        
        # 更新 agents.defaults
        if "agents" not in existing_config:
            existing_config["agents"] = {}
        if "defaults" not in existing_config["agents"]:
            existing_config["agents"]["defaults"] = {}
        
        if "model" in ftp_config.get("agents", {}).get("defaults", {}):
            existing_config["agents"]["defaults"]["model"] = ftp_config["agents"]["defaults"]["model"]
            logger.info(f"✓ 更新 model: {existing_config['agents']['defaults']['model']}")
        
        if "workspace" in ftp_config.get("agents", {}).get("defaults", {}):
            existing_config["agents"]["defaults"]["workspace"] = ftp_config["agents"]["defaults"]["workspace"]
            logger.info(f"✓ 更新 workspace: {existing_config['agents']['defaults']['workspace']}")
        
        # 更新 providers
        if "providers" in ftp_config:
            if "providers" not in existing_config:
                existing_config["providers"] = {}
            
            for provider_name, provider_data in ftp_config["providers"].items():
                if provider_name not in existing_config["providers"]:
                    existing_config["providers"][provider_name] = {}
                
                if "apiKey" in provider_data:
                    existing_config["providers"][provider_name]["apiKey"] = provider_data["apiKey"]
                    logger.info(f"✓ 更新 {provider_name}.apiKey")
                
                if "apiBase" in provider_data:
                    existing_config["providers"][provider_name]["apiBase"] = provider_data["apiBase"]
                    logger.info(f"✓ 更新 {provider_name}.apiBase: {provider_data['apiBase']}")
                
                if "model" in provider_data:
                    existing_config["providers"][provider_name]["model"] = provider_data["model"]
                    logger.info(f"✓ 更新 {provider_name}.model: {provider_data['model']}")
        
        # 更新 gateway
        if "gateway" in ftp_config:
            if "gateway" not in existing_config:
                existing_config["gateway"] = {}
            
            if "host" in ftp_config["gateway"]:
                existing_config["gateway"]["host"] = ftp_config["gateway"]["host"]
                logger.info(f"✓ 更新 gateway.host: {existing_config['gateway']['host']}")
            
            if "port" in ftp_config["gateway"]:
                existing_config["gateway"]["port"] = ftp_config["gateway"]["port"]
                logger.info(f"✓ 更新 gateway.port: {existing_config['gateway']['port']}")
        
        # 更新 tools
        if "tools" in ftp_config:
            if "tools" not in existing_config:
                existing_config["tools"] = {}
            
            if "web" in ftp_config["tools"]:
                if "web" not in existing_config["tools"]:
                    existing_config["tools"]["web"] = {}
                
                if "search" in ftp_config["tools"]["web"]:
                    if "search" not in existing_config["tools"]["web"]:
                        existing_config["tools"]["web"]["search"] = {}
                    
                    if "apiKey" in ftp_config["tools"]["web"]["search"]:
                        existing_config["tools"]["web"]["search"]["apiKey"] = ftp_config["tools"]["web"]["search"]["apiKey"]
                        logger.info(f"✓ 更新 tools.web.search.apiKey")
        
        # 更新 channels
        if "channels" in ftp_config:
            if "channels" not in existing_config:
                existing_config["channels"] = {}
            
            for channel_name, channel_data in ftp_config["channels"].items():
                if channel_data.get("enabled"):
                    existing_config["channels"][channel_name] = channel_data
                    logger.info(f"✓ 更新 channels.{channel_name}")
                elif channel_name in existing_config.get("channels", {}):
                    existing_config["channels"][channel_name]["enabled"] = channel_data.get("enabled", False)
                    logger.info(f"✓ 更新 channels.{channel_name}.enabled = {channel_data.get('enabled', False)}")
        
        # 4. 保存更新后的配置
        logger.info(f"步骤4: 保存更新后的配置")
        config_json = json.dumps(existing_config, indent=2, ensure_ascii=False)
        logger.debug(f"要写入的配置内容: {config_json}")
        
        write_cmd = f"mkdir -p ~/.nanobot && cat > ~/.nanobot/config.json << 'EOF'\n{config_json}\nEOF"
        logger.debug(f"执行写入命令")
        write_result = self._wsl_manager.execute_command(config.distro_name, write_cmd)
        
        if not write_result.success:
            logger.error(f"✗ 写入配置失败: {write_result.stderr}")
            return False
        
        logger.info(f"✓ 配置保存成功: ~/.nanobot/config.json")
        
        # 验证配置是否写入成功
        verify_cmd = "cat ~/.nanobot/config.json"
        verify_result = self._wsl_manager.execute_command(config.distro_name, verify_cmd)
        if verify_result.success:
            logger.debug(f"验证写入的配置: {verify_result.stdout[:200]}...")
        
        # 5. 重启 nanobot 服务
        logger.info(f"步骤5: 重启 nanobot 服务")
        restart_cmd = "sudo systemctl restart nanobot 2>/dev/null || systemctl --user restart nanobot 2>/dev/null || true"
        logger.debug(f"执行重启命令: {restart_cmd}")
        restart_result = self._wsl_manager.execute_command(
            config.distro_name,
            restart_cmd
        )
        
        if restart_result.success:
            logger.info(f"✓ nanobot 服务重启成功: {config.distro_name}")
        else:
            logger.warning(f"⚠ nanobot 服务重启可能失败: {restart_result.stderr}")
        
        logger.info(f"========== 同步配置到 WSL 完成 ==========")
        return True
