# CHANGELOG

Все заметные изменения проекта документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

## [0.7.0] — Футуристический редизайн и сохранение темы

### Добавлено
- **Сохранение темы** — глобальный `ThemeProvider` (`frontend/components/ThemeProvider.jsx`):
  - тема читается из `localStorage` при загрузке и сразу применяется к `<html class="dark">`;
  - тёмная тема **по умолчанию** (не зависит от системной);
  - `useTheme` (`lib/useTheme.js`) — тонкая обёртка над контекстом.
- **Футуристический hi-tech дизайн**:
  - неоновая палитра (`#0a0a0f`, `#111118`, `#1a1a2e`; акценты `#00f0ff`, `#7c3aed`, `#d946ef`, `#fbbf24`);
  - glassmorphism-карточки (полупрозрачный фон + blur + тонкая рамка + тень);
  - неоновые градиенты в заголовках, кнопках, активных пунктах навигации;
  - шрифты Inter + Space Grotesk (`next/font/google`);
  - фоновые эффекты: неоновая сетка и анимированные частицы (чистый CSS) — `BackgroundFX.jsx`;
  - плавные анимации появления через **framer-motion** (`AnimatedSection.jsx`, страницы);
  - графики дашборда на **recharts** (PieChart, BarChart).
- **Таймлайн** (`frontend/components/Timeline.jsx`) — стиль профессионального видеоредактора:
  - сегменты с неоновыми градиентами по статусу;
  - маркеры переходов (fade/zoom/spin/cut);
  - анимация выбора сегмента (framer-motion).
- **`frontend/package.json`** — добавлены `framer-motion`, `recharts` (установка: `npm install`).

### Изменено
- `frontend/app/layout.js` — подключение шрифтов и `ThemeProvider`.
- `frontend/tailwind.config.js` — неоновая палитра, шрифты, тени, анимации.
- `frontend/app/globals.css` — glassmorphism, неон, частицы, скроллбар.
- `frontend/components/` — `Layout`, `Sidebar`, `Card`, `Button`, `StatusBadge`, `VideoPlayer`, `UploadFolderForm`, `BatchDetails` — неоновый стиль.
- `frontend/app/` — `page.js` (дашборд с recharts), `tasks`, `results` (таймлайн), `categories`, `learning`, `settings` — единый hi-tech стиль и framer-motion-анимации.

### Удалено
- `frontend/components/MiniBarChart.jsx`, `DonutChart.jsx` — заменены на графики recharts.

### Примечания
- Перед запуском фронтенда выполните `cd frontend && npm install` (будут установлены `framer-motion`, `recharts`).

## [0.6.1] — Упрощение запуска для не-технических пользователей

### Добавлено
- **`start_all.bat`** — запуск системы одним кликом:
  - активация виртуального окружения;
  - применение миграций (`alembic upgrade head`);
  - запуск бэкенда (FastAPI) в отдельном окне;
  - запуск фронтенда (Next.js) в отдельном окне через 3 секунды;
  - автоматическое открытие браузера на `http://localhost:3000`.
- **`install_deps.bat`** — установка всех зависимостей для первого запуска:
  - создание venv, `pip install -r requirements.txt`, `cd frontend && npm install`.
- **`README.md`** — корневая документация с инструкцией «двойной клик по start_all.bat».

## [0.6.0] — Стадия 11: Веб-интерфейс на Next.js (приоритет №5)

### Добавлено
- **`frontend/`** — новый Next.js (App Router) + Tailwind CSS фронтенд:
  - `Дашборд` — статистика (видео, клипы, композиции, активные задачи), последние задачи;
  - `Задачи` — загрузка папки (POST /api/batch/upload_folder), список batch_jobs с фильтром по статусу, детали задачи с прогрессом, списком видео и запуском обработки (POST /api/batch/process/{id}), авто-обновление (polling) во время обработки;
  - `Результаты` — список клипов (completed/composed) со встроенным видео-плеером и скачиванием;
  - `Категории` — CRUD для категорий;
  - `Обучение` — запуск самообучения (POST /api/learning/train), статус обучения;
  - `Настройки` — параметры обработки;
  - тёмная тема (переключение через `useTheme`), адаптивный сайдбар, бейджи статусов.
- **`src/api/main.py`** — новый эндпоинт `GET /api/batch/list` (список batch_jobs, опционально по статусу) для дашборда и списка задач.
- **`frontend/README.md`** — документация и инструкция по запуску.

