import subprocess
import threading
import os
import json
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from ..models import NanobotConfig, NanobotStatus, NanobotInstance
from .wsl_manager import WSLManager


class NanobotController:
    def __init__(self, wsl_manager: WSLManager):
        self._wsl_manager = wsl_manager
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

        if config.api_key:
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
        config_content = config.to_config_json()
        config_dir = os.path.dirname(config.config_path) if config.config_path else None

        if config_dir and config.sync_to_mnt and config.windows_workspace:
            windows_config_dir = self._wsl_manager.convert_wsl_to_windows_path(config_dir)
            Path(windows_config_dir).mkdir(parents=True, exist_ok=True)

            config_file = os.path.join(windows_config_dir, "config.json")
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_content, f, indent=2)

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

    def is_running(self, config_name: str) -> bool:
        instance = self._instances.get(config_name)
        return instance is not None and instance.status == NanobotStatus.RUNNING

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
