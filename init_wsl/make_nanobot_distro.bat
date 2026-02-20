@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Ubuntu Distro One-Click Configure Nanobot + OpenCode
REM Configure a clean Ubuntu distro for nanobot runtime
REM ============================================================

set "DISTRO_NAME="
set "WHEEL_FILE="
set "VERIFY_ONLY=0"
set "SKIP_MIRROR=0"
set "INSTALL_OPENCODE=1"
set "ERROR_COUNT=0"
set "ERROR_MSG="
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:parse_args
if "%~1"=="" goto detect_wheel
if /i "%~1"=="--whl" (set "WHEEL_FILE=%~2" & shift & shift & goto parse_args)
if /i "%~1"=="--verify-only" (set "VERIFY_ONLY=1" & shift & goto parse_args)
if /i "%~1"=="--skip-mirror" (set "SKIP_MIRROR=1" & shift & goto parse_args)
if /i "%~1"=="--no-opencode" (set "INSTALL_OPENCODE=0" & shift & goto parse_args)
if /i "%~1"=="--help" goto show_help
if /i "%~1"=="-h" goto show_help
if not "%~1"=="" (set "DISTRO_NAME=%~1" & shift & goto parse_args)
goto detect_wheel

:detect_wheel
REM Auto-detect whl files in script directory
if defined WHEEL_FILE goto check_distro

echo.
echo Scanning for nanobot wheel files in: %SCRIPT_DIR%
echo ------------------------------------------------

set "WHEEL_COUNT=0"
set "WHEEL_LIST="

for %%f in ("%SCRIPT_DIR%\nanobot*.whl") do (
    set /a WHEEL_COUNT+=1
    set "WHEEL_!WHEEL_COUNT!=%%~nxf"
    echo   [!WHEEL_COUNT!] %%~nxf
    set "WHEEL_LIST=!WHEEL_LIST!%%~nxf "
)

if !WHEEL_COUNT! equ 0 (
    echo.
    echo [ERROR] No nanobot*.whl files found in script directory.
    echo        Please place a nanobot wheel file in: %SCRIPT_DIR%
    echo        Or use --whl option to specify the wheel file.
    set "ERROR_COUNT=1"
    goto end
)

if !WHEEL_COUNT! equ 1 (
    set "WHEEL_FILE=!WHEEL_1!"
    echo.
    echo Auto-selected: !WHEEL_FILE!
    goto check_distro
)

echo.
set /p "WHEEL_CHOICE=Select wheel file [1-!WHEEL_COUNT!]: "

if "!WHEEL_CHOICE!" geq "1" if "!WHEEL_CHOICE!" leq "!WHEEL_COUNT!" (
    set "WHEEL_FILE=!WHEEL_%WHEEL_CHOICE%!"
    echo Selected: !WHEEL_FILE!
) else (
    echo [ERROR] Invalid selection.
    set "ERROR_COUNT=1"
    goto end
)

:check_distro
if defined DISTRO_NAME goto main

echo.
echo Available WSL distros:
echo ----------------------
wsl -l -v
echo.
set /p "DISTRO_NAME=Enter distro name (or press Enter to exit): "

if not defined DISTRO_NAME (
    echo.
    echo [ERROR] No distro name provided.
    set "ERROR_COUNT=1"
    goto end
)

:main
if "%VERIFY_ONLY%"=="1" goto verify_only

echo.
echo ============================================================
echo Configuring distro: %DISTRO_NAME%
echo ============================================================
echo.

REM Check if distro exists
echo [Check] Verifying distro exists...
wsl -d %DISTRO_NAME% -u root -- echo test >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Distro '%DISTRO_NAME%' not found
    echo.
    echo Available distros:
    wsl -l -v
    set "ERROR_COUNT=1"
    goto end
)
echo        [OK] Distro exists

REM ============================================================
REM Step 1: Environment Setup
REM ============================================================
echo.
echo [Step 1/5] Environment Setup...

