@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title AI AutoClip Pro 2.0 — Старт

echo ============================================================
echo   AI AutoClip Pro 2.0 — Запуск системы
echo ============================================================
echo.

cd /d "%~dp0"

REM ========== Проверка виртуального окружения ==========
if not exist "venv\Scripts\activate.bat" (
    echo [!] Виртуальное окружение не найдено (venv\Scripts\activate.bat).
    echo [!] Сначала запустите install_deps.bat для установки зависимостей.
    echo.
    pause
    exit /b 1
)

echo [1/4] Активация виртуального окружения...
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ОШИБКА] Не удалось активировать venv.
    pause
    exit /b 1
)

echo [2/4] Применение миграций базы данных (alembic upgrade head)...
call alembic upgrade head
if errorlevel 1 (
    echo [ВНИМАНИЕ] Миграции не применены. Проверьте alembic.ini и DATABASE_URL.
)

echo [3/4] Запуск бэкенда (FastAPI)...
echo.
echo   Бэкенд будет доступен на http://127.0.0.1:8000
echo.

REM ========== Запуск бэкенда в отдельном окне ==========
start "AI AutoClip — Бэкенд" cmd /k "cd /d "%~dp0" && call venv\Scripts\activate.bat && python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000"

echo   Ожидание запуска бэкенда (3 секунды)...
ping -n 4 127.0.0.1 >nul

REM ========== Запуск фронтенда в отдельном окне ==========
echo [4/4] Запуск фронтенда (Next.js)...
echo.

if not exist "frontend\node_modules" (
    echo [!] Зависимости фронтенда не установлены.
    echo [!] Сначала установите их через install_deps.bat.
    echo [!] Пытаюсь запустить фронтенд... возможно, потребуется установка.
)

start "AI AutoClip — Фронтенд" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo ============================================================
echo   Оба процесса запущены.
echo   - Бэкенд:  http://127.0.0.1:8000
echo   - Фронтенд: http://localhost:3000
echo ============================================================
echo.
echo   Открываю браузер через 5 секунд...
ping -n 6 127.0.0.1 >nul

REM ========== Открытие браузера ==========
start "" "http://localhost:3000"

echo   Если браузер не открылся — вручную перейдите по адресу:
echo   http://localhost:3000
echo.
echo   Закройте окна бэкенда/фронтенда, чтобы остановить систему.
echo.
pause