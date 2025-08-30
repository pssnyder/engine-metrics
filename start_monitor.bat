@echo off
echo Starting Chess Engine Tournament Monitor...

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Set up the environment
set PYTHONPATH=%~dp0

REM Navigate to the services directory
cd /d "%~dp0services"

REM Start the tournament monitor service
echo Starting tournament monitoring service...
python tournament_monitor.py

pause
