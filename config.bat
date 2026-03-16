@echo off
chcp 65001 >nul 2>nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
title AI Stock Report - Settings
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo Python not found! Please install Python 3.10+
        pause
        exit /b 1
    )
    set PY=py
    goto :found
)
set PY=python

:found
echo Opening settings page...
%PY% -c "from web_config import run_config_server; run_config_server(open_browser=True, wait_for_save=True)"

if not exist config.yaml (
    echo Config not saved. Exiting.
    pause
    exit /b 1
)

echo.
echo Config saved. Starting service...
echo.
title AI Stock Report
%PY% app.py
pause