if "%SKIP_MIRROR%"=="0" (
    echo   [1.1] Test mirror availability...
    wsl -d %DISTRO_NAME% -u root -- bash -c "curl -s --connect-timeout 5 -o /dev/null -w '%%{http_code}' http://mirrors.aliyun.com/ubuntu/dists/jammy/InRelease 2>/dev/null | grep -q '200' && echo OK || echo FAIL" 2>nul | findstr "OK" >nul
    if errorlevel 1 (
        echo        [WARN] Aliyun mirror unavailable, using default...
        wsl -d %DISTRO_NAME% -u root -- bash -c "cp /etc/apt/sources.list /etc/apt/sources.list.bak 2>/dev/null || true"
        wsl -d %DISTRO_NAME% -u root -- bash -c "printf 'deb http://archive.ubuntu.com/ubuntu/ jammy main restricted universe multiverse\ndeb http://archive.ubuntu.com/ubuntu/ jammy-updates main restricted universe multiverse\ndeb http://archive.ubuntu.com/ubuntu/ jammy-backports main restricted universe multiverse\ndeb http://security.ubuntu.com/ubuntu/ jammy-security main restricted universe multiverse\n' > /etc/apt/sources.list"
    ) else (
        echo        [OK] Using Aliyun mirror
        wsl -d %DISTRO_NAME% -u root -- bash -c "cp /etc/apt/sources.list /etc/apt/sources.list.bak 2>/dev/null || true"
        wsl -d %DISTRO_NAME% -u root -- bash -c "printf 'deb http://mirrors.aliyun.com/ubuntu/ jammy main restricted universe multiverse\ndeb http://mirrors.aliyun.com/ubuntu/ jammy-updates main restricted universe multiverse\ndeb http://mirrors.aliyun.com/ubuntu/ jammy-backports main restricted universe multiverse\ndeb http://mirrors.aliyun.com/ubuntu/ jammy-security main restricted universe multiverse\n' > /etc/apt/sources.list"
    )
) else (
    echo   [1.1] Skipping mirror configuration...
)

echo   [1.2] Update apt...
wsl -d %DISTRO_NAME% -u root -- bash -c "apt update 2>/dev/null || apt update -o Acquire::Check-Valid-Until=false"
wsl -d %DISTRO_NAME% -u root -- bash -c "apt upgrade -y"
if errorlevel 1 (
    echo        [WARN] apt upgrade had issues, continuing...
)
echo        [OK]

echo   [1.3] Install basic tools...
wsl -d %DISTRO_NAME% -u root -- bash -c "apt install -y curl wget git software-properties-common build-essential"
if errorlevel 1 (
    echo        [ERROR] Basic tools install failed
    set /a ERROR_COUNT+=1
    set "ERROR_MSG=!ERROR_MSG! [1.3] Basic tools install failed"
)
echo        [OK]

REM ============================================================
REM Step 2: Install Python 3.11+
REM ============================================================
echo.
echo [Step 2/5] Install Python 3.11+...

echo   [2.1] Add deadsnakes PPA...
wsl -d %DISTRO_NAME% -u root -- bash -c "add-apt-repository -y ppa:deadsnakes/ppa && apt update"
if errorlevel 1 (
    echo        [ERROR] PPA add failed
    set /a ERROR_COUNT+=1
    set "ERROR_MSG=!ERROR_MSG! [2.1] PPA add failed"
)
echo        [OK]

echo   [2.2] Install Python 3.11...
wsl -d %DISTRO_NAME% -u root -- bash -c "apt install -y python3.11 python3.11-venv python3.11-dev python3-pip"
if errorlevel 1 (
    echo        [ERROR] Python install failed
    set /a ERROR_COUNT+=1
    set "ERROR_MSG=!ERROR_MSG! [2.2] Python install failed"
)
echo        [OK]

