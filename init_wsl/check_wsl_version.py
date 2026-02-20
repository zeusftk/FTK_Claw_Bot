#!/usr/bin/env python3
"""
检测 Windows 系统 WSL 版本的脚本
支持自动检测旧版本并启用必要功能
"""

import subprocess
import re
import sys


def run_command(cmd):
    """运行命令并返回输出"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), -1


def check_wsl_version_available():
    """检查 wsl --version 命令是否可用"""
    stdout, stderr, returncode = run_command("wsl --version")
    # 新版本返回 0，旧版本返回非 0 或错误信息
    if returncode == 0 and stdout and "无效" not in stderr and "invalid" not in stderr.lower():
        return True, stdout
    return False, stderr


def get_wsl_distributions():
    """获取已安装的 WSL 发行版列表"""
    stdout, stderr, returncode = run_command("wsl -l -v")
    if returncode == 0 and stdout:
        return stdout
    return None


def get_wsl_default_version():
    """获取默认 WSL 版本 (1 或 2)"""
    stdout, stderr, returncode = run_command("wsl --status")
    if returncode == 0:
        match = re.search(r'默认版本[：:]\s*(\d+)', stdout)
        if match:
            return match.group(1)
        match = re.search(r'Default Version[：:]\s*(\d+)', stdout)
        if match:
            return match.group(1)
    return None


def check_admin_privileges():
    """检查是否有管理员权限"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def enable_wsl_features():
    """启用 WSL 相关功能"""
    commands = [
        ("VirtualMachinePlatform", "dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart"),
        ("Subsystem-Linux", "dism.exe /online /enable-feature /featurename=Microsoft-Windows-Subsystem-Linux /all /norestart"),
    ]
    
    print("\n正在启用 WSL 相关功能...")
    for name, cmd in commands:
        print(f"  启用 {name}...")
        stdout, stderr, returncode = run_command(cmd)
        if returncode == 0:
            print(f"  ✓ 成功")
        else:
            print(f"  ✗ 失败: {stderr}")
            return False
    return True


def set_wsl_default_version_2():
    """设置 WSL 默认版本为 2"""
    print("\n设置 WSL 默认版本为 2...")
    stdout, stderr, returncode = run_command("wsl --set-default-version 2")
    if returncode == 0:
        print("  ✓ 成功")
        return True
    else:
        print(f"  ✗ 失败: {stderr}")
        return False


def main():
    print("=" * 50)
    print("WSL 版本检测工具")
    print("=" * 50)
    print()
    
    # 检查 wsl --version 是否可用
    print("[1] 检查 WSL 版本...")
    is_available, output = check_wsl_version_available()
    
    if is_available:
        print("    ✓ WSL 版本正常")
        for line in output.split('\n'):
            if line.strip():
                print(f"    {line.strip()}")
        print()
        
        # 显示发行版列表
        print("[2] 已安装的 WSL 发行版:")
        distros = get_wsl_distributions()
        if distros:
            for line in distros.split('\n'):
                if line.strip():
                    print(f"    {line.strip()}")
        else:
            print("    未找到已安装的发行版")
        
        print()
        print("=" * 50)
        return
    
    # wsl --version 不可用，需要启用功能
    print("    ✗ WSL 版本较旧或功能未启用")
    print()
    
    # 检查管理员权限
    if not check_admin_privileges():
        print("=" * 50)
        print("⚠ 需要管理员权限才能启用 WSL 功能")
        print("请以管理员身份重新运行此脚本")
        print("=" * 50)
        sys.exit(1)
    
    # 执行启用步骤
    print("[2] 启用 WSL 功能...")
    
    # 1. 启用 VirtualMachinePlatform
    # 2. 启用 Microsoft-Windows-Subsystem-Linux
    if not enable_wsl_features():
        print("\n启用功能失败，请手动执行:")
        print("  dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart")
        print("  dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart")
        sys.exit(1)
    
    # 3. 设置默认版本为 2
    set_wsl_default_version_2()
    
    # 4. 提示重启
    print()
    print("=" * 50)
    print("⚠ 请重启电脑以使更改生效！")
    print("重启后再次运行此脚本检查 WSL 版本。")
    print("=" * 50)


if __name__ == "__main__":
    main()