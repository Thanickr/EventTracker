@echo off

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Event Tracker virtual environment was not found.
    echo Expected:
    echo %CD%\.venv\Scripts\python.exe
    pause
    exit /b 1
)

start "" "http://127.0.0.1:8765"

".venv\Scripts\python.exe" -m uvicorn ^
    app.sync_console:app ^
    --host 127.0.0.1 ^
    --port 8765

echo.
echo Event Tracker Sync has stopped.
pause