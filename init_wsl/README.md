# WSL 分发初始化脚本

本目录包含一键配置 WSL 分发为 nanobot 运行环境的脚本。

## 前置条件

- 已安装 WSL2
- 有一个可用的 Ubuntu 分发（如 Ubuntu-22.04）

## 使用方法

1. **进入 init_wsl 目录**：
   ```bash
   cd init_wsl
   ```

2. **运行配置脚本**：
   ```bash
   # 交互式模式（会提示选择分发和 wheel 文件）
   make_nanobot_distro.bat
   
   # 指定分发名称
   make_nanobot_distro.bat Ubuntu-22.04
   
   # 指定分发和 wheel 文件
   make_nanobot_distro.bat Ubuntu-22.04 --whl nanobot-0.1.0.2-py3-none-any.whl
   ```

3. **仅验证安装**：
   ```bash
   make_nanobot_distro.bat Ubuntu-22.04 --verify-only
   ```

## 脚本功能

该脚本会自动完成以下配置：

| 步骤 | 功能 |
|------|------|
| Step 1 | 环境设置（apt 源配置、基础工具安装） |
| Step 2 | 安装 Python 3.11+ |
| Step 3 | 安装 nanobot（从本地 wheel 文件） |
| Step 4 | 安装 OpenCode（可选） |
| Step 5 | 配置 nanobot systemd 服务 |

## 可选参数

| 参数 | 说明 |
|------|------|
| `--whl FILE` | 指定 nanobot wheel 文件名 |
| `--verify-only` | 仅验证现有安装 |
| `--skip-mirror` | 跳过镜像源配置 |
| `--no-opencode` | 跳过 OpenCode 安装 |
| `--help, -h` | 显示帮助信息 |

## 服务管理

配置完成后，可以使用以下命令管理 nanobot 服务：

```bash
# 启动服务
wsl -d Ubuntu-22.04 -u root -- systemctl start nanobot

# 停止服务
wsl -d Ubuntu-22.04 -u root -- systemctl stop nanobot

# 查看状态
wsl -d Ubuntu-22.04 -u root -- systemctl status nanobot

# 查看日志
wsl -d Ubuntu-22.04 -u root -- journalctl -u nanobot -f
```

## 目录内容

| 文件 | 说明 |
|------|------|
| `make_nanobot_distro.bat` | 主配置脚本 |
| `nanobot-*.whl` | nanobot wheel 安装包 |
