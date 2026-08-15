@echo off
chcp 65001 >nul
title AI AutoClip Pro 2.0 - Install Dependencies
cd /d "%~dp0"

echo ============================================================
echo   AI AutoClip Pro 2.0 - Install Dependencies (first run)
echo ============================================================
echo.

REM ===== 1. Check Python =====
echo [1/5] Checking Python...
python --version
if errorlevel 1 goto :no_python

REM ===== 2. Create / activate virtual environment =====
echo.
echo [2/5] Setting up virtual environment (venv)...
if exist "venv\Scripts\activate.bat" goto :venv_exists
echo   Creating venv...
python -m venv venv
if errorlevel 1 goto :venv_fail

:venv_exists
call "venv\Scripts\activate.bat"
if errorlevel 1 goto :venv_fail

REM ===== 3. Install Python dependencies =====
echo.
echo [3/5] Installing Python dependencies (pip install -r requirements.txt)...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto :pip_warn

REM ===== 4. Check frontend folder =====
echo.
echo [4/5] Checking frontend folder...
if exist "frontend\package.json" goto :frontend_ok
echo [!] frontend\package.json not found. Check project structure.
echo.
pause
exit /b 1

:frontend_ok
REM ===== 5. Install frontend dependencies =====
echo.
echo [5/5] Installing frontend dependencies (npm install)...
cd /d "%~dp0frontend"
call npm install
cd /d "%~dp0"

echo.
echo ============================================================
echo   Installation finished!
echo.
echo   Now start the system with start_all.bat
echo ============================================================
echo.
pause
exit /b 0

:no_python
echo.
echo [ERROR] Python not found. Please install Python 3.9+ and add it to PATH.
echo         Download: https://www.python.org/downloads/
echo.
pause
exit /b 1

:venv_fail
echo.
echo [ERROR] Failed to create or activate virtual environment.
echo.
pause
exit /b 1

:pip_warn
echo.
echo [WARNING] Some Python dependencies may have failed to install.
echo           Check the messages above.
echo.
pause
exit /b 1