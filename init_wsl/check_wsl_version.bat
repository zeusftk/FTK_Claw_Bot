@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo WSL Version Check Tool
echo ==================================================
echo.

:: Check admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    set "HAS_ADMIN=0"
) else (
    set "HAS_ADMIN=1"
)

:: [1] Check WSL version
echo [1] Checking WSL version...
wsl --version >nul 2>&1
if %errorlevel% equ 0 (
    echo     [OK] WSL is working
    echo.
    echo     WSL Version Info:
    wsl --version
    echo.

    :: Show installed distros
    echo [2] Installed WSL distributions:
    wsl -l -v
    echo.
    echo ==================================================
    echo.
    echo Done! Press any key to exit...
    pause >nul
    exit /b 0
)

:: wsl --version not available
echo     [X] WSL version is old or not enabled
echo.

:: Check admin privileges
if %HAS_ADMIN% equ 0 (
    echo ==================================================
    echo [WARNING] Admin privileges required to enable WSL
    echo Please run this script as Administrator
    echo ==================================================
    pause
    exit /b 1
)

:: [2] Enable WSL features
echo [2] Enabling WSL features...
echo.

:: Enable VirtualMachinePlatform
echo   Enabling VirtualMachinePlatform...
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Success
) else (
    echo   [X] Failed
    goto :enable_failed
)

:: Enable Subsystem-Linux
echo   Enabling Subsystem-Linux...
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Success
) else (
    echo   [X] Failed
    goto :enable_failed
)

:: Set default version to 2
echo.
echo Setting WSL default version to 2...
wsl --set-default-version 2 >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Success
) else (
    echo   [X] Failed
)

:: Prompt for restart
echo.
echo ==================================================
echo [WARNING] Please restart your computer for changes to take effect!
echo Run this script again after restart to verify WSL.
echo ==================================================
echo.
pause
exit /b 0

:enable_failed
echo.
echo Failed to enable features. Please run manually:
echo   dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
echo   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
echo.
pause
exit /b 1
