@echo off
REM Smart Traffic Control System - Startup Script
REM For Windows

echo.
echo 🚦 Starting Smart Traffic Control System...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH!
    echo    Please install Python 3.9 or higher
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv\" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if dependencies are installed
if not exist "venv\installed" (
    echo 📥 Installing dependencies...
    pip install -r requirements.txt
    echo. > venv\installed
) else (
    echo ✅ Dependencies already installed
)

echo.
echo 🚀 Launching system...
echo.

REM Run the system
python main.py

REM Deactivate on exit
call venv\Scripts\deactivate.bat

pause
