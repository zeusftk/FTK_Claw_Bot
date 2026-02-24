import os
import subprocess
import time
from typing import Optional, Callable, Tuple
from pathlib import Path

from loguru import logger

"""
测试：
curl -sk --connect-timeout 5 -o /dev/null -w '%{http_code}' 'https://mirrors.tuna.tsinghua.edu.cn/ubuntu/' 2>/dev/null
"""

##修复环境中的遗留依赖
necessary_packages = [
    "netifaces",
]

# 镜像源配置
MIRROR_SOURCES = [
    {
        "name": "tsinghua",
        "url": "https://mirrors.tuna.tsinghua.edu.cn/ubuntu",
        "test_url": "https://mirrors.tuna.tsinghua.edu.cn/ubuntu/",
        "sources": """deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu/ jammy-security main restricted universe multiverse
"""
    },
    {
        "name": "ustc",
        "url": "https://mirrors.ustc.edu.cn/ubuntu",
        "test_url": "https://mirrors.ustc.edu.cn/ubuntu/dists/jammy/InRelease",
        "sources": """deb https://mirrors.ustc.edu.cn/ubuntu/ jammy main restricted universe multiverse
deb https://mirrors.ustc.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse
deb https://mirrors.ustc.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu/ jammy-security main restricted universe multiverse
"""
    },
    {
        "name": "tencent",
        "url": "https://mirrors.cloud.tencent.com/ubuntu",
        "test_url": "https://mirrors.cloud.tencent.com/ubuntu/dists/jammy/InRelease",
        "sources": """deb https://mirrors.cloud.tencent.com/ubuntu/ jammy main restricted universe multiverse
deb https://mirrors.cloud.tencent.com/ubuntu/ jammy-updates main restricted universe multiverse
deb https://mirrors.cloud.tencent.com/ubuntu/ jammy-backports main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu/ jammy-security main restricted universe multiverse
"""
    },
    {
        "name": "default",
        "url": "http://archive.ubuntu.com/ubuntu",
        "test_url": None,
        "sources": """deb http://archive.ubuntu.com/ubuntu/ jammy main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ jammy-updates main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ jammy-backports main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu/ jammy-security main restricted universe multiverse
"""
    }
]

DEFAULT_MIRROR_INDEX = 0
MAX_RETRY_COUNT = 3


