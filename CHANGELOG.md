# CHANGELOG

Все заметные изменения проекта документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

## [0.5.0] — Стадия 10: Массовая обработка и композиция (mod9_batch_processing)

### Добавлено
- **`src/modules/mod9_batch_processing/`** — новый модуль пакетной обработки:
  - `composer.py` — `ClipComposer`: кластеризация фрагментов по средним CLIP-эмбеддингам (косинусное сходство, агломерация), `compose_clips()` создаёт несколько планов клипов, fallback `group_by_time()`;
  - `processor.py` — `BatchProcessor`: асинхронная очередь `process_folder(folder_id)`, цепочка ingest→анализ→паттерны→сторибилдер→монтаж→экспорт, graceful shutdown через `_stop_event`;
  - `__init__.py` — экспорт `ClipComposer`, `BatchProcessor`.
- **БД**: таблица `batch_jobs` (folder_path, status, total_videos, processed_videos, created_at, finished_at) + поле `videos.batch_job_id` (FK, ON DELETE SET NULL).
- **CRUD**: `create_batch_job`, `get_batch_job`, `list_batch_jobs`, `update_batch_job_status`, `update_batch_job_progress`, `finish_batch_job`, `get_batch_pending_videos`.
- **Миграция** `0003_batch_jobs.py` (таблица batch_jobs + поле videos.batch_job_id, `render_as_batch=True`).
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

### Примечания
- Полный монтаж в `BatchProcessor._run_editing` — временная заглушка (копирование исходника). Реальный монтаж через `run_pipeline` не подключён (отмечено в коде).
- Интеграция созданных композиций с БД (куда сохранять клипы) будет реализована на следующем этапе.

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