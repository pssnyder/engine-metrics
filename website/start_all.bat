@echo off
title Chess Engine Tournament System - Full Stack
color 0A

cls
echo.
echo  ===============================================
echo   Chess Engine Tournament Monitor v2.0
echo   Full Stack Launcher
echo  ===============================================
echo.

echo [1/4] Starting Backend API Server...
start "Backend API" cmd /c "cd /d "%~dp0" && start_backend.bat"

echo [2/4] Waiting 5 seconds for backend to initialize...
timeout /t 5 /nobreak > nul

echo [3/4] Starting ETL Data Processing Service...
start "ETL Service" cmd /c "cd /d "%~dp0" && start_etl.bat"

echo [4/4] Starting Streamlit Dashboard...
start "Dashboard" cmd /c "cd /d "%~dp0" && start_dashboard.bat"

echo.
echo  ===============================================
echo   System Status
echo  ===============================================
echo.
echo ✅ Backend API:     http://localhost:8000
echo ✅ Dashboard:       http://localhost:8501
echo ✅ API Docs:        http://localhost:8000/docs
echo ✅ ETL Service:     Running in background
echo.
echo All services are starting in separate windows.
echo Close this window or press any key to continue.
echo.

pause
