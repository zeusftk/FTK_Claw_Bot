@echo off
setlocal enabledelayedexpansion

REM Disable MSYS2 path conversion for arguments
set MSYS2_ARG_CONV_EXCL=*

REM ============================================================
REM OpenCode Router WSL Systemd Installer
REM Install opencode-router service to WSL distribution systemd
REM ============================================================

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Parse Windows path to WSL path
for %%i in ("%SCRIPT_DIR%") do set "DRIVE_LETTER=%%~di"
set "DRIVE_LETTER=%DRIVE_LETTER:~0,1%"
call :to_lower DRIVE_LETTER
set "WSL_SCRIPT_PATH=/mnt/%DRIVE_LETTER%/%SCRIPT_DIR:~3%"
set "WSL_SCRIPT_PATH=%WSL_SCRIPT_PATH:\=/%"

REM Default ports
set "DEFAULT_OPENCODE_PORT=4096"
set "DEFAULT_ROUTER_PORT=8000"

REM Parse arguments
set "NON_INTERACTIVE=0"
set "FORCE=0"
for %%a in (%*) do (
    if /i "%%a"=="/noninteractive" set "NON_INTERACTIVE=1"
    if /i "%%a"=="/force" set "FORCE=1"
    if /i "%%a"=="/?" goto :show_help
    if /i "%%a"=="-h" goto :show_help
    if /i "%%a"=="--help" goto :show_help
)

echo.
echo ============================================================
echo       OpenCode Router WSL Systemd Installer
echo ============================================================
echo.

REM Check WSL
wsl --status >nul 2>&1
if errorlevel 1 (
    echo [ERROR] WSL not installed or not running
    echo Please install WSL first: wsl --install
    exit /b 1
)

REM Get WSL distribution list
echo [1/6] Detecting WSL distributions...
echo.
echo Available WSL distributions:
echo ---------------------------
wsl -l -v
echo.

set "DISTRO_NAME=clawbot_1"
if not "%NON_INTERACTIVE%"=="1" set /p "DISTRO_NAME=Enter distribution name to install: "

if not defined DISTRO_NAME (
    echo [ERROR] No distribution name provided
    exit /b 1
)

REM Verify distro exists
wsl -d %DISTRO_NAME% -- echo test >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Distribution '%DISTRO_NAME%' not found
    exit /b 1
)

set "SELECTED_INDICES=1"
set "DISTRO_NAME[1]=%DISTRO_NAME%"
set "SELECTED[1]=1"
set "SELECTED_COUNT=1"

REM Collect port configuration for each distribution
echo.
echo [2/6] Configuring ports...
echo.

set "NEXT_OPENCODE_PORT=%DEFAULT_OPENCODE_PORT%"
set "NEXT_ROUTER_PORT=%DEFAULT_ROUTER_PORT%"

REM Get ports for the distribution
call :get_next_available_ports "%DISTRO_NAME%" NEXT_OPENCODE_PORT NEXT_ROUTER_PORT

if "%NON_INTERACTIVE%"=="1" (
    set "OPENCODE_PORT=!NEXT_OPENCODE_PORT!"
    set "ROUTER_PORT=!NEXT_ROUTER_PORT!"
    echo   [%DISTRO_NAME%] opencode_port=!NEXT_OPENCODE_PORT!, router_port=!NEXT_ROUTER_PORT!
) else (
    echo [%DISTRO_NAME%]
    set /p "OPENCODE_PORT_INPUT=  opencode serve port [!NEXT_OPENCODE_PORT!]: "
    if "!OPENCODE_PORT_INPUT!"=="" (
        set "OPENCODE_PORT=!NEXT_OPENCODE_PORT!"
    ) else (
        set "OPENCODE_PORT=!OPENCODE_PORT_INPUT!"
    )
    
    set /p "ROUTER_PORT_INPUT=  router service port [!NEXT_ROUTER_PORT!]: "
    if "!ROUTER_PORT_INPUT!"=="" (
        set "ROUTER_PORT=!NEXT_ROUTER_PORT!"
    ) else (
        set "ROUTER_PORT=!ROUTER_PORT_INPUT!"
    )
    echo.
)

