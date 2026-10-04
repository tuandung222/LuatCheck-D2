@echo off
rem ==============================================================================
rem One-Click Launch Script for Windows 10/11
rem ==============================================================================

setlocal enabledelayedexpansion
title LuatCheck - Local SLM CPU Assistant

echo ==================================================================
echo  Starting LuatCheck - Local SLM CPU Assistant on Windows
echo ==================================================================

rem 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python is not installed or not in PATH!
        echo Please install Python 3.11+ from https://www.python.org/
        echo Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py
    )
) else (
    set PYTHON_CMD=python
)

echo [OK] Using Python: %PYTHON_CMD%

rem 2. Check Virtual Environment
if not exist "venv\" (
    echo [INFO] Creating virtual environment in .\venv...
    %PYTHON_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
    echo [INFO] Installing required dependencies...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install requirements!
        pause
        exit /b 1
    )
) else (
    call venv\Scripts\activate.bat
)

rem 3. Launch Streamlit UI
echo.
echo ==================================================================
echo [INFO] Launching LuatCheck Web UI on http://localhost:8501...
echo [INFO] Press Ctrl+C in this console window to stop the server.
echo ==================================================================
echo.

streamlit run src\ui\app.py --server.port=8501 --server.address=127.0.0.1 --browser.gatherUsageStats=false

pause
