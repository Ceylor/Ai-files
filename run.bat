@echo off
chcp 65001 >nul
title AI AutoClip Pro - Запуск
echo ==========================================
echo  Запуск AI AutoClip Pro...
echo ==========================================
echo.

:: Переход в папку со скриптом
cd /d "%~dp0"

:: Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден! Установите Python 3.10+ и добавьте в PATH.
    pause
    exit /b
)

:: Запуск главного скрипта
python run_dashboard.py

:: Если скрипт завершился с ошибкой, не закрывать окно
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Программа завершилась с кодом ошибки.
    pause
)