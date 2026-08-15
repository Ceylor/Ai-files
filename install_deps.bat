@echo off
setlocal
chcp 65001 >nul
title AI AutoClip Pro 2.0 — Установка зависимостей

echo ============================================================
echo   AI AutoClip Pro 2.0 — Установка зависимостей
echo   (первый запуск)
echo ============================================================
echo.

cd /d "%~dp0"

REM ========== 1. Проверка Python ==========
echo [1/4] Проверка Python...
python --version
if errorlevel 1 (
    echo [ОШИБКА] Python не найден. Установите Python 3.9+ и добавьте его в PATH.
    echo Скачать: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM ========== 2. Виртуальное окружение ==========
echo.
echo [2/4] Настройка виртуального окружения (venv)...

if not exist "venv\Scripts\activate.bat" (
    echo   Создаю виртуальное окружение...
    python -m venv venv
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось создать виртуальное окружение.
        pause
        exit /b 1
    )
) else (
    echo   Виртуальное окружение уже существует.
)

call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ОШИБКА] Не удалось активировать venv.
    pause
    exit /b 1
)

REM ========== 3. Python-зависимости ==========
echo.
echo [3/4] Установка Python-зависимостей (pip install -r requirements.txt)...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ВНИМАНИЕ] Некоторые зависимости могли не установиться.
    echo Проверьте сообщения выше.
)

REM ========== 4. Frontend зависимости ==========
echo.
echo [4/4] Установка зависимостей фронтенда (npm install)...

if not exist "frontend\package.json" (
    echo [ОШИБКА] Папка frontend\package.json не найдена.
    echo Проверьте структуру проекта.
    pause
    exit /b 1
)

cd frontend
call npm install
if errorlevel 1 (
    echo [ВНИМАНИЕ] npm install завершился с ошибкой.
    echo Убедитесь, что установлен Node.js 18+.
    echo Скачать: https://nodejs.org/
)

cd ..

echo.
echo ============================================================
echo   Установка завершена!
echo.
echo   Теперь запустите систему двойным кликом по start_all.bat
echo   или вручную:
echo     - start_all.bat
echo ============================================================
echo.
pause