@echo off
REM Start Production Mode (Build Frontend and Serve from Backend)

echo Building frontend for production...
cd frontend
call npm run build

if %errorlevel% neq 0 (
    echo Frontend build failed!
    pause
    exit /b 1
)

cd ..

echo Starting production server...
call venv\Scripts\activate.bat
cd backend
python main.py