### Компоненты фронтенда
- `app/` — страницы: `page.js` (дашборд), `tasks/`, `results/`, `categories/`, `learning/`, `settings/`.
- `components/` — `Layout`, `Sidebar`, `Card`, `Button`, `StatusBadge`, `VideoPlayer`, `UploadFolderForm`, `BatchDetails`.
- `lib/` — `api.js` (клиент REST), `useTheme.js` (тёмная тема).

### Изменено
- **`src/api/main.py`** — добавлен `GET /api/batch/list`.

### Примечания
- Фронтенд проксирует `/api/*` на бэкенд FastAPI (`http://127.0.0.1:8000`) через rewrites в `next.config.js`.
- Запуск: `cd frontend && npm install && npm run dev` (порт 3000).

## [0.5.1] — Доработки модуля 9: реальный монтаж и сохранение композиций

### Изменено
- **`src/modules/mod9_batch_processing/processor.py`**:
  - `_run_editing` — **реальный монтаж** через `VideoPipeline.process_batch` (модули mod1–mod6) вместо копирования исходника; при сбое — graceful fallback на копирование;
  - добавлен `_compose_and_save(folder_id)` — композиция клипов по CLIP-эмбеддингам обработанных видео (`ClipComposer.compose_clips`) и сохранение результата в БД как новых записей `videos` (статус `composed`, привязка к `batch_job_id`);
  - `process_folder` вызывает `_compose_and_save` после обработки всех видео (кроме случая graceful shutdown).
- **`tests/test_mod9_batch_processing.py`** — добавлены тесты реального монтажа (`test_run_editing_uses_pipeline`), fallback-копии (`test_run_editing_fallback_copy`), сохранения композиций (`test_compose_and_save`).
- **`BATCH_PROCESSING.md`** — актуализирована документация (реальный монтаж, композиция и сохранение в БД).

### Примечания
- Реальный монтаж выполняется тем же полным конвейером `VideoPipeline`, что и `run_pipeline`.
- Композиции сохраняются в `videos` со статусом `composed`; в `extra_metadata` хранится `{kind, name, source_video_ids}`.

## [0.5.0] — Стадия 10: Массовая обработка и композиция (mod9_batch_processing)

### Добавлено
- **`src/modules/mod9_batch_processing/`** — новый модуль пакетной обработки:
  - `composer.py` — `ClipComposer`: кластеризация фрагментов по средним CLIP-эмбеддингам (косинусное сходство, агломерация), `compose_clips()` создаёт несколько планов клипов, fallback `group_by_time()`;
  - `processor.py` — `BatchProcessor`: асинхронная очередь `process_folder(folder_id)`, цепочка ingest→анализ→паттерны→сторибилдер→монтаж→экспорт, graceful shutdown через `_stop_event`;
  - `__init__.py` — экспорт `ClipComposer`, `BatchProcessor`.
- **БД**: таблица `batch_jobs` (folder_path, status, total_videos, processed_videos, created_at, finished_at) + поле `videos.batch_job_id` (FK, ON DELETE SET NULL).
- **CRUD**: `create_batch_job`, `get_batch_job`, `list_batch_jobs`, `update_batch_job_status`, `update_batch_job_progress`, `finish_batch_job`, `get_batch_pending_videos`.
- **Миграция** `0003_batch_jobs.py` (таблица batch_jobs + поле videos.batch_job_id).
- **REST API**:
  - `POST /api/batch/upload_folder` — сканирование папки, создание BatchJob и pending-записей Video;
  - `POST /api/batch/process/{folder_id}` — запуск пакетной обработки в фоне;
  - `GET /api/batch/status/{folder_id}` — статус задачи;
  - `GET /api/batch/results/{folder_id}` — видео и их статусы.
- **`tests/test_mod9_batch_processing.py`** — тесты с моками (кластеризация, compose_clips, group_by_time, process_folder, graceful shutdown).
- **`BATCH_PROCESSING.md`** — документация модуля.

### Изменено
- **`src/database/models.py`** — добавлены `BatchJob` и `Video.batch_job_id`.
- **`src/database/crud.py`** — добавлены batch-функции; `create_video`/`list_videos` поддерживают `batch_job_id`.
- **`src/database/__init__.py`** — импорт `BatchJob`.
- **`src/api/main.py`** — добавлены batch-эндпоинты; `_video_to_dict` включает `batch_job_id`; `/api/status` считает batch_jobs.

## [0.4.0] — Стадия 9: Многослойный анализ контента (mod8_analysis)