REM Confirm installation plan
echo.
echo [3/6] Confirming installation plan...
echo.
echo Services to be installed:
echo.
echo   Distribution      OpenCode Port  Router Port
echo   --------------------------------------------
echo   %DISTRO_NAME%          %OPENCODE_PORT%             %ROUTER_PORT%
echo.

if "%NON_INTERACTIVE%"=="1" (
    set "CONFIRM=Y"
    echo [Non-interactive mode] Auto-confirming
) else (
    set /p "CONFIRM=Confirm installation? [Y/n]: "
)

if /i not "!CONFIRM!"=="Y" if /i not "!CONFIRM!"=="" (
    echo Installation cancelled
    exit /b 0
)

REM Execute installation
echo.
echo [4/6] Installing...
echo.

set "OC_PORT=%OPENCODE_PORT%"
set "R_PORT=%ROUTER_PORT%"
set "INSTALL_PATH=/opt/opencode_router_%ROUTER_PORT%"
set "SERVICE_NAME=opencode-router-%ROUTER_PORT%"

echo [Installing] %DISTRO_NAME% (opencode_port=%OPENCODE_PORT%, router_port=%ROUTER_PORT%)

REM Check if service already exists
wsl -d "%DISTRO_NAME%" -- systemctl is-enabled %SERVICE_NAME% >nul 2>&1
if !errorlevel!==0 (
    if !FORCE!==0 (
        echo   [Skipped] Service already exists, use /force to overwrite
        goto :install_done
    ) else (
        echo   [Force] Stopping and disabling existing service...
        wsl -d "%DISTRO_NAME%" -- systemctl stop %SERVICE_NAME% >nul 2>&1
        wsl -d "%DISTRO_NAME%" -- systemctl disable %SERVICE_NAME% >nul 2>&1
    )
)

REM Setup Python, create directory, copy files
echo   Setting up environment...
wsl -d %DISTRO_NAME% -- bash -c "ln -sf /usr/bin/python3.11 /usr/bin/python3" 2>nul
wsl -d %DISTRO_NAME% -- mkdir -p %INSTALL_PATH% 2>nul
wsl -d %DISTRO_NAME% -- cp %WSL_SCRIPT_PATH%/router.py %INSTALL_PATH%/router.py 2>nul
wsl -d %DISTRO_NAME% -- chmod 755 %INSTALL_PATH%/router.py 2>nul

REM Generate systemd service file
echo   Generating systemd service file...
call :create_service_file "%DISTRO_NAME%" "%INSTALL_PATH%" "%OPENCODE_PORT%" "%ROUTER_PORT%" "%SERVICE_NAME%"

REM Reload systemd, enable and start service
echo   Enabling and starting service...
wsl -d %DISTRO_NAME% -- systemctl daemon-reload 2>nul
wsl -d %DISTRO_NAME% -- systemctl enable %SERVICE_NAME% 2>nul
wsl -d %DISTRO_NAME% -- systemctl start %SERVICE_NAME% 2>nul

REM Check service status
ping -n 3 127.0.0.1 >nul 2>&1
wsl -d %DISTRO_NAME% -- systemctl is-active %SERVICE_NAME% 2>nul
if errorlevel 1 (
    echo   [Warning] Service may have failed to start, check logs
    wsl -d %DISTRO_NAME% -- journalctl -u %SERVICE_NAME% -n 5 --no-pager 2>nul
) else (
    echo   [Success] Service started
)

:install_done
echo.

