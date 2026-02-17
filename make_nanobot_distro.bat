@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Ubuntu Distro One-Click Configure Nanobot
REM Configure a clean Ubuntu distro for nanobot runtime
REM ============================================================

set "DISTRO_NAME=Ubuntu-22.04"
set "API_KEY="
set "MODEL=anthropic/claude-sonnet-4-20250529"
set "PORT=18790"
set "VERIFY_ONLY=0"

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :end_parse
if /i "%~1"=="--api-key" (
    set "API_KEY=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--model" (
    set "MODEL=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--port" (
    set "PORT=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--verify-only" (
    set "VERIFY_ONLY=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="-h" goto :show_help
if not "%~1"=="" (
    set "DISTRO_NAME=%~1"
    shift
    goto :parse_args
)
:end_parse

REM Verify only mode
if "%VERIFY_ONLY%"=="1" goto :verify_only

echo.
echo ============================================================
echo Configuring distro: %DISTRO_NAME%
echo ============================================================
echo.

REM Check if distro exists
echo [Check] Verifying distro exists...
wsl -l -q 2>nul | findstr /i /c:"%DISTRO_NAME%" >nul
if errorlevel 1 (
    echo [ERROR] Distro '%DISTRO_NAME%' not found
    echo.
    echo Available distros:
    wsl -l -q
    exit /b 1
)
echo        [OK] Distro exists

REM ============================================================
REM Step 1: Environment Setup
REM ============================================================
echo.
echo [Step 1/3] Environment Setup...

echo   [1.1] Configure apt mirror (Aliyun)...
wsl -d %DISTRO_NAME% -u root -- bash -c "cp /etc/apt/sources.list /etc/apt/sources.list.bak 2>/dev/null; cat > /etc/apt/sources.list << 'EOF'
deb http://mirrors.aliyun.com/ubuntu/ jammy main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-updates main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-backports main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ jammy-security main restricted universe multiverse
EOF" 2>nul
echo        [OK]

echo   [1.2] Update apt...
wsl -d %DISTRO_NAME% -u root -- bash -c "apt update && apt upgrade -y" >nul 2>&1
if errorlevel 1 (
    echo        [ERROR] apt update failed
    exit /b 1
)
echo        [OK]

echo   [1.3] Install basic tools...
wsl -d %DISTRO_NAME% -u root -- bash -c "apt install -y curl wget git software-properties-common build-essential" >nul 2>&1
if errorlevel 1 (
    echo        [ERROR] Basic tools install failed
    exit /b 1
)
echo        [OK]

REM ============================================================
REM Step 2: Install Python 3.11+
REM ============================================================
echo.
echo [Step 2/3] Install Python 3.11+...

echo   [2.1] Add deadsnakes PPA...
wsl -d %DISTRO_NAME% -u root -- bash -c "add-apt-repository -y ppa:deadsnakes/ppa && apt update" >nul 2>&1
if errorlevel 1 (
    echo        [ERROR] PPA add failed
    exit /b 1
)
echo        [OK]

echo   [2.2] Install Python 3.11...
wsl -d %DISTRO_NAME% -u root -- bash -c "apt install -y python3.11 python3.11-venv python3.11-dev python3-pip" >nul 2>&1
if errorlevel 1 (
    echo        [ERROR] Python install failed
    exit /b 1
)
echo        [OK]

echo   [2.3] Set Python 3.11 as default...
wsl -d %DISTRO_NAME% -u root -- bash -c "update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1" >nul 2>&1
wsl -d %DISTRO_NAME% -u root -- bash -c "update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1" >nul 2>&1
echo        [OK]

echo   [2.4] Configure pip mirror (Tsinghua)...
wsl -d %DISTRO_NAME% -u root -- bash -c "mkdir -p ~/.pip && cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF" >nul 2>&1
echo        [OK]

echo   [2.5] Upgrade pip...
wsl -d %DISTRO_NAME% -u root -- bash -c "python3.11 -m pip install --upgrade pip" >nul 2>&1
echo        [OK]

echo   [2.6] Verify Python install...
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -- python3 --version 2^>nul`) do set PYTHON_VER=%%i
echo        [OK] !PYTHON_VER!

REM ============================================================
REM Step 3: Install nanobot
REM ============================================================
echo.
echo [Step 3/3] Install nanobot...

echo   [3.1] Copy wheel file to WSL...

set "WHEEL_FILE=nanobot-1.0.0+ftk-py3-none-any.whl"
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -- bash -c "echo %SCRIPT_DIR% ^| sed 's|\\\\|/|g' ^| sed 's|^\([A-Za-z]\):|/mnt/\L\1|'"`) do set "WSL_SCRIPT_DIR=%%i"

wsl -d %DISTRO_NAME% -u root -- bash -c "cp '%WSL_SCRIPT_DIR%/%WHEEL_FILE%' /tmp/%WHEEL_FILE%" >nul 2>&1
if errorlevel 1 (
    echo        [ERROR] Failed to copy wheel file
    exit /b 1
)
echo        [OK]

echo   [3.2] Install nanobot from local wheel...
wsl -d %DISTRO_NAME% -u root -- bash -c "pip install /tmp/%WHEEL_FILE%" >nul 2>&1
if errorlevel 1 (
    echo        [ERROR] Failed to install nanobot
    exit /b 1
)
echo        [OK]

echo   [3.3] Cleanup wheel file...
wsl -d %DISTRO_NAME% -u root -- bash -c "rm -f /tmp/%WHEEL_FILE%" >nul 2>&1
echo        [OK]

echo   [3.4] Verify nanobot install...
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -- nanobot --version 2^>nul`) do set NANOBOT_VER=%%i
if defined NANOBOT_VER (
    echo        [OK] !NANOBOT_VER!
) else (
    echo        [WARN] nanobot --version failed
)

echo   [3.5] Initialize nanobot config...
wsl -d %DISTRO_NAME% -- nanobot onboard >nul 2>&1
if not errorlevel 1 (
    echo        [OK]
) else (
    echo        [WARN] onboard warning
)

REM ============================================================
REM Write API config
REM ============================================================
if defined API_KEY (
    echo.
    echo [Config] Writing API config...
    wsl -d %DISTRO_NAME% -u root -- bash -c "mkdir -p ~/.nanobot && cat > ~/.nanobot/config.json << 'EOF'
{
  \"providers\": {
    \"openrouter\": {
      \"apiKey\": \"%API_KEY%\"
    }
  },
  \"agents\": {
    \"defaults\": {
      \"model\": \"%MODEL%\"
    }
  },
  \"gateway\": {
    \"host\": \"0.0.0.0\",
    \"port\": %PORT%
  }
}
EOF" >nul 2>&1
    echo        [OK]
)

REM ============================================================
REM Done
REM ============================================================
echo.
echo ============================================================
echo SUCCESS! Distro '%DISTRO_NAME%' is ready
echo ============================================================
echo.

REM Verify installation
echo [Verify] Installation status...
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -- python3 --version 2^>nul`) do echo   Python: %%i
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -- nanobot --version 2^>nul`) do echo   nanobot: %%i

if not defined API_KEY (
    echo.
    echo Tip: Use the following command to write API config:
    echo   %~nx0 %DISTRO_NAME% --api-key YOUR_KEY
)

exit /b 0

REM ============================================================
REM Verify only mode
REM ============================================================
:verify_only
echo.
echo [Verify] Checking installation status...

wsl -l -q 2>nul | findstr /i /c:"%DISTRO_NAME%" >nul
if errorlevel 1 (
    echo   Distro: Not found
    exit /b 1
)
echo   Distro: Found

for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -- python3 --version 2^>nul`) do echo   Python: %%i
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -- pip --version 2^>nul`) do echo   pip: %%i
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -- nanobot --version 2^>nul`) do echo   nanobot: %%i

wsl -d %DISTRO_NAME% -- bash -c "test -f ~/.nanobot/config.json && echo 'exists'" 2>nul | findstr "exists" >nul
if not errorlevel 1 (
    echo   Config file: Exists
) else (
    echo   Config file: Not found
)

exit /b 0

REM ============================================================
REM Help
REM ============================================================
:show_help
echo.
echo Usage: %~nx0 [distro_name] [options]
echo.
echo Arguments:
echo   distro_name     WSL distro name (default: Ubuntu-22.04)
echo.
echo Options:
echo   --api-key KEY   OpenRouter API Key
echo   --model MODEL   Default model (default: anthropic/claude-sonnet-4-20250529)
echo   --port PORT     Gateway port (default: 18790)
echo   --verify-only   Only verify installation, do not configure
echo   -h, --help      Show this help message
echo.
echo Examples:
echo   %~nx0 Ubuntu-22.04
echo   %~nx0 Ubuntu-22.04 --api-key YOUR_KEY
echo   %~nx0 Ubuntu-22.04 --api-key YOUR_KEY --model anthropic/claude-sonnet-4-20250529
echo   %~nx0 Ubuntu-22.04 --verify-only
echo.
exit /b 0
