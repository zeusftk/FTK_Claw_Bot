import subprocess
import json
import sys
import time
import argparse
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass

try:
    from loguru import logger
    HAS_LOGURU = True
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    HAS_LOGURU = False


@dataclass
class CommandResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int


class NanobotDistroConfigurator:
    """Ubuntu 分发一键配置 Nanobot
    
    将纯净的 Ubuntu 分发配置为 nanobot 运行环境。
    所有操作从 Windows 通过 wsl.exe 执行，无需进入 WSL。
    
    使用示例:
        # 基本用法
        python nanobot_distro_configurator.py Ubuntu-22.04
        
        # 写入配置
        python nanobot_distro_configurator.py Ubuntu-22.04 --api-key YOUR_KEY
        
        # 完整配置
        python nanobot_distro_configurator.py Ubuntu-22.04 \\
            --api-key YOUR_KEY \\
            --model qwen-portal/coder-model \\
            --port 18790
    """
    
    PIP_MIRRORS = [
        "https://pypi.tuna.tsinghua.edu.cn/simple",
        "https://mirrors.aliyun.com/pypi/simple/",
        "https://pypi.douban.com/simple/"
    ]
    
    APT_SOURCES = """deb http://mirrors.aliyun.com/ubuntu/ jammy main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-updates main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-backports main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-security main restricted universe multiverse"""
    
    PIP_CONF = """[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn"""

    def __init__(self, distro_name: str = "Ubuntu-22.04"):
        self.distro_name = distro_name
        self._progress_callback = None

    def set_progress_callback(self, callback):
        self._progress_callback = callback

    def _report_progress(self, step: str, status: str, message: str = ""):
        if self._progress_callback:
            self._progress_callback(step, status, message)
        if status == "start":
            logger.info(f"[{step}] 开始...")
        elif status == "ok":
            logger.success(f"[{step}] 完成: {message}")
        elif status == "warn":
            logger.warning(f"[{step}] 警告: {message}")
        elif status == "error":
            logger.error(f"[{step}] 失败: {message}")

    def _run_command(
        self, 
        cmd_str: str, 
        timeout: int = 300, 
        user: str = "root"
    ) -> CommandResult:
        cmd = [
            "wsl.exe", "-d", self.distro_name,
            "-u", user, "--",
            "bash", "-c", cmd_str
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout
            )
            stdout = result.stdout.decode("utf-8", errors="replace").replace('\x00', '').strip()
            stderr = result.stderr.decode("utf-8", errors="replace").replace('\x00', '').strip()
            
            return CommandResult(
                success=result.returncode == 0,
                stdout=stdout,
                stderr=stderr,
                return_code=result.returncode
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"Command timed out ({timeout}s)",
                return_code=-1
            )
        except Exception as e:
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1
            )

    def check_distro_exists(self) -> bool:
        result = subprocess.run(
            ["wsl.exe", "-l", "-q"],
            capture_output=True,
            text=True,
            encoding="utf-16-le",
            errors="replace",
            timeout=30
        )
        
        if result.returncode != 0:
            return False
        
        distros = result.stdout.replace('\x00', '').strip().split('\n')
        distros = [d.strip() for d in distros if d.strip()]
        
        return self.distro_name in distros

    def configure(self) -> Tuple[bool, str]:
        print(f"\n{'='*60}")
        print(f"开始配置分发: {self.distro_name}")
        print(f"{'='*60}\n")
        
        if not self.check_distro_exists():
            return False, f"分发 '{self.distro_name}' 不存在"
        
        print("\n[步骤 1/3] 环境准备...")
        success, message = self._step1_environment()
        if not success:
            return False, f"环境准备失败: {message}"
        
        print("\n[步骤 2/3] 安装 Python 3.11+...")
        success, message = self._step2_python()
        if not success:
            return False, f"Python 安装失败: {message}"
        
        print("\n[步骤 3/3] 安装 nanobot...")
        success, message = self._step3_nanobot()
        if not success:
            return False, f"nanobot 安装失败: {message}"
        
        print(f"\n{'='*60}")
        print(f"✓ 配置完成！分发 '{self.distro_name}' 已就绪")
        print(f"{'='*60}\n")
        
        return True, "配置完成"

    def _step1_environment(self) -> Tuple[bool, str]:
        print("  [1.1] 配置国内 apt 源（阿里云镜像）...")
        cmd_str = f'''cp /etc/apt/sources.list /etc/apt/sources.list.bak 2>/dev/null; cat > /etc/apt/sources.list << 'EOF'
{self.APT_SOURCES}
EOF'''
        result = self._run_command(cmd_str, 30)
        if not result.success:
            print(f"        [WARN] apt 源配置警告: {result.stderr}")
        print("        [OK]")
        
        print("  [1.2] 更新 apt 源...")
        result = self._run_command("apt update && apt upgrade -y", 300)
        if not result.success:
            return False, result.stderr
        print("        [OK]")
        
        print("  [1.3] 安装基础工具...")
        packages = "curl wget git software-properties-common build-essential"
        result = self._run_command(f"apt install -y {packages}", 300)
        if not result.success:
            return False, result.stderr
        print("        [OK]")
        
        return True, "环境准备完成"

    def _step2_python(self) -> Tuple[bool, str]:
        print("  [2.1] 添加 deadsnakes PPA...")
        result = self._run_command(
            "add-apt-repository -y ppa:deadsnakes/ppa && apt update", 120
        )
        if not result.success:
            return False, result.stderr
        print("        [OK]")
        
        print("  [2.2] 安装 Python 3.11...")
        packages = "python3.11 python3.11-venv python3.11-dev python3-pip"
        result = self._run_command(f"apt install -y {packages}", 300)
        if not result.success:
            return False, result.stderr
        print("        [OK]")
        
        print("  [2.3] 设置 Python 3.11 为默认...")
        self._run_command(
            "update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1"
        )
        self._run_command(
            "update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1"
        )
        print("        [OK]")
        
        print("  [2.4] 配置 pip 国内镜像（清华大学）...")
        cmd_str = f'''mkdir -p ~/.pip && cat > ~/.pip/pip.conf << 'EOF'
{self.PIP_CONF}
EOF'''
        self._run_command(cmd_str, 30)
        print("        [OK]")
        
        print("  [2.5] 升级 pip...")
        result = self._run_command("python3.11 -m pip install --upgrade pip", 120)
        if not result.success:
            print(f"        [WARN] pip 升级警告: {result.stderr}")
        else:
            print("        [OK]")
        
        print("  [2.6] 验证 Python 安装...")
        result = self._run_command("python3 --version", 10)
        if result.success:
            print(f"        [OK] {result.stdout}")
        else:
            return False, "Python 版本验证失败"
        
        return True, "Python 安装完成"

    def _step3_nanobot(self) -> Tuple[bool, str]:
        print("  [3.1] 安装 nanobot...")
        
        installed = False
        last_error = ""
        for mirror in self.PIP_MIRRORS:
            print(f"        尝试镜像: {mirror}")
            result = self._run_command(
                f"pip install -i {mirror} nanobot-ai", 300
            )
            if result.success:
                print("        [OK]")
                installed = True
                break
            else:
                last_error = result.stderr
                print(f"        [WARN] 失败，尝试下一个镜像...")
        
        if not installed:
            return False, f"所有镜像都失败: {last_error}"
        
        print("  [3.2] 验证 nanobot 安装...")
        result = self._run_command("nanobot --version", 10)
        if result.success:
            print(f"        [OK] {result.stdout}")
        else:
            print("        [WARN] nanobot --version 失败")
        
        print("  [3.3] 初始化 nanobot 配置...")
        result = self._run_command("nanobot onboard", 60)
        if result.success:
            print("        [OK]")
        else:
            print(f"        [WARN] onboard 警告: {result.stderr}")
        
        return True, "nanobot 安装完成"

    def write_config(
        self, 
        api_key: str, 
        model: str = "qwen-portal/coder-model",
        port: int = 18790
    ) -> Tuple[bool, str]:
        config = {
            "providers": {
                "qwen_portal": {
                    "apiKey": api_key
                }
            },
            "agents": {
                "defaults": {
                    "model": model
                }
            },
            "gateway": {
                "host": "0.0.0.0",
                "port": port
            }
        }
        
        config_json = json.dumps(config, indent=2, ensure_ascii=False)
        cmd_str = f'''mkdir -p ~/.nanobot && cat > ~/.nanobot/config.json << 'EOF'
{config_json}
EOF'''
        
        result = self._run_command(cmd_str, 30)
        if result.success:
            logger.success("配置写入成功")
            return True, "配置写入成功"
        
        return False, f"配置写入失败: {result.stderr}"

    def verify_installation(self) -> Tuple[bool, dict]:
        results = {
            "python_version": None,
            "pip_version": None,
            "nanobot_version": None,
            "config_exists": False
        }
        
        result = self._run_command("python3 --version", 10)
        if result.success:
            results["python_version"] = result.stdout
        
        result = self._run_command("pip --version", 10)
        if result.success:
            results["pip_version"] = result.stdout
        
        result = self._run_command("nanobot --version", 10)
        if result.success:
            results["nanobot_version"] = result.stdout
        
        result = self._run_command("test -f ~/.nanobot/config.json && echo 'exists'", 10)
        results["config_exists"] = result.success and "exists" in result.stdout
        
        all_ok = (
            results["python_version"] is not None and
            results["nanobot_version"] is not None
        )
        
        return all_ok, results


