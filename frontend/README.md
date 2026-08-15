# 🎬 AI AutoClip Pro 2.0 — Frontend (Next.js)

Веб-интерфейс для системы ИИ-генерации клипов. Построен на **Next.js (App Router)**,
**Tailwind CSS** с футуристическим hi-tech дизайном. Клиент общается с бэкендом
**FastAPI** через REST API.

## ✨ Возможности

- **Дашборд** — статистика с анимированными графиками (recharts), последние задачи.
- **Задачи** — загрузка папки с видео, список `batch_jobs` с фильтром по статусу,
  детали задачи с прогрессом и списком видео, запуск обработки.
- **Результаты** — список созданных клипов (`completed`) и композиций (`composed`)
  со встроенным видео-плеером, **визуальным таймлайном** (стиль видеоредактора)
  и кнопкой скачивания.
- **Категории** — CRUD для категорий.
- **Обучение** — запуск самообучения на референсных клипах категории.
- **Настройки** — параметры обработки (локально в браузере).
- **Тёмная тема (по умолчанию)** — неоновый hi-tech стиль, сохранение выбора в localStorage.

## 🛠 Технологии

- Next.js 14 (App Router)
- React 18
- Tailwind CSS 3 (dark mode) — неоновая палитра, glassmorphism, анимации
- **framer-motion** — плавные анимации появления/переходов
- **recharts** — графики (круговые, столбчатые)
- REST API через `fetch` (проксирование на бэкенд)

> Фоновые частицы и сетка реализованы на чистом CSS (без внешней библиотеки).

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
cd frontend
npm install
```

### 2. Настройка окружения

Скопируйте `.env.local.example` в `.env.local` и, при необходимости, укажите адрес бэкенда:

```bash
cp .env.local.example .env.local
```

По умолчанию фронтенд проксирует `/api/*` на `http://127.0.0.1:8000` (FastAPI).

### 3. Запуск в режиме разработки

```bash
npm run dev
```

Откройте http://localhost:3000.

### 4. Продакшен-сборка

```bash
npm run build
npm start
```

## 🌙 Тема

Тёмная тема включена **по умолчанию**. Выбор сохраняется в `localStorage`
(`theme`) и применяется к `<html class="dark">`. Переключение доступно в сайдбаре.
Контекст темы — `components/ThemeProvider.jsx`, хук — `lib/useTheme.js`.

## 🔌 Связь с бэкендом

Фронтенд использует **rewrites** в `next.config.js`: все запросы `/api/*`
проксируются на бэкенд FastAPI. Предполагается, что бэкенд запущен на `127.0.0.1:8000`
(см. `src/api/main.py`).

Основные используемые эндпоинты:

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/status` | Статус системы |
| GET | `/api/videos` | Список видео |
| POST | `/api/batch/upload_folder` | Создать задачу из папки |
| GET | `/api/batch/list` | Список задач |
| POST | `/api/batch/process/{id}` | Запустить обработку |
| GET | `/api/batch/status/{id}` | Статус задачи |
| GET | `/api/batch/results/{id}` | Видео в задаче |
| GET/POST/PUT/DELETE | `/api/categories` | CRUD категорий |
| POST | `/api/learning/train` | Запуск обучения |

## 📁 Структура

```
frontend/
├── app/                    # страницы (App Router)
│   ├── layout.js           # корневой layout (шрифты, ThemeProvider)
│   ├── globals.css         # глобальные стили (неон, glassmorphism, частицы)
│   ├── page.js             # дашборд (recharts)
│   ├── tasks/              # задачи
│   ├── results/            # результаты (таймлайн)
│   ├── categories/         # категории
│   ├── learning/           # обучение
│   └── settings/           # настройки
├── components/
│   ├── Layout.jsx          # обёртка с сайдбаром и фоновыми эффектами
│   ├── Sidebar.jsx         # неоновая навигация
│   ├── ThemeProvider.jsx   # глобальный контекст темы
│   ├── BackgroundFX.jsx    # частицы + неоновая сетка
│   ├── Card.jsx            # glass-карточка
│   ├── Button.jsx          # неоновая кнопка
│   ├── StatusBadge.jsx     # неоновый бейдж статуса
│   ├── VideoPlayer.jsx     # видео-плеер
│   ├── Timeline.jsx        # визуальный таймлайн
│   ├── AnimatedSection.jsx # framer-motion анимация
│   ├── UploadFolderForm.jsx# форма загрузки папки
│   └── BatchDetails.jsx    # детали задачи
├── lib/
│   ├── api.js              # клиент API
│   └── useTheme.js         # хук тёмной темы (обёртка над ThemeProvider)
├── package.json
├── next.config.js
├── tailwind.config.js
└── postcss.config.js
```