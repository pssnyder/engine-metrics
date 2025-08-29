@echo off
echo Starting Engine Metrics Dashboard Backend...
echo.

REM Change to the backend directory
cd /d "%~dp0backend"

REM Start the FastAPI server using the configured Python environment
"C:/Users/patss/AppData/Local/Programs/Python/Python313/python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
