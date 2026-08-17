# 🏗 Архитектура — AI AutoClip Pro 2.0

Техническое описание устройства системы для разработчиков и всех, кому интересно,
как работает AI AutoClip Pro 2.0.

---

## Содержание

1. [Общая архитектура](#общая-архитектура)
2. [Ключевые модули](#ключевые-модули)
3. [Схема базы данных](#схема-базы-данных)
4. [REST API](#rest-api)
5. [Workflow обработки одного видео](#workflow-обработки-одного-видео)
6. [Расширяемость: как добавить новую модель ИИ](#как-добавить-новую-модель-ии)

---

## Общая архитектура

Система состоит из трёх слоёв:

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js)                       │
│          React + Tailwind CSS, /api/* проксируется           │
│                        на :8000                              │
└──────────────────────────┬──────────────────────────────────┘
                           │  HTTP /api/* (REST)
┌──────────────────────────▼──────────────────────────────────┐
│                     BACKEND (FastAPI)                        │
│   src/api/main.py — REST + WebSocket(/ws/logs)               │
│   src/core/pipeline.py — оркестратор пайплайна               │
│   src/modules/ — модули обработки (mod0..mod10)              │
│   src/utils/ — вспомогательные утилиты                       │
└──────────────────────────┬──────────────────────────────────┘
                           │  SQLAlchemy 2.0
┌──────────────────────────▼──────────────────────────────────┐
│                    БАЗА ДАННЫХ (SQLite)                      │
│   src/database/ + Alembic миграции (migrations/)             │
└─────────────────────────────────────────────────────────────┘
```

**Ключевые технологии:**
- **Бэкенд** — FastAPI (Python 3.9+), асинхронный, WebSocket для логов в реальном времени.
- **Фронтенд** — Next.js 14 (App Router) + React 18 + Tailwind CSS, framer-motion, recharts.
- **БД** — SQLAlchemy 2.0 + SQLite (по умолчанию), Alembic для миграций.
- **Обработка видео** — FFmpeg (монтаж, склейка, экспорт).
- **ИИ** — Ollama (LLM для нарратива), опционально DeepFace/YOLO/CLIP для анализа.

**Структура папок:**
```
src/
├── api/            # FastAPI-приложение (эндпоинты)
├── core/           # pipeline.py (оркестратор), config_loader.py
├── database/       # models, crud, session (SQLAlchemy)
├── modules/        # mod0..mod10 — модули обработки
└── utils/          # логгер, story_builder, style_profiler, и др.
configs/            # конфигурация (config.yaml, профили стилей)
migrations/         # Alembic миграции
frontend/           # Next.js интерфейс
docs/               # документация (этот файл + USER_GUIDE.md)
```

---

## Ключевые модули

Модули живут в `src/modules/` и вызываются оркестратором `src/core/pipeline.py`.

### `mod0_ingest` — ингестия и нормализация
`src/modules/mod0_ingest.py`
- Собирает ffprobe-метаданные (длительность, разрешение, fps, поворот).
- Нормализует видео к целевым параметрам (30 fps, 1080×1920, pad).
- Извлекает аудио (PCM) для дальнейшего анализа.
- Graceful fallback: битый файл пропускается, обработка не падает.

### `mod1_ingestion` — ингестия для пайплайна
`src/modules/mod1_ingestion.py`
- Внутренний шаг `VideoPipeline`: анализ фрагмента (транскрипт, сцены, аудио).

### `mod2_story_builder` — нарративный движок
> Реализован в `src/utils/story_builder.py` (Story Builder).

- Строит смысловую структуру клипа: тип истории (путешествие, до/после, туториал, реакция).
- Выбирает **hook** (самый яркий момент для начала клипа).
- Сортирует фрагменты по логической цепочке, удаляет «мусор».
- Определяет **темп** каждой сцены (fast/normal/slow).
- Использует LLM (Ollama, fallback — GigaChat, затем эвристика).

### `mod3_music_ai` — подбор музыки
`src/modules/mod3_music_ai.py`
- Ищет трек по настроению, длительности и BPM.
- Поддержка локальной библиотеки и Pixabay API.

### `mod4_subtitles` — субтитры
`src/modules/mod4_subtitles.py`
- Генерация субтитров (ASS) из транскрипта.

### `mod5_editing` — монтаж
`src/modules/mod5_editing.py`
- **Синхронизация под бит** музыки (склейки на битах/дропах).
- Auto-reframe в 9:16, Ken Burns-эффекты, зум/фейды.
- Темпы сцен из нарратива.

### `mod6_export` — экспорт
`src/modules/mod6_export.py`
- Финальный рендер: видео + музыка + субтитры.
- Профили экспорта (качество, платформа) — см. `mod10_final_features/export_profiles.py`.
- Fallback: NVENC → libx264.

### `mod7_learning` — самообучение
`src/modules/mod7_learning/`
- Извлекает **паттерны успеха** из референсных клипов (структура, темп, переходы, цвет, музыка).
- **Векторное хранилище**: FAISS → Chroma → NumPy (graceful fallback по убыванию).
- `learner.py` — движок обучения, `pattern_extractor.py` — извлечение признаков.

### `mod8_analysis` — многослойный анализ
`src/modules/mod8_analysis/`
- **Эмоции** лиц (`emotion_detector.py` — DeepFace/FER);
- **Объекты** (`object_detector.py` — YOLO);
- **Движение** (`motion_analyzer.py` — optical flow, энергия 0..1);
- **CLIP-эмбеддинги** кадров (`clip_embedder.py`);
- **Золотые моменты** (`golden_moments.py` — интегральный скор эмоции+движения+редкости);
- **Оркестратор** `analyzer.py` (`MultiLayerAnalyzer`) — асинхронный запуск слоёв.
- Все слои — graceful fallback (модель недоступна → слой пропускается).

### `mod9_batch_processing` — пакетная обработка
`src/modules/mod9_batch_processing/`
- `processor.py` — `BatchProcessor`: асинхронная очередь, цепочка
  ingest→анализ→паттерны→сторибилдер→монтаж→экспорт, graceful shutdown.
- `composer.py` — `ClipComposer`: кластеризация фрагментов по CLIP-эмбеддингам
  и сборка **композиций** из похожих клипов.
- Создаёт записи `BatchJob` и привязывает видео к задаче.

### `mod10_final_features` — финальные фичи
`src/modules/mod10_final_features/`
- `color_grade.py` — **авто-цветокоррекция** по контексту сцены (энергичный/спокойный/тёмный/естественный);
- `transitions.py` — **умные переходы** (fade/zoom/spin/cut) по энергии сцен;
- `subtitles_style.py` — **субтитры с эмодзи** и стилями (ASS);
- `export_profiles.py` — **профили экспорта**: качество (HD/FHD/4K) и платформы
  (TikTok/Shorts/Reels/YouTube).

---

## Схема базы данных

Модели в `src/database/models.py` (SQLAlchemy 2.0, `Mapped`/`mapped_column`).

```
categories
├── id (PK)
├── name (unique)
├── description
└── parent_id (FK → categories.id)   # иерархия

videos
├── id (PK)
├── file_path (unique)
├── duration
├── resolution
├── category_id (FK → categories.id)
├── upload_date
├── status                    # uploaded / pending / processing / completed / composed / error ...
├── extra_metadata (JSON)     # "metadata" зарезервировано SQLAlchemy
├── analysis_results (JSON)   # результаты mod8
├── golden_moments (JSON)     # золотые моменты
└── batch_job_id (FK → batch_jobs.id)

learning_patterns
├── id (PK)
├── video_id (FK → videos.id)
├── category_id (FK → categories.id)
├── vector (JSON)             # признаки паттерна
├── structure / tempo / transitions / color_profile / music_profile (JSON)

processing_history
├── id (PK)
├── input_video_ids (JSON)
├── output_video_path
├── used_pattern_ids (JSON)
├── parameters (JSON)
├── status
├── started_at
└── finished_at

user_feedback
├── id (PK)
├── video_id (FK → videos.id, unique)
├── rating (1..5)
└── comment

frame_embeddings
├── id (PK)
├── video_id (FK → videos.id, CASCADE)
├── timestamp
└── embedding (JSON)          # CLIP-вектор

batch_jobs
├── id (PK)
├── folder_path
├── status                    # pending / processing / completed / error
├── total_videos
├── processed_videos
├── created_at
└── finished_at
```

**Связи:**
- `Category 1—N Video`, `Category 1—N LearningPattern`
- `Video 1—N LearningPattern`, `Video 1—N FrameEmbedding`, `Video 1—1 UserFeedback`
- `Video N—1 BatchJob`
- `Video N—1 Category` (через `category_id`)

---

## REST API

Базовый URL бэкенда: `http://127.0.0.1:8000`

### Категории
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/categories` | Создать категорию (Form: name, description?, parent_id?) |
| GET | `/api/categories` | Список категорий |
| GET | `/api/categories/{id}` | Получить категорию |
| PUT | `/api/categories/{id}` | Обновить категорию |
| DELETE | `/api/categories/{id}` | Удалить категорию |

### Видео
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/videos` | Создать запись видео |
| GET | `/api/videos` | Список видео (фильтры: category_id, status, batch_job_id) |
| GET | `/api/videos/{id}` | Получить видео |
| PATCH | `/api/videos/{id}/status` | Сменить статус |
| DELETE | `/api/videos/{id}` | Удалить видео |

### Анализ (mod8)
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/analysis/analyze/{id}` | Запустить анализ в фоне |
| GET | `/api/analysis/{id}` | Результаты анализа |
| GET | `/api/analysis/{id}/embeddings` | CLIP-эмбеддинги |

### Самообучение (mod7)
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/learning/train` | Запустить обучение категории (Form: category) |
| GET | `/api/learning/status` | Статус обучения |
| GET | `/api/learning/categories` | Обученные категории |
| GET | `/api/learning/profile/{category}` | Профиль категории |
| GET | `/api/learning/find_similar/{category}` | Поиск похожих (k) |
| POST | `/api/learning/extract` | Извлечь паттерны из загруженных файлов |

### Референсы и пайплайн (легаси web_ui)
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/upload_references` | Загрузить референсы в категорию |
| POST | `/api/train_links` | Обучиться по ссылкам (yt-dlp) |
| POST | `/api/analyze_style` | Анализ стиля категории |
| POST | `/api/upload_input` | Загрузить исходники |
| POST | `/api/start_pipeline` | Запустить пайплайн категории |

### Пакетная обработка (mod9)
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/batch/upload_folder` | Создать задачу из папки (Form: folder_path) |
| GET | `/api/batch/list` | Список задач (опц. ?status=) |
| POST | `/api/batch/process/{id}` | Запустить обработку в фоне |
| GET | `/api/batch/status/{id}` | Статус задачи |
| GET | `/api/batch/results/{id}` | Видео задачи и их статусы |

### Прочее
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/status` | Статус системы |
| WS | `/ws/logs` | WebSocket: логи в реальном времени |
| GET | `/` | Легаси-дашборд (web_ui) |

**Примеры:**

Создать пакетную задачу:
```bash
curl -X POST http://127.0.0.1:8000/api/batch/upload_folder \
  -F "folder_path=C:\MyVideos\Trip"
```

Запустить обработку:
```bash
curl -X POST http://127.0.0.1:8000/api/batch/process/3
```

Получить статус:
```bash
curl http://127.0.0.1:8000/api/batch/status/3
```

---

## Workflow обработки одного видео

Пакетная задача (`mod9`) вызывает полный конвейер `VideoPipeline.process_batch`
(`src/core/pipeline.py`). Для каждого кластера фрагментов выполняется:

```
1. КЛАСТЕРИЗАЦИЯ (mod9 / narrative_cluster)
   └��─ группировка фрагментов по смыслу/времени

2. СБОР ДАННЫХ (mod1_ingestion)
   └── метаданные, транскрипт, сцены, аудио по каждому фрагменту

3. НАРРАТИВ (story_builder / "mod2")
   └── тип истории, hook, цепочка, темп, удаление мусора
   └── (использует LLM Ollama/GigaChat/эвристику)

4. КОНКАТЕНАЦИЯ + ПЕРЕХОДЫ (mod5 + mod10 transitions)
   └── склейка фрагментов в исходный ролик, выбор типа перехода

5. АНАЛИЗ СЦЕН (mod8 / beat-sync)
   └── объединение транскриптов, определение длительности

6. МУЗЫКА (mod3_music_ai)
   └── подбор трека по настроению/длительности/BPM

7. МОНТАЖ (mod5_editing)
   └── beat-sync склейки, auto-reframe 9:16, Ken Burns, зум/фейды

8. ЦВЕТОКОРРЕКЦИЯ (mod10 color_grade)
   └── профиль по энергии/эмоциям сцены

9. СУБТИТРЫ (mod10 subtitles_style)
   └── ASS с эмодзи и стилями

10. ЭКСПОРТ (mod6_export + mod10 export_profiles)
    └── финальный рендер: видео + музыка + субтитры
    └── качество (HD/FHD/4K) и платформа (TikTok/Shorts/Reels)
```

После обработки `BatchProcessor` может **скомпоновать** похожие клипы в композицию
(`ClipComposer` по CLIP-эмбеддингам) и сохранить её как запись `videos` со статусом
`composed`.

---

## Как добавить новую модель ИИ

Архитектура спроектирована так, чтобы легко подключать новые ИИ-возможности.

### Паттерн «graceful fallback» (рекомендуется)
Все ML-слои (`mod8_analysis`) следуют паттерну: попробуем тяжёлую модель → при ошибке
используем запасной вариант или возвращаем пустой результат (не роняем пайплайн).

### Пример: добавить детектор жестов

1. **Создайте модуль** в `src/modules/mod8_analysis/gesture_detector.py`:
   ```python
   class GestureDetector:
       def __init__(self):
           self.available = False
           try:
               import mediapipe  # тяжёлая зависимость
               self._mp = mediapipe
               self.available = True
           except ImportError:
               pass

       def detect(self, frame):
           if not self.available:
               return []  # graceful fallback
           # ... реальная логика
           return [{"gesture": "wave", "conf": 0.9}]
   ```

2. **Добавьте слой в оркестратор** `src/modules/mod8_analysis/analyzer.py`:
   ```python
   from .gesture_detector import GestureDetector
   # в __init__: self.gesture = GestureDetector()
   # в analyze(): gestures = await asyncio.to_thread(self.gesture.detect, frame)
   # включите результаты в итоговый VideoAnalysisResult
   ```

3. **Добавьте поле в схему** `schemas.py` (Pydantic) и, если нужно, в БД.

4. **Зависимость** добавьте в `requirements.txt` как **опциональную**
   (extra-маркер), чтобы основной запуск не требовал её:
   ```
   mediapipe>=0.10 ; extra == "analysis"
   ```

5. **Используйте результат** в любом модуле (например, в `story_builder` или
   `color_grade`) через поле анализа.

### Ключевые принципы расширения
- **Модульность** — каждый слой в отдельном файле/классе.
- **Асинхронность** — тяжёлые модели запускаются через `asyncio.to_thread`.
- **Graceful fallback** — недоступность модели не роняет обработку.
- **Опциональные зависимости** — тяжёлые ML-пакеты не обязательны для базового запуска.
- **Логирование** — используйте `ws_manager.broadcast(...)` для логов в реальном времени.

---

Документация пользователя: [`USER_GUIDE.md`](USER_GUIDE.md).