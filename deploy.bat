@echo off
chcp 65001 >nul
title AI AutoClip Pro 2.0 - Deploy
cd /d "%~dp0"

echo ============================================================
echo   AI AutoClip Pro 2.0 - Deploy Script
echo ============================================================
echo.

REM ===== Check Python =====
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python not found in PATH.
    echo     Install Python 3.9+ from https://python.org
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i

REM ===== Check Node.js =====
node --version >nul 2>&1
if errorlevel 1 (
    echo [X] Node.js not found in PATH.
    echo     Install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo [OK] Node %%i

REM ===== Check FFmpeg =====
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [X] FFmpeg not found in PATH.
    echo     Install: winget install Gyan.FFmpeg
    pause
    exit /b 1
)
echo [OK] FFmpeg installed

REM ===== Check yt-dlp =====
yt-dlp --version >nul 2>&1
if errorlevel 1 (
    echo [!] yt-dlp not found. Installing...
    pip install yt-dlp
)
echo [OK] yt-dlp installed

REM ===== Create virtual environment =====
if not exist "venv" (
    echo [1/6] Creating virtual environment...
    python -m venv venv
) else (
    echo [1/6] Virtual environment exists.
)

REM ===== Install Python dependencies =====
echo [2/6] Installing Python dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

REM ===== Install frontend dependencies =====
echo [3/6] Installing frontend dependencies...
cd frontend
if not exist "node_modules" (
    npm install
) else (
    echo       Frontend dependencies exist.
)
cd ..

REM ===== Create data directories =====
echo [4/6] Creating data directories...
for %%d in (data data\reference_clips data\input data\output data\downloads logs) do (
    if not exist "%%d" mkdir "%%d"
)

REM ===== Apply database migrations =====
echo [5/6] Applying database migrations...
call venv\Scripts\activate.bat
alembic upgrade head

REM ===== Run health check =====
echo [6/6] Running health check...
python health_check.py

echo.
echo ============================================================
echo   Deploy complete!
echo.
echo   To start the system:
echo     start_all.bat
echo.
echo   Or run manually:
echo     Backend:  venv\Scripts\activate ^& python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
echo     Frontend: cd frontend ^& npm run dev
echo ============================================================
pause
