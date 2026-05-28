@echo off
REM ============================================================
REM  Manipuri Tutor — one-click launcher (portable)
REM
REM  - First run: creates .venv and installs dependencies
REM  - Detects .venv copied from another machine / Python version
REM    and rebuilds it automatically
REM  - Starts Streamlit and opens browser at http://localhost:8501
REM ============================================================

cd /d "%~dp0"
title Manipuri Tutor
setlocal EnableDelayedExpansion

REM --- Step 1: Find a working Python to bootstrap from ---------
set "BOOTSTRAP_PY="
where py >nul 2>&1 && set "BOOTSTRAP_PY=py"
if not defined BOOTSTRAP_PY (
    where python >nul 2>&1 && set "BOOTSTRAP_PY=python"
)
if not defined BOOTSTRAP_PY (
    if exist "C:\Users\administrator\AppData\Local\Python\bin\python.exe" set "BOOTSTRAP_PY=C:\Users\administrator\AppData\Local\Python\bin\python.exe"
)

if not defined BOOTSTRAP_PY (
    echo.
    echo [ERROR] Python is not installed on this computer.
    echo.
    echo Install Python 3.10 or newer from:
    echo     https://www.python.org/downloads/
    echo.
    echo During install, tick the box "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo Bootstrap Python: %BOOTSTRAP_PY%

REM --- Step 2: Check if existing .venv is usable ---------------
set "VENV_PY=%~dp0.venv\Scripts\python.exe"
set "VENV_BROKEN=0"

if not exist "%VENV_PY%" (
    set "VENV_BROKEN=1"
) else (
    "%VENV_PY%" --version >nul 2>&1
    if errorlevel 1 set "VENV_BROKEN=1"
)

REM --- Step 3: Rebuild venv if broken or missing ---------------
if "!VENV_BROKEN!"=="1" (
    if exist .venv (
        echo.
        echo Detected an incompatible .venv ^(probably from another machine
        echo or a different Python version^). Removing and rebuilding...
        rmdir /s /q .venv
    ) else (
        echo.
        echo First-run setup. Creating virtual environment...
    )

    %BOOTSTRAP_PY% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create .venv
        pause
        exit /b 1
    )

    echo.
    echo Installing dependencies. This takes 2-3 minutes on first run...
    echo.
    "%VENV_PY%" -m pip install --upgrade pip
    "%VENV_PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] pip install failed. Check your internet connection.
        pause
        exit /b 1
    )

    echo.
    echo Setup complete. Starting app...
    echo.
)

REM --- Step 4: Open browser after Streamlit has booted ---------
start "" /B cmd /c "timeout /t 6 /nobreak >nul & start """" http://localhost:8501"

REM --- Step 5: Launch Streamlit ------------------------------
"%VENV_PY%" -m streamlit run app.py ^
    --server.port 8501 ^
    --server.address 0.0.0.0 ^
    --server.headless true ^
    --browser.gatherUsageStats false

echo.
echo Streamlit has stopped. Press any key to close this window...
pause >nul
