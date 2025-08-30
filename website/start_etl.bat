@echo off
title Chess Engine ETL Service
color 0D

cls
echo.
echo  ===============================================
echo   Chess Engine Tournament Monitor v2.0
echo   ETL Service (Background Data Processing)
echo  ===============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Starting ETL service...
echo.
echo The ETL service processes tournament data in the background
echo and feeds it to the backend API for dashboard display.
echo.
echo Press Ctrl+C to stop the service
echo.

REM Start from project root
cd /d "%~dp0"
python services/realtime_etl.py

echo.
echo ETL service stopped.
pause
