import os
import subprocess
from typing import Optional, Callable, Tuple
from pathlib import Path

from loguru import logger


class WSLInitializer:
    """WSL 分发初始化器 - 使用 Python 实现完整的初始化流程"""

    def __init__(self, wsl_manager):
        self._wsl_manager = wsl_manager
        self._distro_name: str = ""
        self._progress_callback: Optional[Callable[[int, str], None]] = None
        self._step_callback: Optional[Callable[[int, str, str], None]] = None
        self._log_callback: Optional[Callable[[str], None]] = None

    def set_progress_callback(self, callback: Callable[[int, str], None]):
        self._progress_callback = callback

    def set_step_callback(self, callback: Callable[[int, str, str], None]):
        self._step_callback = callback

    def set_log_callback(self, callback: Callable[[str], None]):
        self._log_callback = callback

    def _emit_progress(self, percent: int, status: str):
        if self._progress_callback:
            self._progress_callback(percent, status)

    def _emit_step(self, step_index: int, step_name: str, status: str):
        if self._step_callback:
            self._step_callback(step_index, step_name, status)

    def _emit_log(self, message: str):
        if self._log_callback:
            self._log_callback(message)
        logger.info(f"[WSLInitializer] {message}")

    def _run_wsl_command(self, command: str, timeout: int = 300) -> Tuple[bool, str, str]:
        result = self._wsl_manager.execute_command(
            self._distro_name,
            command,
            timeout=timeout
        )
        return result.success, result.stdout or "", result.stderr or ""

    def initialize_distro(
        self,
        distro_name: str,
        tar_path: str,
        whl_path: str,
        install_location: Optional[str] = None,
        skip_nodejs: bool = False
    ) -> Tuple[bool, str]:
        self._distro_name = distro_name
        self._emit_log(f"开始初始化分发: {distro_name}")

        steps = [
            ("导入 Ubuntu 镜像", self._import_tar, (tar_path, install_location)),
            ("配置镜像源", self._configure_mirror, ()),
            ("更新系统包", self._update_apt, ()),
            ("安装基础工具", self._install_basic_tools, ()),
            ("安装 Python 3.11", self._install_python, ()),
            ("安装 clawbot", self._install_clawbot, (whl_path,)),
        ]

        if not skip_nodejs:
            steps.append(("安装 Node.js", self._install_nodejs, ()))

        steps.append(("配置系统服务", self._setup_service, ()))

        total_steps = len(steps)

        for i, (step_name, step_func, args) in enumerate(steps):
            self._emit_step(i, step_name, "running")
            self._emit_log(f"开始: {step_name}")

            try:
                success, error_msg = step_func(*args)
                if not success:
                    self._emit_step(i, step_name, "error")
                    return False, f"{step_name} 失败: {error_msg}"

                self._emit_step(i, step_name, "done")
                progress = int((i + 1) / total_steps * 100)
                self._emit_progress(progress, f"{step_name} 完成")

            except Exception as e:
                self._emit_step(i, step_name, "error")
                logger.exception(f"{step_name} 异常")
                return False, f"{step_name} 异常: {str(e)}"

        self._emit_progress(100, "初始化完成")
        return True, "初始化成功"

    def _import_tar(self, tar_path: str, install_location: Optional[str]) -> Tuple[bool, str]:
        if not os.path.exists(tar_path):
            return False, f"镜像文件不存在: {tar_path}"

        result = self._wsl_manager.import_distro(
            tar_path,
            self._distro_name,
            install_location
        )

        if not result.success:
            return False, f"导入失败: {result.stderr}"

        return True, ""

    def _configure_mirror(self) -> Tuple[bool, str]:
        self._emit_log("测试镜像可用性...")

        success, stdout, _ = self._run_wsl_command(
            "curl -s --connect-timeout 5 -o /dev/null -w '%{http_code}' "
            "http://mirrors.aliyun.com/ubuntu/dists/jammy/InRelease 2>/dev/null | "
            "grep -q '200' && echo OK || echo FAIL"
        )

        if success and "OK" in stdout:
            self._emit_log("使用阿里云镜像")
            mirror_content = """deb http://mirrors.aliyun.com/ubuntu/ jammy main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-updates main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-backports main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-security main restricted universe multiverse
"""
        else:
            self._emit_log("使用默认镜像")
            mirror_content = """deb http://archive.ubuntu.com/ubuntu/ jammy main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ jammy-updates main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ jammy-backports main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu/ jammy-security main restricted universe multiverse
"""

        self._run_wsl_command("cp /etc/apt/sources.list /etc/apt/sources.list.bak 2>/dev/null || true")
        success, _, stderr = self._run_wsl_command(f"printf '{mirror_content}' > /etc/apt/sources.list")

        if not success:
            return False, f"配置镜像源失败: {stderr}"

        return True, ""

    def _update_apt(self) -> Tuple[bool, str]:
        self._emit_log("更新 apt...")

        success, _, stderr = self._run_wsl_command(
            "apt update 2>/dev/null || apt update -o Acquire::Check-Valid-Until=false",
            timeout=300
        )

        if not success:
            return False, f"apt update 失败: {stderr}"

        self._emit_log("升级系统包...")
        self._run_wsl_command("apt upgrade -y", timeout=600)

        return True, ""

    def _install_basic_tools(self) -> Tuple[bool, str]:
        self._emit_log("安装基础工具...")

        success, _, stderr = self._run_wsl_command(
            "apt install -y curl wget git software-properties-common build-essential",
            timeout=600
        )

        if not success:
            return False, f"安装基础工具失败: {stderr}"

        return True, ""

    def _install_python(self) -> Tuple[bool, str]:
        self._emit_log("添加 deadsnakes PPA...")
        success, _, stderr = self._run_wsl_command(
            "add-apt-repository -y ppa:deadsnakes/ppa && apt update",
            timeout=120
        )

        if not success:
            return False, f"添加 PPA 失败: {stderr}"

        self._emit_log("安装 Python 3.11...")
        success, _, stderr = self._run_wsl_command(
            "apt install -y python3.11 python3.11-venv python3.11-dev python3-pip",
            timeout=600
        )

        if not success:
            return False, f"安装 Python 失败: {stderr}"

        self._emit_log("配置 Python 符号链接...")
        self._run_wsl_command("rm -f /usr/bin/python && ln -sf /usr/bin/python3.11 /usr/bin/python")
        self._run_wsl_command("rm -f /usr/bin/pip && ln -sf /usr/local/bin/pip3.11 /usr/bin/pip 2>/dev/null || ln -sf /usr/bin/pip3 /usr/bin/pip")
        self._run_wsl_command("ln /usr/local/bin/pip3.11 /usr/bin/pip3 2>/dev/null || true")
        self._run_wsl_command("ln /usr/bin/python3.11 /usr/bin/python3")

        self._emit_log("安装 pip...")
        self._run_wsl_command("python3.11 -m ensurepip --upgrade 2>/dev/null || curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11")

        self._emit_log("配置 pip 镜像...")
        pip_conf = """[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
"""
        self._run_wsl_command(f"mkdir -p ~/.pip && printf '{pip_conf}' > ~/.pip/pip.conf")

        self._emit_log("升级 pip...")
        self._run_wsl_command("python -m pip install --upgrade pip")

        success, stdout, _ = self._run_wsl_command("python --version")
        self._emit_log(f"Python 版本: {stdout.strip()}")

        return True, ""

    def _install_clawbot(self, whl_path: str) -> Tuple[bool, str]:
        if not os.path.exists(whl_path):
            return False, f"Wheel 文件不存在: {whl_path}"

        whl_name = os.path.basename(whl_path)
        self._emit_log(f"安装 clawbot: {whl_name}")

        whl_dir = os.path.dirname(whl_path).replace("\\", "/")

        success, stdout, stderr = self._run_wsl_command(f"wslpath '{whl_dir}'")
        if not success:
            return False, f"转换路径失败: {stderr}"

        wsl_dir = stdout.strip()
        wsl_whl_path = f"{wsl_dir}/{whl_name}"

        self._emit_log(f"复制 wheel 文件到 WSL...")
        success, _, stderr = self._run_wsl_command(f"cp '{wsl_whl_path}' /tmp/{whl_name}")
        if not success:
            return False, f"复制 wheel 文件失败: {stderr}"

        self._emit_log("安装 clawbot...")
        success, _, stderr = self._run_wsl_command(f"pip install /tmp/{whl_name}", timeout=300)
        if not success:
            return False, f"安装 clawbot 失败: {stderr}"

        self._run_wsl_command(f"rm -f /tmp/{whl_name}")

        success, stdout, _ = self._run_wsl_command("nanobot --version")
        if success:
            self._emit_log(f"clawbot 版本: {stdout.strip()}")

        self._emit_log("初始化 clawbot 配置...")
        self._run_wsl_command("nanobot onboard", timeout=60)
        ##删除 whl
        self._run_wsl_command(f"rm -f /tmp/{whl_name}")

        return True, ""

    def _install_nodejs(self) -> Tuple[bool, str]:
        self._emit_log("安装 Node.js 24.x...")

        success, _, stderr = self._run_wsl_command(
            "curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && apt install -y nodejs",
            timeout=600
        )

        if not success:
            self._emit_log(f"Node.js 安装失败: {stderr}，尝试继续...")

        success, stdout, _ = self._run_wsl_command("node --version 2>/dev/null || echo 'N/A'")
        self._emit_log(f"Node.js 版本: {stdout.strip()}")

        success, stdout, _ = self._run_wsl_command("npm --version 2>/dev/null || echo 'N/A'")
        self._emit_log(f"npm 版本: {stdout.strip()}")

        ### 安装 opencode
        self._emit_log("安装 opencode...")
        self._run_wsl_command("npm install -g opencode-ai 2>/dev/null", timeout=300)
        success, stdout, _ = self._run_wsl_command("which opencode 2>/dev/null || echo 'not found'")
        
        if "not found" in stdout:
            self._emit_log("尝试通过官方脚本安装 opencode...")
            self._run_wsl_command("curl -fsSL https://opencode.ai/install | bash", timeout=300)

        success, stdout, _ = self._run_wsl_command("which opencode 2>/dev/null || echo 'not installed'")
        if "not installed" not in stdout:
            self._emit_log(f"opencode 安装位置: {stdout.strip()}")
        else:
            self._emit_log("opencode 未安装，跳过")

        # ### 安装 iflow
        # self._emit_log("安装 iflow...")
        # self._run_wsl_command("npm i -g @iflow-ai/iflow-cli@latest 2>/dev/null", timeout=300)
        # success, stdout, _ = self._run_wsl_command("which iflow 2>/dev/null || echo 'not found'")
        # if "not found" in stdout:
        #     self._emit_log("尝试通过官方脚本安装 iflow...")
        #     self._run_wsl_command("curl -fsSL https://iflow.ai/install | bash", timeout=300)
        # success, stdout, _ = self._run_wsl_command("which iflow 2>/dev/null || echo 'not installed'")
        # if "not installed" not in stdout:
        #     self._emit_log(f"iflow 安装位置: {stdout.strip()}")
        # else:
        #     self._emit_log("iflow 未安装，跳过")

        return True, ""

    def _setup_service(self) -> Tuple[bool, str]:
        self._emit_log("验证 nanobot 配置...")

        success, stdout, _ = self._run_wsl_command(
            "test -f /root/.nanobot/config.json && echo 'OK' || echo 'MISSING'"
        )

        if "MISSING" in stdout:
            self._emit_log("配置不存在，重新运行 onboard...")
            self._run_wsl_command("nanobot onboard", timeout=60)

        self._emit_log("创建 systemd 服务...")

        service_content = """[Unit]
Description=Nanobot AI Agent Service
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/root
Environment=PATH=/usr/local/bin:/usr/bin:/bin
Environment=HOME=/root
ExecStart=/usr/bin/python -m nanobot gateway
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

        success, _, stderr = self._run_wsl_command(
            f"printf '{service_content}' > /etc/systemd/system/nanobot.service"
        )

        if not success:
            return False, f"创建服务文件失败: {stderr}"

        self._emit_log("启用 nanobot 服务...")
        self._run_wsl_command("systemctl daemon-reload && systemctl enable nanobot.service")

        self._emit_log("启动 nanobot 服务...")
        self._run_wsl_command("systemctl start nanobot.service 2>/dev/null || echo 'Service will start on next boot'")

        return True, ""
