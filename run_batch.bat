@echo off
echo UAV Target Tracking - Batch Experiment Runner
echo.

:: Check for --headless flag
echo %* | findstr /i "headless" >nul
if %errorlevel% equ 0 (
    echo Running in HEADLESS mode...
    echo.
    if exist ".venv\Scripts\python.exe" (
        .venv\Scripts\python.exe batch_runner.py --mode headless %*
    ) else (
        python batch_runner.py --mode headless %*
    )
) else (
    echo Opening Batch Runner GUI...
    echo.
    if exist ".venv\Scripts\python.exe" (
        .venv\Scripts\python.exe batch_runner.py --mode gui %*
    ) else (
        python batch_runner.py --mode gui %*
    )
)

if errorlevel 1 (
    echo.
    echo [ERROR] Batch runner exited with an error.
    pause
)
