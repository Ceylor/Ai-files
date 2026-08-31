@echo off
chcp 65001 >nul
title AI AutoClip Pro 2.0
cd /d "%~dp0"

echo ============================================================
echo   AI AutoClip Pro 2.0 - Startup (single window)
echo   Backend:  http://127.0.0.1:8000
echo   Frontend: http://localhost:3000
echo   (Browser will NOT be opened automatically)
echo ============================================================
echo.

REM ===== Check virtual environment =====
if exist "venv\Scripts\activate.bat" goto venv_ok
echo [!] Virtual environment not found.
echo     Expected: venv\Scripts\activate.bat
echo.
echo [!] Please run install_deps.bat first.
echo.
pause
exit /b 1

:venv_ok
REM ===== Check frontend dependencies =====
if exist "frontend\node_modules" goto frontend_ok
echo [!] Frontend dependencies not found.
echo     Expected: frontend\node_modules
echo.
echo [!] Please run install_deps.bat first.
echo.
pause
exit /b 1

:frontend_ok
echo [1/2] Starting backend (FastAPI) in background...
echo       Logs: logs\backend.log
echo.

REM Create logs dir if missing
if not exist "logs" mkdir logs

REM Run migrations then backend, both in this same window.
call venv\Scripts\activate.bat
call alembic upgrade head > logs\migrations.log 2>&1
start "AI-AutoClip-Backend" /b cmd /c "call venv\Scripts\activate.bat && python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 > logs\backend.log 2>&1"

echo [2/2] Starting frontend (Next.js) in background...
echo       Logs: logs\frontend.log
echo.
start "AI-AutoClip-Frontend" /b cmd /c "cd /d %~dp0frontend && npm run dev > ..\logs\frontend.log 2>&1"

echo.
echo ============================================================
echo   System is starting...
echo   - Backend:  http://127.0.0.1:8000  (logs\backend.log)
echo   - Frontend: http://localhost:3000  (logs\frontend.log)
echo.
echo   Press Ctrl+C in this window to stop both processes.
echo   This window must stay open while the system is running.
echo ============================================================
echo.

:loop
timeout /t 2 >nul
goto loop