echo   [2.3] Configure python to point to 3.11 (keep python3 as 3.10 for apt)...
wsl -d %DISTRO_NAME% -u root -- bash -c "rm -f /usr/bin/python && ln -sf /usr/bin/python3.11 /usr/bin/python"
wsl -d %DISTRO_NAME% -u root -- bash -c "rm -f /usr/bin/pip && ln -sf /usr/local/bin/pip3.11 /usr/bin/pip 2>/dev/null || ln -sf /usr/bin/pip3 /usr/bin/pip"
wsl -d %DISTRO_NAME% -u root -- bash -c "ln /usr/local/bin/pip3.11 /usr/bin/pip3 && ln /usr/bin/python3.11 /usr/bin/python3"
echo        [OK]

echo   [2.4] Install pip for python3.11...
wsl -d %DISTRO_NAME% -u root -- bash -c "python3.11 -m ensurepip --upgrade 2>/dev/null || curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11"
echo        [OK]

echo   [2.5] Configure pip mirror (Tsinghua)...
wsl -d %DISTRO_NAME% -u root -- bash -c "mkdir -p ~/.pip && printf '[global]\nindex-url = https://pypi.tuna.tsinghua.edu.cn/simple\ntrusted-host = pypi.tuna.tsinghua.edu.cn\n' > ~/.pip/pip.conf"
echo        [OK]

echo   [2.6] Upgrade pip...
wsl -d %DISTRO_NAME% -u root -- bash -c "python -m pip install --upgrade pip"
echo        [OK]

echo   [2.7] Verify Python install...
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- python --version 2^>nul`) do set PYTHON_VER=%%i
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- pip --version 2^>nul`) do set PIP_VER=%%i
echo        [OK] %PYTHON_VER%, %PIP_VER%

REM ============================================================
REM Step 3: Install nanobot
REM ============================================================
echo.
echo [Step 3/5] Install nanobot...
echo   Using wheel: %WHEEL_FILE%

echo   [3.1] Copy wheel file to WSL...

REM Convert Windows path to WSL path using wslpath
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- bash -c "wslpath '%SCRIPT_DIR:\=/%'"`) do set "WSL_PATH=%%i"

wsl -d %DISTRO_NAME% -u root -- bash -c "cp '%WSL_PATH%/%WHEEL_FILE%' /tmp/%WHEEL_FILE%"
if errorlevel 1 (
    echo        [ERROR] Failed to copy wheel file from %WSL_PATH%/%WHEEL_FILE%
    set /a ERROR_COUNT+=1
    set "ERROR_MSG=!ERROR_MSG! [3.1] Wheel file copy failed"
)
echo        [OK]

echo   [3.2] Install nanobot from local wheel...
wsl -d %DISTRO_NAME% -u root -- bash -c "pip install /tmp/%WHEEL_FILE%"
if errorlevel 1 (
    echo        [ERROR] Failed to install nanobot
    set /a ERROR_COUNT+=1
    set "ERROR_MSG=!ERROR_MSG! [3.2] Nanobot install failed"
)
echo        [OK]

echo   [3.3] Cleanup wheel file...
wsl -d %DISTRO_NAME% -u root -- bash -c "rm -f /tmp/%WHEEL_FILE%"
echo        [OK]

echo   [3.4] Verify nanobot install...
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- nanobot --version 2^>nul`) do set NANOBOT_VER=%%i
if defined NANOBOT_VER (
    echo        [OK] %NANOBOT_VER%
) else (
    echo        [WARN] nanobot --version failed
)

echo   [3.5] Initialize nanobot config...
wsl -d %DISTRO_NAME% -u root -- nanobot onboard
if not errorlevel 1 (
    echo        [OK]
) else (
    echo        [WARN] onboard warning
)