### Добавлено
- **`src/modules/mod8_analysis/`** — новый модуль многослойного анализа:
  - `schemas.py` — pydantic-модели (EmotionalFrame, DetectedObject, MotionSample, GoldenMoment, ClipEmbedding, VideoAnalysisResult);
  - `emotion_detector.py` — эмоции лиц (DeepFace/FER), graceful fallback;
  - `object_detector.py` — объекты (YOLO/ultralytics), graceful fallback;
  - `motion_analyzer.py` — движение (optical flow, Farneback), энергия 0..1;
  - `golden_moments.py` — «золотые моменты»: интегральный скор = (эмоция + движение + редкость объекта) / 3, топ-3 для хука;
  - `clip_embedder.py` — CLIP-эмбеддинги кадров (openai/clip-vit-base-patch32), graceful fallback;
  - `analyzer.py` — оркестратор `MultiLayerAnalyzer`, асинхронный запуск слоёв через asyncio.to_thread.
- **БД**: таблица `frame_embeddings` (video_id, timestamp, embedding) + поля `analysis_results`, `golden_moments` в `videos`; CRUD-функции `save_analysis_results`, `save_frame_embeddings`, `get_analysis`, `get_frame_embeddings`.
- **Миграция** `0002_frame_embeddings.py` (таблица frame_embeddings + поля анализа).
- **REST API**:
  - `POST /api/analysis/analyze/{video_id}` — асинхронный запуск анализа (BackgroundTasks);
  - `GET /api/analysis/{video_id}` — результаты анализа;
  - `GET /api/analysis/{video_id}/embeddings` — CLIP-эмбеддинги.
- **Интеграция с нарративом** (`story_builder.py`): параметр `golden_moments`, выбор хука из топ-3 «золотых моментов» (`_apply_golden_moments`).
- **`tests/test_mod8_analysis.py`** — тесты с моками (золотые моменты, движение, graceful fallback оркестратора).
- **`ANALYSIS.md`** — документация и инструкция по установке зависимостей.
- **`requirements.txt`** — опциональные зависимости анализа (deepface, ultralytics, torch, transformers) с extra-маркером `analysis`.

### Изменено
- **`src/database/models.py`** — добавлены FrameEmbedding и поля анализа в Video.
- **`src/database/crud.py`** — добавлены CRUD-функции для анализа.
- **`src/api/main.py`** — добавлены эндпоинты анализа.
- **`src/utils/story_builder.py`** — интеграция «золотых моментов» в выбор хука.

### Примечания
- Все слои имеют graceful fallback: если модель недоступна — слой пропускается, анализ не падает.
- Тяжёлые ML-слои (DeepFace, YOLO, CLIP) — опциональны (`pip install ".[analysis]"`).
- Документация: см. `ANALYSIS.md`.

## [0.3.0] — Стадия 8: Схема базы данных (SQLAlchemy 2.0 + Alembic)

### Добавлено
- **`src/database/`** — новый пакет БД:
  - `base.py` — `DeclarativeBase` (Base) + миксин `TimestampMixin` (created_at);
  - `models.py` — SQLAlchemy-модели в стиле 2.0 (`Mapped`, `mapped_column`);
  - `session.py` — engine, фабрика сессий, `get_db`, `session_scope`, `init_db`;
  - `crud.py` — базовые CRUD-операции для категорий и видео.
- **`migrations/`** — Alembic (`alembic.ini`, `env.py`, `script.py.mako`, `0001_initial.py`).
- **REST API**: CRUD-эндпоинты `/api/categories` и `/api/videos`, lifespan-инициализация БД.
- **Интеграция с самообучением** (`learner.py`): паттерны сохраняются в БД (`learning_patterns`).
- **`tests/test_database.py`**, **`DATABASE.md`**, `requirements.txt` (sqlalchemy, alembic), `.env.example` (DATABASE_URL).

## [0.2.0] — Стадия 7: Самообучение на примерах (AI AutoClip Pro 2.0)

### Добавлено
- **`src/modules/mod7_learning/`** — модуль самообучения: pattern_models, pattern_extractor, vector_store (FAISS→Chroma→NumPy), learner (LearningEngine).
- **REST API**: `/api/learning/*` (train, status, categories, profile, find_similar, extract).
- **`tests/test_mod7_learning.py`**, `requirements.txt` (faiss-cpu/chromadb), `SELF_LEARNING.md`.

## [0.1.0] — Стадия 1: Ингестия и нормализация (mod0_ingest)

### Добавлено
- **`src/modules/mod0_ingest.py`** — ffprobe-метаданные, авто-поворот, нормализация fps/размера, извлечение аудио, dry-run, CLI.
- **`tests/test_mod0_ingest.py`**, `pytest.ini`, `requirements.txt` (pytest).

## [0.0.1] — Базовый проект AI AutoClip Pro

- Исходная структура репозитория (src/modules, src/utils, src/core, configs, assets, web_ui).
- Существующие модули mod1..mod6, пайплайн, Web UI.