REM Show installation results
echo.
echo [5/6] Installation results...
echo.
echo ============================================================
echo                    Installation Complete
echo ============================================================
echo.
echo Service list:
echo   [OK] %DISTRO_NAME%: http://localhost:%ROUTER_PORT%
echo.
echo [6/6] Test commands:
echo   curl http://localhost:%ROUTER_PORT%/health
echo   curl http://localhost:%ROUTER_PORT%/v1/models
echo.
echo Management commands:
echo   View status: status-wsl.bat
echo   View logs:   wsl -d %DISTRO_NAME% -- journalctl -u opencode-router-%ROUTER_PORT% -f
echo   Restart:     wsl -d %DISTRO_NAME% -- systemctl restart opencode-router-%ROUTER_PORT%
echo.

exit /b 0

REM ============================================================
REM Subroutines
REM ============================================================

:show_help
echo.
echo Usage: install-wsl.bat [options]
echo.
echo Options:
echo   /noninteractive  Non-interactive mode, use defaults
echo   /force           Force overwrite existing services
echo   /?               Show help
echo.
echo Examples:
echo   install-wsl.bat
echo   install-wsl.bat /noninteractive
echo   install-wsl.bat /force
echo.
exit /b 0

:to_lower
for %%i in (a b c d e f g h i j k l m n o p q r s t u v w x y z) do (
    call set "%1=%%%1:%%i=%%i%%"
)
exit /b 0

:get_next_available_ports
set "DISTRO=%~1"
set "PORT_VAR1=%~2"
set "PORT_VAR2=%~3"

set "FOUND_OC=!DEFAULT_OPENCODE_PORT!"
set "FOUND_R=!DEFAULT_ROUTER_PORT!"

REM Query installed service ports
for /f "tokens=*" %%s in ('wsl -d "!DISTRO!" -- ls /etc/systemd/system/opencode-router-*.service 2^>nul') do (
    for /f "tokens=2 delims=-" %%p in ("%%s") do (
        set "EXISTING_PORT=%%p"
        set "EXISTING_PORT=!EXISTING_PORT:.service=!"
        if !EXISTING_PORT! geq !FOUND_R! (
            set /a FOUND_R=EXISTING_PORT+1
        )
    )
)

REM Check Windows port usage
:check_port_loop
netstat -ano | findstr ":!FOUND_R! " >nul 2>&1
if not errorlevel 1 (
    set /a FOUND_R+=1
    set /a FOUND_OC+=1
    goto :check_port_loop
)

set "%PORT_VAR1%=!FOUND_OC!"
set "%PORT_VAR2%=!FOUND_R!"
exit /b 0

:create_service_file
set "DISTRO=%~1"
set "INSTALL_PATH=%~2"
set "OC_PORT=%~3"
set "R_PORT=%~4"
set "SERVICE_NAME=%~5"

REM Create temporary service file
set "TEMP_FILE=%TEMP%\opencode-router-service.tmp"

(
echo [Unit]
echo Description=OpenCode Router - %DISTRO%
echo Documentation=https://github.com/opencode-ai/opencode-client
echo After=network.target network-online.target
echo Wants=network-online.target
echo.
echo [Service]
echo Type=simple
echo User=root
echo Group=root
echo WorkingDirectory=%INSTALL_PATH%
echo Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
echo Environment="PYTHONUNBUFFERED=1"
echo ExecStart=/usr/bin/python3 %INSTALL_PATH%/router.py --opencode-port %OC_PORT% --router-port %R_PORT%
echo Restart=always
echo RestartSec=10
echo StartLimitIntervalSec=60
echo StartLimitBurst=5
echo StandardOutput=journal
echo StandardError=journal
echo SyslogIdentifier=opencode-router-%R_PORT%
echo LimitNOFILE=65535
echo.
echo [Install]
echo WantedBy=multi-user.target
) > "%TEMP_FILE%"

REM Copy service file to WSL
type "%TEMP_FILE%" | wsl -d %~1 -- tee /etc/systemd/system/%~5.service >nul 2>&1
del "%TEMP_FILE%" >nul 2>&1
exit /b 0