REM ============================================================
REM Step 4: Install OpenCode (optional)
REM ============================================================
if "%INSTALL_OPENCODE%"=="1" (
    echo.
    echo [Step 4/5] Install OpenCode...

echo   [4.1] Install Node.js 24.x...
wsl -d %DISTRO_NAME% -u root -- bash -c "curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && apt install -y nodejs"
if errorlevel 1 (
    echo        [ERROR] Node.js install failed
    goto skip_opencode
)
echo        [OK]

echo   [4.2] Verify Node.js and npm...
wsl -d %DISTRO_NAME% -u root -- bash -c "echo 'Node.js:' $(node --version 2>/dev/null || echo 'N/A'); echo 'npm:' $(npm --version 2>/dev/null || echo 'N/A')"
echo        [OK]

echo   [4.3] Install opencode globally...
wsl -d %DISTRO_NAME% -u root -- bash -c "npm install -g opencode-ai 2>/dev/null || echo 'npm install failed, trying script'"
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- bash -c "which opencode 2>/dev/null || echo 'not found'"`) do set "OPENCODE_PATH=%%i"
if "%OPENCODE_PATH%"=="not found" (
    echo        [INFO] Installing opencode via official script...
    wsl -d %DISTRO_NAME% -u root -- bash -c "curl -fsSL https://opencode.ai/install | bash"
)

echo   [4.4] Verify opencode install...
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- bash -c "which opencode 2>/dev/null || echo 'not found'"`) do set OPENCODE_PATH=%%i
if "%OPENCODE_PATH%"=="not found" (
    echo        [WARN] opencode not found in PATH
    ) else (
        echo        [OK] %OPENCODE_PATH%
    )
) else (
    echo.
    echo [Step 4/5] Skipping OpenCode installation...
)

:skip_opencode

REM ============================================================
REM Step 5: Setup systemd service for nanobot
REM ============================================================
echo.
echo [Step 5/5] Setup nanobot systemd service...

echo   [5.1] Verify nanobot config exists...
wsl -d %DISTRO_NAME% -u root -- bash -c "test -f /root/.nanobot/config.json && echo 'OK' || echo 'MISSING'" 2>nul | findstr "OK" >nul
if errorlevel 1 (
    echo        [WARN] Config not found, running onboard again...
    wsl -d %DISTRO_NAME% -u root -- nanobot onboard
)
echo        [OK]

echo   [5.2] Create systemd service file...
wsl -d %DISTRO_NAME% -u root -- bash -c "printf '[Unit]\nDescription=Nanobot AI Agent Service\nAfter=network.target\n\n[Service]\nType=simple\nUser=root\nGroup=root\nWorkingDirectory=/root\nEnvironment=PATH=/usr/local/bin:/usr/bin:/bin\nEnvironment=HOME=/root\nExecStart=/usr/bin/python -m nanobot gateway\nRestart=always\nRestartSec=10\nStandardOutput=journal\nStandardError=journal\n\n[Install]\nWantedBy=multi-user.target\n' > /etc/systemd/system/nanobot.service"
if errorlevel 1 (
    echo        [ERROR] Failed to create service file
    set /a ERROR_COUNT+=1
    set "ERROR_MSG=!ERROR_MSG! [5.2] Service file creation failed"
)
echo        [OK]

echo   [5.3] Enable nanobot service...
wsl -d %DISTRO_NAME% -u root -- bash -c "systemctl daemon-reload && systemctl enable nanobot.service"
if errorlevel 1 (
    echo        [WARN] systemctl enable failed (WSL1 may not support systemd fully)
) else (
    echo        [OK]
)

echo   [5.4] Start nanobot service...
wsl -d %DISTRO_NAME% -u root -- bash -c "systemctl start nanobot.service 2>/dev/null || echo 'Service will start on next boot'"
echo        [OK]

REM ============================================================
REM Done
REM ============================================================
echo.
echo ============================================================
echo SUCCESS! Distro '%DISTRO_NAME%' is ready
echo ============================================================
echo.

