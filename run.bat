@echo off
echo Starting UAV Target Tracking Simulation...
echo.

:: Try venv first, then global Python
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe main.py --mode gui %*
) else (
    python main.py --mode gui %*
)

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error.
    echo Make sure you have run setup.bat first.
    pause
)
