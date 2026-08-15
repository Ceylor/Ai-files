# 🎬 AI AutoClip Pro 2.0 — Frontend (Next.js)

Веб-интерфейс для системы ИИ-генерации клипов. Построен на **Next.js (App Router)**
и **Tailwind CSS**. Клиент общается с бэкендом **FastAPI** через REST API.

## ✨ Возможности

- **Дашборд** — статистика (видео, клипы, композиции, активные задачи), последние задачи.
- **Задачи** — загрузка папки с видео, список `batch_jobs` с фильтром по статусу,
  детали задачи с прогрессом и списком видео, запуск обработки.
- **Результаты** — список созданных клипов (`completed`) и композиций (`composed`)
  со встроенным видео-плеером и кнопкой скачивания.
- **Категории** — CRUD для категорий.
- **Обучение** — запуск самообучения на референсных клипах категории.
- **Настройки** — параметры обработки (локально в браузере).
- **Тёмная тема** — переключение светлой/тёмной темы.

## 🛠 Технологии

- Next.js 14 (App Router)
- React 18
- Tailwind CSS 3 (dark mode)
- REST API через `fetch` (проксирование на бэкенд)

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
│   ├── layout.js           # корневой layout
│   ├── globals.css         # глобальные стили (Tailwind)
│   ├── page.js             # дашборд
│   ├── tasks/              # задачи
│   ├── results/            # результаты
│   ├── categories/         # категории
│   ├── learning/           # обучение
│   └── settings/           # настройки
├── components/             # переиспользуемые компоненты
│   ├── Layout.jsx          # обёртка с сайдбаром
│   ├── Sidebar.jsx         # навигация
│   ├── Card.jsx            # карточка
│   ├── Button.jsx          # кнопка
│   ├── StatusBadge.jsx     # бейдж статуса
│   ├── VideoPlayer.jsx     # видео-плеер
│   ├── UploadFolderForm.jsx# форма загрузки папки
│   └── BatchDetails.jsx    # детали задачи
├── lib/
│   ├── api.js              # клиент API
│   └── useTheme.js         # хук тёмной темы
├── package.json
├── next.config.js
├── tailwind.config.js
└── postcss.config.js
```