class WSLInitializer:
    """WSL 分发初始化器 - 使用 Python 实现完整的初始化流程"""

    def __init__(self, wsl_manager):
        self._wsl_manager = wsl_manager
        self._distro_name: str = ""
        self._progress_callback: Optional[Callable[[int, str], None]] = None
        self._step_callback: Optional[Callable[[int, str, str], None]] = None
        self._log_callback: Optional[Callable[[str], None]] = None
        self._current_mirror_index: int = DEFAULT_MIRROR_INDEX
        self._tested_mirrors: set = set()

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

    def _run_wsl_command(self, command: str, timeout: int = 300) -> Tuple[bool, str, str]:
        result = self._wsl_manager.execute_command(
            self._distro_name,
            command,
            timeout=timeout
        )
        return result.success, result.stdout or "", result.stderr or ""

    def _test_mirror(self, mirror: dict) -> bool:
        if mirror["test_url"] is None:
            return True
        
        test_url = mirror["test_url"]
        success, stdout, _ = self._run_wsl_command(
            f"curl -sk --connect-timeout 5 -o /dev/null -w '%{{http_code}}' "
            f"'{test_url}' 2>/dev/null",
            timeout=10
        )
        
        http_code = stdout.strip()
        if success and http_code:
            self._emit_log(f"镜像 {mirror['name']} 可用 (HTTP {http_code})")
            return True
        
        self._emit_log(f"镜像 {mirror['name']} 不可用 (HTTP {http_code})")
        return False

    def _select_available_mirror(self) -> Tuple[dict, int]:
        for i, mirror in enumerate(MIRROR_SOURCES):
            if i in self._tested_mirrors:
                continue
            
            self._tested_mirrors.add(i)
            
            if self._test_mirror(mirror):
                self._current_mirror_index = i
                return mirror, i
        
        self._emit_log("所有镜像已测试，使用默认镜像")
        return MIRROR_SOURCES[-1], len(MIRROR_SOURCES) - 1

    def _switch_to_next_mirror(self) -> Tuple[dict, bool]:
        self._emit_log(f"从 {MIRROR_SOURCES[self._current_mirror_index]['name']} 切换...")
        
        for i in range(self._current_mirror_index + 1, len(MIRROR_SOURCES)):
            if self._test_mirror(MIRROR_SOURCES[i]):
                self._current_mirror_index = i
                return MIRROR_SOURCES[i], True
        
        return MIRROR_SOURCES[-1], False

    def _apply_mirror(self, mirror: dict) -> Tuple[bool, str]:
        self._emit_log(f"应用镜像: {mirror['name']}")
        
        self._run_wsl_command("cp /etc/apt/sources.list /etc/apt/sources.list.bak 2>/dev/null || true")
        
        sources_content = mirror["sources"].replace("'", "'\\''")
        success, _, stderr = self._run_wsl_command(
            f"printf '%s' '{sources_content}' > /etc/apt/sources.list"
        )
        
        if not success:
            return False, f"应用镜像失败: {stderr}"
        
        return True, ""

    def _retry_with_mirror_switch(self, step_func, step_name: str, *args) -> Tuple[bool, str]:
        last_error = ""
        
        for attempt in range(MAX_RETRY_COUNT):
            success, error = step_func(*args)
            
            if success:
                return True, ""
            
            last_error = error
            self._emit_log(f"{step_name} 失败 (尝试 {attempt + 1}/{MAX_RETRY_COUNT}): {error}")
            
            if attempt < MAX_RETRY_COUNT - 1:
                new_mirror, has_more = self._switch_to_next_mirror()
                
                if has_more and new_mirror["name"] != MIRROR_SOURCES[self._current_mirror_index]["name"]:
                    self._emit_log(f"切换到 {new_mirror['name']} 并重试...")
                    apply_success, apply_error = self._apply_mirror(new_mirror)
                    
                    if not apply_success:
                        self._emit_log(f"应用新镜像失败: {apply_error}")
                        continue
                else:
                    self._emit_log("没有更多可用镜像")
                    break
        
        return False, f"{step_name} 在 {MAX_RETRY_COUNT} 次尝试后失败: {last_error}"

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
        
        self._tested_mirrors = set()
        self._current_mirror_index = DEFAULT_MIRROR_INDEX

        steps = [
            ("导入 Ubuntu 镜像", self._import_tar, (tar_path, install_location), False),
            ("验证 WSL 网络", self._verify_wsl_network, (), False),
            ("配置镜像源", self._configure_mirror, (), False),
            ("更新系统包", self._update_apt, (), True),
            ("安装基础工具", self._install_basic_tools, (), True),
            ("安装 Python 3.11", self._install_python, (), True),
            ("安装 clawbot", self._install_clawbot, (whl_path,), False),
        ]

        if not skip_nodejs:
            steps.append(("安装 Node.js", self._install_nodejs, (), False))

        steps.append(("配置系统服务", self._setup_service, (), False))

        total_steps = len(steps)

        for i, (step_name, step_func, args, use_retry) in enumerate(steps):
            self._emit_step(i, step_name, "running")
            self._emit_log(f"开始: {step_name}")

            try:
                if use_retry:
                    success, error_msg = self._retry_with_mirror_switch(step_func, step_name, *args)
                else:
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

    def _verify_wsl_network(self) -> Tuple[bool, str]:
        self._emit_log("验证 WSL 分发状态...")    
        for i in range(20):
            time.sleep(10)
            success, stdout, stderr = self._run_wsl_command("echo 'WSL OK'", timeout=10)
            if success:
                break
            if i > 0 and i % 5 == 0:
                restart_success = self._wsl_manager.stop_distro(self._distro_name)
                time.sleep(15)
                if restart_success:
                    restart_success = self._wsl_manager.start_distro(self._distro_name)
                    time.sleep(15)
                if not restart_success:
                    return False, f"分发启动失败: {stderr}"
        
        if not success:
            self._emit_log(f"WSL 分发响应异常: {stderr}")
            return False, f"分发响应异常: {stderr}"
        
        self._emit_log("检查 curl 命令...")
        success, stdout, stderr = self._run_wsl_command("which curl", timeout=10)
        if not success or not stdout.strip():
            self._emit_log("curl 未安装，尝试安装...")
            success, _, stderr = self._run_wsl_command("apt update && apt install -y curl", timeout=120)
            if not success:
                return False, f"安装 curl 失败: {stderr}"
        
        self._emit_log("测试网络连接...")
        test_urls = [
            "https://mirrors.tuna.tsinghua.edu.cn/ubuntu/",
            "https://mirrors.ustc.edu.cn/ubuntu/",
            "http://archive.ubuntu.com/ubuntu/",
        ]
        
        network_ok = False
        last_error = ""
        for test_url in test_urls:
            success, stdout, stderr = self._run_wsl_command(
                f"curl -sk --connect-timeout 10 -o /dev/null -w '%{{http_code}}' '{test_url}' 2>/dev/null",
                timeout=15
            )
            http_code = stdout.strip()
            if success and http_code and http_code != "000":
                self._emit_log(f"网络测试成功: (HTTP {http_code})")
                network_ok = True
                break
            else:
                last_error = f"HTTP {http_code}" if http_code else stderr
                self._emit_log(f"网络测试失败: {test_url} ({last_error})")
        
        if not network_ok:
            self._emit_log("网络连接异常，尝试重启分发...")
            if self._wsl_manager.stop_distro(self._distro_name):
                time.sleep(2)
                if self._wsl_manager.start_distro(self._distro_name):
                    time.sleep(3)
                    self._emit_log("分发已重启，重新测试网络...")
                    for test_url in test_urls:
                        success, stdout, stderr = self._run_wsl_command(
                            f"curl -sk --connect-timeout 10 -o /dev/null -w '%{{http_code}}' '{test_url}' 2>/dev/null",
                            timeout=15
                        )
                        http_code = stdout.strip()
                        if success and http_code and http_code != "000":
                            self._emit_log(f"重启后网络测试成功: {test_url} (HTTP {http_code})")
                            network_ok = True
                            break
            
            if not network_ok:
                return False, f"网络连接失败，重启分发后仍无法连接: {last_error}"
        
        self._emit_log("WSL 分发验证通过")
        return True, ""

    def _configure_mirror(self) -> Tuple[bool, str]:
        self._emit_log("选择最佳镜像...")
        
        mirror, index = self._select_available_mirror()
        self._current_mirror_index = index
        
        success, error = self._apply_mirror(mirror)
        if not success:
            return False, error
        
        self._emit_log(f"成功配置镜像: {mirror['name']}")
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
        self._emit_log(f"Python安装...")
        success, _, stderr = self._run_wsl_command(
            "add-apt-repository -y ppa:deadsnakes/ppa && apt update",
            timeout=120
        )
        if not success:
            return False, f"添加 PPA 失败: {stderr}"
        
        success, _, stderr = self._run_wsl_command(
            "apt install -y python3.11 python3.11-venv python3.11-dev python3-pip",
            timeout=600
        )
        if not success:
            return False, f"安装 Python 失败: {stderr}"
        
        ##配置 Python 符号链接
        self._run_wsl_command("update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1")
        self._run_wsl_command("update-alternatives --install /usr/bin/python3 python /usr/bin/python3.11 1")
        self._run_wsl_command("ln -sf /usr/bin/python3 /usr/bin/python")
        self._run_wsl_command("apt install -y python3-pip")
        self._run_wsl_command("ln -sf /usr/bin/pip3 /usr/bin/pip")

        pip_mirrors = [
            "https://mirrors.aliyun.com/pypi/simple/",
            "https://pypi.mirrors.ustc.edu.cn/simple/",
            "https://pypi.tuna.tsinghua.edu.cn/simple/",
            "https://pypi.org/simple/"
        ]

        self._emit_log("升级 pip...")
        success, stdout = False, ""
        for mirror in pip_mirrors:
            self._run_wsl_command(f"pip config set global.index-url {mirror}")
            tmpdomain=mirror.split("/")[2]
            self._run_wsl_command(f"pip config set global.extra-index-url {tmpdomain}")
            self._run_wsl_command("python -m pip install --upgrade pip")
            success, stdout, _ = self._run_wsl_command("python --version")
            if success:
                break

        if not success:
            return False, f"获取 Python 版本失败: {stdout.strip()}"
        self._emit_log(f"Python 版本: {stdout.strip()}")

        return True, ""

    def _install_clawbot(self, whl_path: str) -> Tuple[bool, str]:
        if not os.path.exists(whl_path):
            return False, f"Wheel 文件不存在: {whl_path}"

        whl_name = os.path.basename(whl_path)
        # self._emit_log(f"安装 clawbot: {whl_name}")

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
        for i in necessary_packages:
            success, _, stderr = self._run_wsl_command(f"pip show {i}")
            if not success:
                self._run_wsl_command(f"pip install {i}")

        success, _, stderr = self._run_wsl_command(f"pip install /tmp/{whl_name}", timeout=300)
        if not success:
            return False, f"安装 clawbot 失败: {stderr}"

        self._run_wsl_command(f"rm -f /tmp/{whl_name}")

        success, stdout, _ = self._run_wsl_command("nanobot --version")
        if success:
            version = stdout.replace('\n', '').replace('\r', '').strip().replace('nanobot', '')
            self._emit_log(f"clawbot 版本: {version}")

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
