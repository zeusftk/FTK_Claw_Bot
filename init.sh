#!/bin/bash
# FTK_Claw_Bot 开发环境初始化脚本

set -e

echo "=== FTK_Claw_Bot 开发环境初始化 ==="

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "检测到 Python 版本: $python_version"

# 安装依赖
echo "正在安装依赖..."
cd "$(dirname "$0")"

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "警告: requirements.txt 不存在"
fi

# 检查 PyQt6
echo "检查 PyQt6..."
python3 -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')" || {
    echo "错误: PyQt6 未正确安装"
    exit 1
}

# 检查 WSL2
echo "检查 WSL2..."
if command -v wsl.exe &> /dev/null; then
    wsl.exe --list --verbose || true
else
    echo "警告: wsl.exe 不可用"
fi

# 运行基本测试
echo "运行基本测试..."
python3 -c "
from ftk_claw_bot.models import WSLDistro, DistroStatus, NanobotConfig
from ftk_claw_bot.core import WSLManager, ConfigManager
print('核心模块导入成功')
"

echo "=== 初始化完成 ==="
echo "运行 'python -m ftk_claw_bot.main' 启动应用"
