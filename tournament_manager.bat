@echo off
title Chess Engine Tournament Monitor - Control Panel
color 0A

:MENU
cls
echo.
echo  ===============================================
echo   Chess Engine Tournament Monitor v2.0
echo  ===============================================
echo.
echo  [1] Start Monitor Service (File Watching)
echo  [2] Start Dashboard (Streamlit)
echo  [3] Start Both Services
echo  [4] View System Status
echo  [5] Install/Update Dependencies
echo  [6] Exit
echo.
set /p choice="Select option (1-6): "

if "%choice%"=="1" goto START_MONITOR
if "%choice%"=="2" goto START_DASHBOARD
if "%choice%"=="3" goto START_BOTH
if "%choice%"=="4" goto VIEW_STATUS
if "%choice%"=="5" goto INSTALL_DEPS
if "%choice%"=="6" goto EXIT
goto MENU

:START_MONITOR
cls
echo Starting Tournament Monitor Service...
echo.
echo This will monitor the Arena tournaments directory and process new files.
echo Press Ctrl+C to stop the service.
echo.
pause
cd /d "%~dp0services"
python tournament_monitor.py
pause
goto MENU

:START_DASHBOARD
cls
echo Starting Streamlit Dashboard...
echo.
echo The dashboard will be available at:
echo - Local: http://localhost:8501
echo - Network: http://[your-ip]:8501
echo.
echo Press Ctrl+C to stop the dashboard.
echo.
pause
cd /d "%~dp0dashboard"
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
pause
goto MENU

:START_BOTH
cls
echo Starting Both Services...
echo.
echo This will start both the monitor service and dashboard.
echo Two command windows will open - keep both running.
echo.
pause

REM Start monitor service in new window
start "Tournament Monitor" cmd /k "cd /d \"%~dp0services\" && python tournament_monitor.py"

REM Wait a moment for the monitor to start
timeout /t 3 /nobreak >nul

REM Start dashboard in new window
start "Streamlit Dashboard" cmd /k "cd /d \"%~dp0dashboard\" && streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0"

echo.
echo Both services are starting...
echo - Monitor Service: Running in background
echo - Dashboard: http://localhost:8501
echo.
echo Press any key to return to menu...
pause >nul
goto MENU

:VIEW_STATUS
cls
echo System Status Check...
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
) else (
    for /f "tokens=*" %%i in ('python --version') do echo [OK] %%i
)

REM Check Streamlit
python -c "import streamlit; print(f'Streamlit {streamlit.__version__}')" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Streamlit is not installed
) else (
    for /f "tokens=*" %%i in ('python -c "import streamlit; print(f'Streamlit {streamlit.__version__}')"') do echo [OK] %%i
)

REM Check directories
if exist "%~dp0config\settings.yaml" (
    echo [OK] Configuration file found
) else (
    echo [ERROR] Configuration file missing
)

if exist "%~dp0services\tournament_monitor.py" (
    echo [OK] Monitor service found
) else (
    echo [ERROR] Monitor service missing
)

if exist "%~dp0dashboard\streamlit_app.py" (
    echo [OK] Dashboard found
) else (
    echo [ERROR] Dashboard missing
)

echo.
echo Press any key to return to menu...
pause >nul
goto MENU

:INSTALL_DEPS
cls
echo Installing/Updating Dependencies...
echo.

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not available
    echo Please install Python with pip
    pause
    goto MENU
)

echo Installing required packages...
pip install -r requirements_realtime.txt

echo.
echo Installation complete!
echo Press any key to return to menu...
pause >nul
goto MENU

:EXIT
cls
echo.
echo Thank you for using Chess Engine Tournament Monitor!
echo.
echo To stop running services:
echo - Close any open command windows
echo - Or press Ctrl+C in service windows
echo.
pause
exit

:ERROR
echo.
echo An error occurred. Please check the logs for details.
pause
goto MENU
