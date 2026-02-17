# Nanobot 本地化打包方案

## 一、关键发现：nanobot 是纯 Python 包

通过分析 `pyproject.toml`：
- 使用 `hatchling` 作为构建后端
- 没有 C 扩展、Cython 或 cffi
- whl 文件将是 `py311-none-any.whl` 格式

**结论：可以在 Windows 上构建，在 Linux/WSL 上安装！**

## 二、推荐方案：预构建 whl 文件

### 优势
- **跨平台兼容**：纯 Python 包，一次构建随处安装
- **简单直接**：无需在 WSL 中构建
- **安装快速**：whl 是预打包格式
- **无需网络**：离线安装
- **便于分发**：直接包含在项目中

### 目录结构
```
d:\bot_workspace\FTK_bot\FTK_bot_A\
├── ftk_claw_bot/             # FTK-Claw-Bot 主包
├── packages/            # 本地包目录
│   └── nanobot_ai-0.1.3.post7-py311-none-any.whl
├── make_nanobot_distro.bat
├── build_nanobot_whl.bat
└── ...
```

## 三、实施步骤

### 步骤 1：创建 packages 目录和构建脚本

创建 `build_nanobot_whl.bat`：

```batch
@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Build nanobot whl file
REM ============================================================

set "NANOBOT_SRC=%~dp0..\nanobot"
set "OUTPUT_DIR=%~dp0packages"

echo.
echo ============================================================
echo Building nanobot whl package
echo ============================================================
echo.

REM 检查源码目录
if not exist "%NANOBOT_SRC%\pyproject.toml" (
    echo [ERROR] nanobot source not found at %NANOBOT_SRC%
    echo Please ensure nanobot directory exists
    exit /b 1
)
echo [OK] Found nanobot source

REM 创建输出目录
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM 检查 build 工具
python -c "import build" 2>nul
if errorlevel 1 (
    echo [Install] Installing build tool...
    pip install build
)

REM 构建
echo.
echo [Build] Creating wheel package...
cd /d "%NANOBOT_SRC%"
python -m build --wheel --outdir "%OUTPUT_DIR%"

if errorlevel 1 (
    echo [ERROR] Build failed
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS! whl file created
echo ============================================================
echo.
echo Output directory: %OUTPUT_DIR%
dir "%OUTPUT_DIR%\*.whl"
echo.
exit /b 0
```

### 步骤 2：修改 make_nanobot_distro.bat

将 Step 3 的安装逻辑改为本地 whl 安装：

```batch
REM ============================================================
REM Step 3: Install nanobot from local whl
REM ============================================================
echo.
echo [Step 3/3] Install nanobot from local package...

REM 检查 whl 文件是否存在
set "PKG_DIR=%~dp0packages"
set "WHL_FOUND=0"
for %%f in ("%PKG_DIR%\nanobot_ai-*.whl") do (
    set "WHL_FILE=%%f"
    set "WHL_FOUND=1"
)

if "%WHL_FOUND%"=="0" (
    echo [ERROR] nanobot whl file not found in packages/
    echo Please run build_nanobot_whl.bat first
    exit /b 1
)

echo   [3.1] Found: %WHL_FILE%

REM 转换 Windows 路径到 WSL 路径
for /f "usebackq delims=" %%i in (`wsl wslpath -u "%WHL_FILE%"`) do set "WSL_WHL_PATH=%%i"

echo   [3.2] Installing nanobot from local whl...
wsl -d %DISTRO_NAME% -u root -- bash -c "pip install '%WSL_WHL_PATH%'"
if errorlevel 1 (
    echo        [ERROR] nanobot install failed
    exit /b 1
)
echo        [OK]

echo   [3.3] Verify nanobot install...
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -- nanobot --version 2^>nul`) do set NANOBOT_VER=%%i
if defined NANOBOT_VER (
    echo        [OK] !NANOBOT_VER!
) else (
    echo        [WARN] nanobot --version failed
)

echo   [3.4] Initialize nanobot config...
wsl -d %DISTRO_NAME% -- nanobot onboard >nul 2>&1
if not errorlevel 1 (
    echo        [OK]
) else (
    echo        [WARN] onboard warning
)
```

## 四、完整工作流程

### 首次设置
```batch
# 1. 构建 whl 文件
cd d:\bot_workspace\FTK_bot\FTK_bot_A
build_nanobot_whl.bat

# 2. 配置 WSL 分发
make_nanobot_distro.bat Ubuntu-22.04 --api-key YOUR_KEY
```

### 更新 nanobot 版本
```batch
# 1. 更新 nanobot 源码
cd d:\bot_workspace\FTK_bot\nanobot
git pull

# 2. 重新构建 whl
cd d:\bot_workspace\FTK_bot\FTK_bot_A
build_nanobot_whl.bat

# 3. 重新配置 WSL 分发（可选）
make_nanobot_distro.bat Ubuntu-22.04 --api-key YOUR_KEY
```

## 五、关于跨平台兼容性

### 纯 Python 包的特点
- whl 文件名包含 `none-any` 表示平台无关
- 不包含编译的二进制文件
- 可以在任何平台安装

### nanobot 的依赖
nanobot 的依赖（litellm, websockets, pydantic 等）都是纯 Python 或提供预编译 wheel，所以：
- 在 WSL 中 `pip install nanobot.whl` 会自动下载 Linux 版本的依赖
- 不需要在 Linux 下重新构建

## 六、.gitignore 配置

```gitignore
# 可选：排除 whl 文件（开发者自行构建）
# packages/*.whl
```

建议：
- **提交 whl 文件**：用户无需构建，开箱即用
- **排除 whl 文件**：减小仓库体积，开发者自行构建
