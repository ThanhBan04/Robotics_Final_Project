@echo off
echo ============================================
echo  UAV Target Tracking 2D - Setup
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.10+ and add to PATH.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.

:: Create virtual environment
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)
echo.

:: Install dependencies
echo Installing dependencies...
.venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo [WARNING] Some dependencies may have failed. Trying alternative...
    python -m pip install -r requirements.txt
)
echo.

:: Install pyyaml if not in requirements
.venv\Scripts\pip.exe install pyyaml >nul 2>&1

:: Verify imports
echo Verifying installation...
.venv\Scripts\python.exe -c "import numpy, scipy, pygame, yaml; print('[OK] All core libraries imported successfully.')"
if errorlevel 1 (
    python -c "import numpy, scipy, pygame, yaml; print('[OK] All core libraries imported (global).')"
)
echo.
echo ============================================
echo  Setup complete! Run 'run.bat' to start.
echo ============================================
pause
