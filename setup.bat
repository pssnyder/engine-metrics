@echo off
REM Engine Metrics Dashboard Startup Script for Windows

echo Starting Engine Metrics Dashboard...

REM Check if we're in the correct directory
if not exist "config\settings.yaml" (
    echo Error: Please run this script from the engine-metrics root directory
    pause
    exit /b 1
)

REM Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check for Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Warning: Node.js not found. Frontend development server won't be available.
    set NODE_AVAILABLE=false
) else (
    set NODE_AVAILABLE=true
)

REM Set up Python virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install Python dependencies
echo Installing Python dependencies...
cd backend
pip install -r requirements.txt
cd ..

REM Install Node.js dependencies if Node is available
if "%NODE_AVAILABLE%"=="true" (
    echo Installing Node.js dependencies...
    cd frontend
    call npm install
    cd ..
)

REM Create database directory if it doesn't exist
if not exist "database" mkdir database

echo.
echo Setup complete!
echo.
echo To start the dashboard:
echo 1. Backend only: start-backend.bat
if "%NODE_AVAILABLE%"=="true" (
    echo 2. Development mode (with live reload): start-development.bat
    echo 3. Full production: start-production.bat
) else (
    echo 2. Install Node.js to enable frontend development features
)
echo.
echo The dashboard will be available at: http://localhost:8000
echo.
pause
