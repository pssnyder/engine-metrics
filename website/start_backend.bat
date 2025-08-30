@echo off
title Chess Engine Tournament Backend API
color 0E

cls
echo.
echo  ===============================================
echo   Chess Engine Tournament Monitor v2.0
echo   Backend API Server
echo  ===============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if FastAPI is installed
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] FastAPI is not installed. Installing...
    pip install fastapi uvicorn
)

echo Starting Backend API server...
echo.
echo The API will be available at:
echo - Local:   http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start from backend directory
cd /d "%~dp0\backend"
python app.py

echo.
echo Backend API stopped.
pause