def main():
    parser = argparse.ArgumentParser(
        description="Ubuntu 分发一键配置 Nanobot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s Ubuntu-22.04
  %(prog)s Ubuntu-22.04 --api-key YOUR_KEY
  %(prog)s Ubuntu-22.04 --api-key YOUR_KEY --model qwen-portal/coder-model
  %(prog)s Ubuntu-22.04 --verify-only
        """
    )
    
    parser.add_argument(
        "distro_name",
        nargs="?",
        default="Ubuntu-22.04",
        help="WSL 分发名称 (默认: Ubuntu-22.04)"
    )
    
    parser.add_argument(
        "--api-key",
        dest="api_key",
        help="OpenRouter API Key"
    )
    
    parser.add_argument(
        "--model",
        default="qwen-portal/coder-model",
        help="默认模型 (默认: qwen-portal/coder-model)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=18790,
        help="Gateway 端口 (默认: 18790)"
    )
    
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="仅验证安装，不执行配置"
    )
    
    args = parser.parse_args()
    
    if not HAS_LOGURU:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s"
        )
    
    configurator = NanobotDistroConfigurator(args.distro_name)
    
    if args.verify_only:
        success, results = configurator.verify_installation()
        print("\n验证结果:")
        print(f"  Python 版本: {results['python_version'] or '未安装'}")
        print(f"  pip 版本: {results['pip_version'] or '未安装'}")
        print(f"  nanobot 版本: {results['nanobot_version'] or '未安装'}")
        print(f"  配置文件: {'存在' if results['config_exists'] else '不存在'}")
        sys.exit(0 if success else 1)
    
    success, message = configurator.configure()
    
    if not success:
        print(f"\n配置失败: {message}")
        sys.exit(1)
    
    if args.api_key:
        print("\n写入 API 配置...")
        success, message = configurator.write_config(
            api_key=args.api_key,
            model=args.model,
            port=args.port
        )
        if not success:
            print(f"配置写入失败: {message}")
            sys.exit(1)
    else:
        print("\n提示: 请使用以下命令写入 API 配置:")
        print(f"  python {sys.argv[0]} {args.distro_name} --api-key YOUR_KEY")
    
    print("\n验证安装...")
    success, results = configurator.verify_installation()
    print(f"  Python 版本: {results['python_version'] or '未安装'}")
    print(f"  nanobot 版本: {results['nanobot_version'] or '未安装'}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
