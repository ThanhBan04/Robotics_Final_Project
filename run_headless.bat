@echo off
echo UAV Target Tracking - Headless Batch Runner
echo.

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe batch_runner.py --mode headless %*
) else (
    python batch_runner.py --mode headless %*
)

if errorlevel 1 (
    echo.
    echo [ERROR] Batch runner exited with an error.
    pause
)
