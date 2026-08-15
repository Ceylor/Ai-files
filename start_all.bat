@echo off
chcp 65001 >nul
title AI AutoClip Pro 2.0 - Start
cd /d "%~dp0"

echo ============================================================
echo   AI AutoClip Pro 2.0 - Startup
echo ============================================================
echo.

REM ===== Check virtual environment =====
if exist "venv\Scripts\activate.bat" goto :venv_ok
echo [!] Virtual environment not found.
echo     Expected: venv\Scripts\activate.bat
echo.
echo [!] Please run install_deps.bat first to install dependencies.
echo.
pause
exit /b 1

:venv_ok
REM ===== Check frontend dependencies =====
if exist "frontend\node_modules" goto :frontend_ok
echo [!] Frontend dependencies not found.
echo     Expected: frontend\node_modules
echo.
echo [!] Please run install_deps.bat first to install dependencies.
echo.
pause
exit /b 1

:frontend_ok
REM ===== 1. Start backend =====
echo [1/3] Starting backend (FastAPI)...
echo       Backend will be at http://127.0.0.1:8000
echo.
start "Backend" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && alembic upgrade head && python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000"

REM ===== 2. Wait 3 seconds =====
echo [2/3] Waiting 3 seconds for backend...
ping -n 4 127.0.0.1 >nul

REM ===== 3. Start frontend =====
echo [3/3] Starting frontend (Next.js)...
echo       Frontend will be at http://localhost:3000
echo.
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

REM ===== Open browser =====
echo Opening browser at http://localhost:3000 ...
ping -n 4 127.0.0.1 >nul
start http://localhost:3000

echo.
echo ============================================================
echo   System is running:
echo   - Backend:  http://127.0.0.1:8000
echo   - Frontend: http://localhost:3000
echo ============================================================
echo.
echo   Close the "Backend" and "Frontend" windows to stop.
echo.
pause