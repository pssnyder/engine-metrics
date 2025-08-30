@echo off
echo Starting Streamlit Dashboard...

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if Streamlit is installed
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo Streamlit is not installed. Installing...
    pip install streamlit plotly
)

REM Set up the environment
set PYTHONPATH=%~dp0

REM Navigate to the dashboard directory
cd /d "%~dp0dashboard"

REM Start the Streamlit dashboard
echo Starting Streamlit dashboard...
echo Dashboard will be available at http://localhost:8501
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0

pause
