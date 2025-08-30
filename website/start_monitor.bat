@echo off
title Chess Engine Tournament Monitor - Arena Watcher
color 0A

cls
echo.
echo  ===============================================
echo   Chess Engine Tournament Monitor v2.0
echo   Arena File Monitor Service
echo  ===============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Starting Arena monitor service...
echo.
echo This service will:
echo - Watch Arena tournaments directory for new files
echo - Automatically organize and process tournament data
echo - Enable real-time dashboard updates
echo.
echo Press Ctrl+C to stop the service
echo.

REM Set up the environment and start from project root
cd /d "%~dp0"
python services\tournament_monitor.py

echo.
echo Monitor service stopped.
pause
