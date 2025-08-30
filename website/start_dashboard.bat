@echo off
title Chess Engine Tournament Dashboard
color 0B

cls
echo.
echo  ===============================================
echo   Chess Engine Tournament Monitor v2.0
echo   Streamlit Dashboard
echo  ===============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if Streamlit is installed
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Streamlit is not installed. Installing...
    pip install streamlit plotly
)

echo Starting Streamlit dashboard...
echo.
echo The dashboard will be available at:
echo - Local:   http://localhost:8501
echo.
echo Press Ctrl+C to stop the dashboard
echo.

REM Start from project root
cd /d "%~dp0"
streamlit run dashboard\streamlit_app.py --server.port 8501 --server.address localhost

echo.
echo Dashboard stopped.
pause
