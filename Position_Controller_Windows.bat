@echo off
setlocal

REM ##################################################################################################
REM Launch Position Controller on Windows with a project-local uv installation and Python environment.
REM ##################################################################################################

REM --------------------------------------------------------------------------------------------------
REM Paths
REM --------------------------------------------------------------------------------------------------
set "SCRIPT_DIR=%~dp0"
set "APP_DIR=%SCRIPT_DIR%app"
set "UV_DIR=%APP_DIR%\.uv"
set "UV_BIN=%UV_DIR%\uv.exe"
set "UV_CACHE_DIR=%UV_DIR%\cache"
set "UV_PYTHON_INSTALL_DIR=%UV_DIR%\python"
set "UV_PROJECT_ENVIRONMENT=%UV_DIR%\venv"
set "MAIN_FILE=%APP_DIR%\main.py"
set "RELEASE_MODULE=scripts.create_release"
cd /d "%APP_DIR%"

REM --------------------------------------------------------------------------------------------------
REM Constants
REM --------------------------------------------------------------------------------------------------
set "RESTART_EXIT_CODE=42"

REM --------------------------------------------------------------------------------------------------
REM uv installation
REM --------------------------------------------------------------------------------------------------
if not exist "%UV_BIN%" (
    mkdir "%UV_DIR%" 2>nul
    set "UV_INSTALL_DIR=%UV_DIR%"
    set "INSTALLER_NO_MODIFY_PATH=1"
    echo Installing uv...
    powershell -ExecutionPolicy ByPass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if errorlevel 1 (
        echo Failed to install uv.
        pause
        exit /b 1
    )
)

REM --------------------------------------------------------------------------------------------------
REM Developer release
REM --------------------------------------------------------------------------------------------------
if /I "%~1"=="release" goto release
goto launch
:release
"%UV_BIN%" run python -m "%RELEASE_MODULE%"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%

REM --------------------------------------------------------------------------------------------------
REM Application launch and restart
REM --------------------------------------------------------------------------------------------------
:launch
"%UV_BIN%" run python "%MAIN_FILE%"
set "EXIT_CODE=%ERRORLEVEL%"
if "%EXIT_CODE%"=="%RESTART_EXIT_CODE%" (
    echo Restarting Position Controller...
    goto launch
)
if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%
