@echo off
chcp 65001 >nul 2>nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
title AI Stock Report
cd /d "%~dp0"

:: --- Check Python ---
where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo ============================================
        echo   Python not found!
        echo   Please install Python 3.10+
        echo   https://www.python.org/downloads/
        echo   IMPORTANT: Check "Add Python to PATH"
        echo ============================================
        pause
        exit /b 1
    )
    set PY=py
    goto :found
)
set PY=python

:found

:: --- Install dependencies on first run ---
if not exist .deps_installed (
    echo [1/2] Installing dependencies...
    %PY% -m pip install -r requirements.txt -q
    if errorlevel 1 (
        echo.
        echo Failed to install dependencies. Please check your network.
        pause
        exit /b 1
    )
    echo. > .deps_installed
    echo [1/2] Done.
)

:: --- Launch app (Python handles all UI from here) ---
echo [2/2] Starting...
echo.
%PY% app.py

pause
