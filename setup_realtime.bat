@echo off
title Chess Engine Tournament Monitor - First Time Setup
color 0B

echo.
echo  ===============================================
echo   Chess Engine Tournament Monitor v2.0
echo              FIRST TIME SETUP
echo  ===============================================
echo.

REM Check Python installation
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('python --version') do echo [OK] Found %%i
)

echo.
echo [2/5] Installing Python dependencies...
pip install -r requirements_realtime.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed successfully

echo.
echo [3/5] Checking configuration...
if not exist "config\settings.yaml" (
    echo [ERROR] Configuration file not found
    echo Please ensure config\settings.yaml exists
    pause
    exit /b 1
)
echo [OK] Configuration file found

echo.
echo [4/5] Creating directories...
if not exist "game_records" mkdir "game_records"
if not exist "database" mkdir "database"
echo [OK] Directories created

echo.
echo [5/5] Testing system components...

REM Test Arena monitor
python -c "from services.arena_monitor import ArenaMonitor; print('Arena Monitor: OK')" 2>nul
if errorlevel 1 (
    echo [WARNING] Arena Monitor test failed - check services directory
) else (
    echo [OK] Arena Monitor ready
)

REM Test ETL pipeline
python -c "from services.realtime_etl import RealTimeETL; print('ETL Pipeline: OK')" 2>nul
if errorlevel 1 (
    echo [WARNING] ETL Pipeline test failed - check backend dependencies
) else (
    echo [OK] ETL Pipeline ready
)

REM Test Streamlit
python -c "import streamlit; print('Streamlit: OK')" 2>nul
if errorlevel 1 (
    echo [WARNING] Streamlit test failed
) else (
    echo [OK] Streamlit ready
)

echo.
echo  ===============================================
echo              SETUP COMPLETE!
echo  ===============================================
echo.
echo  Next steps:
echo  1. Review config\settings.yaml and update paths if needed
echo  2. Run tournament_manager.bat to start the system
echo  3. Access the dashboard at http://localhost:8501
echo.
echo  Quick Start:
echo  - Option 3 in tournament_manager.bat starts everything
echo  - Dashboard auto-refreshes every 30 seconds
echo  - Monitor service watches Arena tournaments directory
echo.

set /p start="Start the system now? (y/n): "
if /i "%start%"=="y" (
    echo.
    echo Starting tournament manager...
    call tournament_manager.bat
) else (
    echo.
    echo Setup complete! Run tournament_manager.bat when ready.
    pause
)

exit /b 0
