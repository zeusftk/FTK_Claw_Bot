@echo off
setlocal enabledelayedexpansion

REM Disable MSYS2 path conversion for arguments
set MSYS2_ARG_CONV_EXCL=*

REM ============================================================
REM OpenCode Router WSL Uninstaller (All Distributions)
REM Find all running WSL distributions and their services
REM ============================================================

echo.
echo ============================================================
echo    OpenCode Router WSL Uninstaller (All Distributions)
echo ============================================================
echo.

REM Get all running WSL distributions - query each known distro
echo [1/4] Finding running WSL distributions...
echo.

set "DISTRO_COUNT=0"
set "KNOWN_DISTROS=clawbot_1 clawbot_2 clawbot_3 clawbot_4 clawbot_5 Ubuntu Debian"

for %%d in (!KNOWN_DISTROS!) do (
    wsl -d %%d -- echo test >nul 2>&1
    if !errorlevel!==0 (
        set /a DISTRO_COUNT+=1
        set "DISTRO_NAME[!DISTRO_COUNT!]=%%d"
    )
)

if %DISTRO_COUNT%==0 (
    echo [INFO] No running WSL distributions found
    exit /b 0
)

echo Found %DISTRO_COUNT% running distribution(s):
echo.

REM Find services in each distribution
set "TOTAL_SERVICES=0"

for /l %%i in (1,1,%DISTRO_COUNT%) do (
    set "D=!DISTRO_NAME[%%i]!"
    echo [%%i] !D!
    
    REM Get service name using for loop with glob
    for /f "tokens=*" %%a in ('wsl -d !D! -- ls /etc/systemd/system/opencode-router-*.service 2^>nul') do (
        set "FULLPATH=%%a"
        REM Extract port from filename: opencode-router-8000.service -> 8000
        set "FILENAME=!FULLPATH:/etc/systemd/system/=!"
        set "FILENAME=!FILENAME:.service=!"
        set "PORT=!FILENAME:opencode-router-=!"
        
        if defined PORT (
            set /a TOTAL_SERVICES+=1
            set "SERVICE_DISTRO[!TOTAL_SERVICES!]=!D!"
            set "SERVICE_NAME[!TOTAL_SERVICES!]=opencode-router-!PORT!"
            set "SERVICE_PORT[!TOTAL_SERVICES!]=!PORT!"
            
            REM Get opencode port
            set "OC_PORT=?"
            for /f "tokens=4" %%x in ('wsl -d !D! -- grep "ExecStart" /etc/systemd/system/opencode-router-!PORT!.service 2^>nul') do (
                set "OC_PORT=%%x"
            )
            set "OPENCODE_PORT[!TOTAL_SERVICES!]=!OC_PORT!"
        )
    )
)

echo.
if %TOTAL_SERVICES%==0 (
    echo [INFO] No opencode-router services found in any distribution
    exit /b 0
)

echo ============================================================
echo Found %TOTAL_SERVICES% service(s) across all distributions:
echo.
echo   #   Distribution          Router Port    OpenCode Port
echo   --- -------------------- ------------- ---------------
for /l %%i in (1,1,!TOTAL_SERVICES!) do (
    set "DM=!SERVICE_DISTRO[%%i]!"
    set "RP=!SERVICE_PORT[%%i]!"
    set "OP=!OPENCODE_PORT[%%i]!"
    echo   %%i  !DM!             !RP!            !OP!
)
echo.

REM Check for /force flag
set "FORCE=0"
if /i "%~1"=="/force" set "FORCE=1"

REM Select services to uninstall
if %FORCE%==1 (
    set "SELECTION=all"
) else (
    set /p "SELECTION=Enter service numbers to uninstall (comma separated, 'all', or press Enter for all): "
)

if "!SELECTION!"=="" set "SELECTION=all"

echo.

REM Confirm uninstallation
if %FORCE%==1 (
    set "CONFIRM=Y"
) else (
    set /p "CONFIRM=Confirm uninstallation? [y/N]: "
)

if /i not "!CONFIRM!"=="Y" if /i not "!CONFIRM!"=="y" (
    echo Uninstallation cancelled
    exit /b 0
)

REM Uninstall services
echo.
echo [2/4] Uninstalling services...
echo.

if /i "%SELECTION%"=="all" (
    for /l %%i in (1,1,!TOTAL_SERVICES!) do (
        call :uninstall_service !SERVICE_DISTRO[%%i]! !SERVICE_NAME[%%i]! !SERVICE_PORT[%%i]!
    )
) else (
    for %%s in (!SELECTION!) do (
        call :uninstall_service !SERVICE_DISTRO[%%s]! !SERVICE_NAME[%%s]! !SERVICE_PORT[%%s]!
    )
)

REM Reload systemd for each distro
echo [3/4] Reloading systemd...
for /l %%i in (1,1,%DISTRO_COUNT%) do (
    wsl -d !DISTRO_NAME[%%i]! -- systemctl daemon-reload 2>nul
)

echo.
echo ============================================================
echo                    Uninstallation Complete
echo ============================================================
echo.

exit /b 0

:uninstall_service
set "DISTRO=%~1"
set "SVC=%~2"
set "PORT=%~3"

if not defined SVC (
    echo [ERROR] Invalid service selection
    exit /b 1
)

echo [%SVC% on %DISTRO%]
echo   Stopping service...
wsl -d %DISTRO% -- systemctl stop %SVC% 2>nul
wsl -d %DISTRO% -- systemctl disable %SVC% 2>nul
echo   Removing service file...
wsl -d %DISTRO% -- rm -f /etc/systemd/system/%SVC%.service 2>nul
echo   Removing installation directory...
wsl -d %DISTRO% -- rm -rf /opt/opencode_router_%PORT% 2>nul
echo.
exit /b 0
