@echo off
REM Start Development Mode (Backend + Frontend Dev Server)

echo Starting Engine Metrics Dashboard in Development Mode...

REM Start backend in background
start "Backend Server" /min cmd /c "call venv\Scripts\activate.bat && cd backend && python main.py"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend development server
echo Starting frontend development server...
cd frontend
call npm start