echo [Verify] Installation status...
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- python --version 2^>nul`) do echo   Python: %%i
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- pip --version 2^>nul`) do echo   pip: %%i
set "NANOBOT_VER="
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- nanobot --version 2^>nul`) do set "NANOBOT_VER=!NANOBOT_VER!%%i"
if defined NANOBOT_VER echo   nanobot: !NANOBOT_VER!
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- bash -c "node --version 2>/dev/null || echo 'N/A'"`) do echo   Node.js: %%i
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- bash -c "npm --version 2>/dev/null || echo 'N/A'"`) do echo   npm: %%i
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- bash -c "which opencode 2>/dev/null || echo 'not installed'"`) do echo   opencode: %%i
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- bash -c "systemctl is-enabled nanobot.service 2>/dev/null || echo 'not enabled'"`) do echo   nanobot.service: %%i

echo.
echo Service management:
echo   Start:   wsl -d %DISTRO_NAME% -u root -- systemctl start nanobot
echo   Stop:    wsl -d %DISTRO_NAME% -u root -- systemctl stop nanobot
echo   Status:  wsl -d %DISTRO_NAME% -u root -- systemctl status nanobot
echo   Logs:    wsl -d %DISTRO_NAME% -u root -- journalctl -u nanobot -f

goto end

REM ============================================================
REM Show help
REM ============================================================
:show_help
echo.
echo Usage: %~nx0 [DISTRO_NAME] [OPTIONS]
echo.
echo Options:
echo   --whl FILE         Nanobot wheel file name (auto-detect if not specified)
echo   --verify-only      Only verify existing installation
echo   --skip-mirror      Skip mirror configuration
echo   --no-opencode      Skip OpenCode installation
echo   --help, -h         Show this help message
echo.
echo Examples:
echo   %~nx0                          Interactive mode
echo   %~nx0 mydistro                 Configure specific distro
echo   %~nx0 mydistro --whl nanobot-1.0.0-py3-none-any.whl
echo.
goto end

REM ============================================================
REM Verify only mode
REM ============================================================
:verify_only
echo.
echo [Verify] Checking installation status...

wsl -d %DISTRO_NAME% -u root -- echo test >nul 2>&1
if errorlevel 1 (
    echo   Distro: Not found
    set "ERROR_COUNT=1"
    goto end
)
echo   Distro: Found

for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- python --version 2^>nul`) do echo   Python: %%i
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- pip --version 2^>nul`) do echo   pip: %%i
set "NANOBOT_VER="
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- nanobot --version 2^>nul`) do set "NANOBOT_VER=!NANOBOT_VER!%%i"
if defined NANOBOT_VER echo   nanobot: !NANOBOT_VER!
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- bash -c "node --version 2>/dev/null || echo 'N/A'"`) do echo   Node.js: %%i
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- bash -c "npm --version 2>/dev/null || echo 'N/A'"`) do echo   npm: %%i
for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- bash -c "which opencode 2>/dev/null || echo 'not installed'"`) do echo   opencode: %%i

wsl -d %DISTRO_NAME% -u root -- bash -c "test -f ~/.nanobot/config.json && echo 'exists'" 2>nul | findstr "exists" >nul
if not errorlevel 1 (
    echo   Config file: Exists
) else (
    echo   Config file: Not found
)

for /f "usebackq delims=" %%i in (`wsl -d %DISTRO_NAME% -u root -- bash -c "systemctl is-active nanobot.service 2>/dev/null || systemctl is-enabled nanobot.service 2>/dev/null || echo 'not configured'"`) do echo   nanobot.service: %%i

goto end

REM ============================================================
REM End - Show summary and pause
REM ============================================================
:end
echo.
echo ============================================================
if !ERROR_COUNT! gtr 0 (
    echo COMPLETED WITH !ERROR_COUNT! ERROR^(S^)
    if defined ERROR_MSG echo Errors:!ERROR_MSG!
) else (
    echo COMPLETED SUCCESSFULLY
)
echo ============================================================
echo.
exit /b !ERROR_COUNT!
