# ДЕТАЛЬНЫЙ АНАЛИЗ И ПЛАН РАЗВИТИЯ AI AutoClip Pro 2.0

> Составлен: 31.08.2026 | Автор: Senior Software Architect & Lead AI Engineer
> Метод: полное изучение исходников + сравнение с 11 эталонными репозиториями

---

## 1. ОБЩЕЕ ВПЕЧАТЛЕНИЕ

**Оценка: 7/10** — амбициозный проект с впечатляющим набором фич, но с серьёзными архитектурными проблемами, которые мешают продакшен-использованию.

**Что работает хорошо:**
- Многослойный анализ (7 слоёв) — лучший в open-source классе
- Самообучение на референсах — уникальная фича, которую не делает почти никто
- Beat-synced editing с нарративным сторителлингом
- Graceful fallback на каждом уровне ( DeepFace → FER → пустой список)
- WebSocket логи в реальном времени

**Что вызывает вопросы:**
- `main.py` на 1092 строки — монолит, который нужно разбивать
- Нет proper memory management — на длинных видео будет OOM
- Отсутствие GPU detection / CPU-only режима
- Нет retry/resume для пайплайна — сбой = потеря всей работы
- Фронтенд на 6 страниц без типизации (plain JS)

---

## 2. АРХИТЕКТУРА

### 2.1 Бэкенд (FastAPI)

**Оценка: 6/10**

**Сильные стороны:**
- Чистая модульная структура `src/modules/` с нумерацией (mod0-mod10)
- Graceful fallback для всех ML-моделей (YOLO, DeepFace, CLIP)
- Pydantic модели в `schemas.py` для валидации
- Rate limiting на критических эндпоинтах
- WAL-режим SQLite

**Слабые стороны:**

1. **`main.py` — God Object (1092 строк)**
   - Включает: CRUD для категорий/видео, анализ, обучение, пакетную обработку, загрузку ссылок, пайплайн, статистику
   - Должен быть разбит на роутеры: `categories.py`, `videos.py`, `analysis.py`, `learning.py`, `batch.py`, `pipeline.py`
   - **Рекомендация:** Использовать `APIRouter` для каждого домена

2. **Нет proper error recovery**
   - `run_analysis_task`, `run_learning_task`, `run_full_pipeline_task` — все используют `asyncio.create_task()` без отслеживания
   - Если пайплайн падает на 5-м видео из 10 — вся задача теряется
   - **Рекомендация:** Добавить checkpoint/resume в pipeline, persistent task tracking

3. **Memory management**
   - `BatchProcessor` загружает все видео сразу
   - Нет лимита на одновременную обработку
   - CLIP-эмбеддинги хранятся в памяти без лимита
   - **Рекомендация:** Generator-based processing, max_workers лимит, streaming embeddings

4. **Sync operations в async контексте**
   - `db_crud` вызовы блокируют event loop (SQLAlchemy синхронный)
   - FFmpeg команды через `asyncio.create_subprocess_exec` — это ок, но утечки памяти возможны
   - **Рекомендация:** Перейти на `async SQLAlchemy` или `run_in_executor`

### 2.2 Пайплайн (pipeline.py)

**Оценка: 7.5/10**

**Сильные стороны:**
- 6-шаговый пайплайн: кластеризация → ингестия → музыка → монтаж → субтитры → экспорт
- Нарративный сторителлинг через `story_builder`
- Интеграция с mod10 (цветокоррекция, переходы, emoji-субтитры)
- CLIP-кластеризация для объединения видео

**Слабые стороны:**
- Нет промежуточного сохранения (checkpoint) между шагами
- `_process_cluster` создает временные файлы, но не всегда очищает их
- Нет retry для FFmpeg операций
- Hardcoded лимиты (200 beat_times, 20 drop_times)

### 2.3 Фронтенд (Next.js)

**Оценка: 6.5/10**

**Сильные стороны:**
- Киберпанк-дизайн с glassmorphism
- Framer Motion анимации
- WebSocket для реального времени
- ThemeProvider для тёмной/светлой темы
- Timeline компонент для визуализации

**Слабые стороны:**
- TypeScript в devDeps, но страницы на `.js` — нет типизации
- Нет React Query / SWR для кеширования API-запросов
- Нет proper error boundaries
- Нет loading skeletons
- Нет optimisic updates
- `api.js` — 139 строк без типизации
- Нет E2E тестов

### 2.4 База данных (SQLite + Alembic)

**Оценка: 7/10**

**Сильные стороны:**
- 4 миграции с индексами
- WAL-режим
- `session_scope` контекстный менеджер
- Корректные FK constraints

**Слабые стороны:**
- SQLite — не масштабируется (но для single-user ок)
- Нет connection pooling для concurrent requests
- JSON поля для analysis_results/golden_moments — сложные запросы
- Нет soft delete

### 2.5 Тесты (pytest)

**Оценка: 7/10**

**Сильные стороны:**
- 113 тестов — хорошее покрытие
- Тесты для API, безопасности, экспорта, модулей
- Моки для ML-моделей

**Слабые стороны:**
- Нет E2E тестов (end-to-end pipeline)
- Нет нагрузочных тестов
- Нет тестов для фронтенда
- Нет тестов для WebSocket

---

## 3. СРАВНЕНИЕ С ЭТАЛОННЫМИ РЕПОЗИТОРИЯМИ

### 3.1 Что можно позаимствовать из artbyjazi/autoclip

| Фича | Описание | Приоритет |
|------|----------|-----------|
| **Word-index timing** | LLM работает с индексами слов, а не с временными метками — точнее и надёжнее | Высокий |
| **Resumable pipeline** | Каждый шаг записывает артефакт; при сбое возобновляется с первого недостающего | Высокий |
| **Per-shot crop paths** | Каждый кадр кадрируется отдельно (без интерполяции через склейку) | Средний |
| **Functional hardware probing** | `autoclip doctor` проверяет НЕ только наличие GPU, а возможность КОДИРОВАНИЯ | Высокий |
| **VAD trimming** | Voice Activity Detection перед декодированием — ускоряет и предотвращает галлюцинации Whisper | Средний |
| **Compute-type-by-hardware** | Выбор `int8_float16` vs `float16` на основе compute capability GPU | Средний |
| **Retry-with-feedback** | При ошибке валидации LLM-ответа — повтор с указанием ошибки | Средний |
| **Overlapping windows** | Транскрипция длинных видео по окнам с 60с перекрытием | Высокий |

### 3.2 Что можно позаимствовать из zhouxiaoka/autoclip

| Фича | Описание | Приоритет |
|------|----------|-----------|
| **Celery/Redis очередь** | Горизонтальное масштабирование обработки | Средний |
| **Per-chunk resilience** | Каждый 30-мин чанк обрабатывается независимо | Высокий |
| **LLM response caching** | Кеш ответов LLM для повторных вызовов | Средний |
| **Multi-layer JSON parser** | 5-уровневый fallback парсинга LLM-ответов | Средний |
| **Bilibili integration** | Поддержка B站 (массовый рынок) | Низкий |
| **Tauri desktop** | Нативное десктопное приложение | Низкий |

### 3.3 Что можно позаимствовать из notivn/AIEV

| Фича | Описание | Приоритет |
|------|----------|-----------|
| **Skills system** | Накопленные знания как markdown-файлы | Средний |
| **Brand logo auto-fetch** | Авто-поиск и кеширование логотипов | Низкий |
| **Phone upload via QR** | Загрузка видео с телефона через QR + Cloudflare Tunnel | Средний |
| **GPU/CPU split per stage** | Детальный контроль: browser GPU, encode GPU, transcribe GPU | Высокий |
| **Pre-render validation** | Валидация перед рендером (проверка that render won't waste GPU) | Средний |

### 3.4 Что можно позаимствовать из zhangzhanglaila/ai-montage-agent

| Фича | Описание | Приоритет |
|------|----------|-----------|
| **5-axis highlight scoring** | Motion(25%) + Shot diversity(20%) + Face(25%) + Camera(15%) + Audio(15%) | Средний |
| **Beat-count quantization** | Длительность кадра = N битов (не просто выравнивание) | Средний |
| **Cross-video shot balancing** | Чередование кадров из разных видео | Низкий |
| **Timeline export (EDL/XML)** | Экспорт в форматы Premiere/DaVinci | Низкий |
| **LLM natural language control** | Превращение промпта в параметры пайплайна | Средний |
| **BGM auto-download** | Поиск музыки по стилю на Bilibili | Низкий |

---

## 4. СИЛЬНЫЕ СТОРОНЫ (что уже сделано отлично)

1. **Уникальная многослойная система анализа** — 7 слоёв (аудио, движение, эмоции, объекты, смена планов, биты, яркость) — нет аналогов в open-source с таким покрытием
2. **Самообучение на референсах** — LearningEngine с FAISS/ChromaDB векторным поиском — концепция, которую делает только OpenMontage (и то иначе)
3. **Beat-synced editing с нарративом** — `story_builder.py` строит нарративную структуру + `mod5_editing.py` синхронизирует с битами — это то, что делает beat-synced-edit, но сضافadded narrative layer
4. **Graceful fallback на каждом уровне** — DeepFace → FER → пустой список; YOLO → пустой список; FAISS → ChromaDB → NumPy — это production-ready подход
5. **CLIP-кластеризация видео** — `composer.py` объединяет 30+ видео по темам через эмбеддинги — уникальная фича
6. **WebSocket в реальном времени** — `ws_manager` для логов + `batch_ws_manager` для пакетной обработки
7. **Нарративный сторителлинг** — `story_builder.py` с золотыми моментами, hook detection, chain structure
8. **Экспортные профили** — TikTok/Shorts/Reels/YouTube + HD/FHD/4K пресеты
9. **Цветокоррекция и переходы** — mod10 с auto-grading и smart transitions
10. **113 тестов** — хорошее покрытие для open-source проекта

---

## 5. СЛАБЫЕ СТОРОНЫ (что можно улучшить)

### Критические (блокируют продакшен)

1. **Нет memory management** — OOM на длинных видео (>1ч)
   - CLIP-эмбеддинги хранятся в памяти
   - BatchProcessor не имеет лимита параллельной обработки
   - Нет streaming/generator паттерна для больших видео

2. **Нет GPU detection** — система крашится без GPU при попытке CUDA-операций
   - Нет проверки `torch.cuda.is_available()`
   - Нет fallback на CPU для YOLO/DeepFace/CLIP
   - NVENC fallback в mod6_export есть, но нет в анализе

3. **`main.py` — монолит (1092 строки)** — нарушение SRP
   - Нужно разбить на APIRouter'ы
   - CRUD-операции смешаны с бизнес-логикой

4. **Нет checkpoint/resume** — сбой = потеря всей работы
   - Pipeline не сохраняет промежуточные результаты
   - Batch processing не имеет retry

### Важные (снижают качество)

5. **SQLAlchemy sync в async контексте** — блокирует event loop
6. **Нет proper cleanup temp файлов** — утечка дискового пространства
7. **Hardcoded параметры** — нет API для изменения весов скоринга
8. **Нет proper logging** — traceback.print_exc() вместо structured logging
9. **Фронтенд без TypeScript** — потеря типизации
10. **Нет health check endpoint** — только `/api/status` без проверки зависимостей

### Средние (снижают UX)

11. **Нет progress tracking для анализа** — пользователь не видит прогресс
12. **Нет cancellation** — нельзя отменить задачу
13. **Нет priority queue** — все задачи равноприоритетны
14. **Нет notification system** — нет email/webhook уведомлений
15. **Нет rate limiting для batch операций** — только для upload

---

## 6. ОПТИМИЗАЦИЯ ДЛЯ СЛАБЫХ ПК

### 6.1 Ограничение RAM (целевое: 4-6 ГБ в пике)

**Текущая проблема:**
- CLIP-эмбеддинги для全长 видео могут занимать 2+ ГБ
- PySceneDetect загружает весь кадр в память
- faster-whisper загружает модель (~1-2 ГБ)
- YOLO/DeepFace модели загружаются одновременно

**Решения:**

```python
# 1. Streaming processing для длинных видео
async def process_video_streaming(video_path, chunk_size=300):
    """Обработка видео по частям (по 5 минут)"""
    total_duration = get_video_duration(video_path)
    for start in range(0, total_duration, chunk_size):
        end = min(start + chunk_size, total_duration)
        chunk = extract_video_chunk(video_path, start, end)
        yield await process_chunk(chunk)
        del chunk  # Принудительная очистка
        gc.collect()

# 2. Lazy loading моделей
class LazyModelLoader:
    def __init__(self):
        self._models = {}
    
    def get(self, model_name):
        if model_name not in self._models:
            self._models[model_name] = load_model(model_name)
        return self._models[model_name]
    
    def unload(self, model_name):
        if model_name in self._models:
            del self._models[model_name]
            gc.collect()

# 3. LRU cache для embeddings
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_clip_embedding(frame_path):
    # ...
```

**Конкретные изменения:**
- `mod8_analysis/analyzer.py`: обрабатывать видео по 30-секундным чанкам
- `mod9_batch_processing/processor.py`: обрабатывать одно видео за раз (не параллельно)
- `mod1_ingestion.py`: VAD trimming перед Whisper (экономит 30-50% RAM)
- `clip_embedder.py`: batch size = 1 на слабых ПК, streaming embeddings

### 6.2 Использование GPU (только когда доступно)

**Текущая проблема:**
- `import torch` в requirements.txt может крашнуться без CUDA
- Нет проверки доступности GPU перед использованием
- NVENC fallback только в mod6_export

**Решения:**

```python
# src/utils/gpu_detector.py (НОВЫЙ ФАЙЛ)
import logging

logger = logging.getLogger(__name__)

class GPUDetector:
    """Определение доступности GPU и выбор оптимального compute mode."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._detect()
        return cls._instance
    
    def _detect(self):
        self.cuda_available = False
        self.gpu_name = None
        self.compute_capability = None
        
        try:
            import torch
            if torch.cuda.is_available():
                self.cuda_available = True
                self.gpu_name = torch.cuda.get_device_name(0)
                cc = torch.cuda.get_device_capability(0)
                self.compute_capability = cc
                # pre-Volta (CC < 7.0) не поддерживает fp16 тензоры
                self.fp16_available = cc[0] >= 7
                logger.info(f"GPU detected: {self.gpu_name}, CC={cc}, FP16={'yes' if self.fp16_available else 'no'}")
            else:
                logger.info("CUDA not available, using CPU")
        except ImportError:
            logger.info("PyTorch not installed, using CPU")
    
    def get_compute_type(self):
        """Выбор compute type на основе hardware."""
        if not self.cuda_available:
            return "int8"  # CPU
        if self.fp16_available:
            return "float16"
        return "int8_float16"  # pre-Volta
    
    def get_whisper_device(self):
        return "cuda" if self.cuda_available else "cpu"
    
    def get_yolo_device(self):
        return "0" if self.cuda_available else "cpu"
```

**Конкретные изменения:**
- Добавить `gpu_detector.py` в `src/utils/`
- `mod1_ingestion.py`: использовать `GPUDetector().get_whisper_device()`
- `mod8_analysis/object_detector.py`: использовать `GPUDetector().get_yolo_device()`
- `mod8_analysis/clip_embedder.py`: lazy load с device detection
- `mod6_export.py`: уже имеет NVENC fallback — оставить как есть

### 6.3 Ускорение на старых CPU (Xeon E5 2650v2)

**Текущая проблема:**
- Optical flow (Farneback) — тяжёлая операция на CPU
- YOLO inference на CPU медленный
- librosa beat detection может быть медленным

**Решения:**

```python
# 1. Уменьшенное разрешение для анализа
ANALYSIS_RESOLUTIONS = {
    "fast": (320, 180),      # Быстрый режим
    "normal": (640, 360),    # Нормальный
    "quality": (1280, 720),  # Высокое качество
}

# 2. Оптимизация FFmpeg для слабых CPU
WEAK_CPU_FFMPEG_PARAMS = [
    "-preset", "ultrafast",  # Быстрейший пресет
    "-tune", "zerolatency",  # Минимальная задержка
    "-threads", "4",         # Лимит потоков
    "-x264-params", "ref=1:bframes=0",  # Минимальная сложность
]

# 3. Paralllelism с лимитом
import multiprocessing
CPU_COUNT = multiprocessing.cpu_count()
OPTIMAL_WORKERS = min(CPU_COUNT // 2, 4)  # Не более 4 воркеров
```

**Конкретные изменения:**
- `mod0_ingest.py`: добавить параметр `resolution` в FFmpeg команды
- `mod8_analysis/motion_analyzer.py`: уменьшать разрешение перед optical flow
- `pipeline.py`: добавить параметр `performance_mode` (fast/normal/quality)
- `main.py`: добавить query parameter `fast_mode` во все analysis endpoints

### 6.4 Рекомендуемые настройки по умолчанию для слабых ПК

```json
{
  "performance_mode": "fast",
  "max_concurrent_videos": 1,
  "analysis_resolution": "320x180",
  "whisper_model": "tiny",
  "whisper_compute_type": "int8",
  "yolo_model": "yolov8n",
  "clip_batch_size": 1,
  "scene_detection_threshold": 30,
  "max_beat_times": 100,
  "ffmpeg_preset": "ultrafast",
  "cleanup_temp": true,
  "max_ram_mb": 4096
}
```

### 6.5 Обработка длинных видео (избежание OOM)

```python
# Стратегия: chunk-based processing
class LongVideoProcessor:
    """Обработка видео длиннее 30 минут по частям."""
    
    CHUNK_DURATION = 300  # 5 минут
    
    async def process(self, video_path):
        duration = get_duration(video_path)
        if duration <= self.CHUNK_DURATION:
            return await self._process_full(video_path)
        
        # Разбиваем на чанки
        chunks = []
        for start in range(0, duration, self.CHUNK_DURATION):
            end = min(start + self.CHUNK_DURATION, duration)
            chunk_path = self._extract_chunk(video_path, start, end)
            chunks.append(chunk_path)
        
        # Обрабатываем каждый чанк
        results = []
        for chunk in chunks:
            result = await self._process_full(chunk)
            results.append(result)
            self._cleanup(chunk)  # Удаляем чанк после обработки
        
        # Объединяем результаты
        return self._merge_results(results)
```

---

## 7. ПЛАН РАЗВИТИЯ (приоритеты)

### 7.1 Высокий приоритет (0-2 месяца)

| # | Задача | Описание | Файлы |
|---|--------|----------|-------|
| 1 | **GPU/CPU detection** | `gpu_detector.py` + интеграция во все модули ML | `src/utils/gpu_detector.py` (новый), `mod1_ingest.py`, `mod8_analysis/*.py` |
| 2 | **Memory management** | Streaming processing, lazy model loading, LRU cache для embeddings | `mod8_analysis/analyzer.py`, `mod9_batch_processing/processor.py`, `clip_embedder.py` |
| 3 | **Refactor main.py** | Разбить на APIRouter'ы: categories, videos, analysis, learning, batch | `src/api/main.py` → `src/api/routers/*.py` |
| 4 | **Resumable pipeline** | Checkpoint между шагами, retry для FFmpeg | `src/core/pipeline.py` |
| 5 | **Overlapping windows для длинных видео** | Транскрипция по 8-мин окнам с перекрытием | `mod1_ingestion.py` |
| 6 | **Performance config** | JSON-конфиг с параметрами для слабых/средних/сильных ПК | `configs/performance.json` (новый), `config_loader.py` |

### 7.2 Средний приоритет (2-4 месяца)

| # | Задача | Описание | Файлы |
|---|--------|----------|-------|
| 7 | **Async SQLAlchemy** | Перейти на async engine для неблокирующих DB-операций | `database/session.py`, `database/crud.py` |
| 8 | **Health check endpoint** | Проверка FFmpeg, yt-dlp, GPU, disk space, RAM | `src/api/main.py` → `/api/health` |
| 9 | **Structured logging** | Заменить `traceback.print_exc()` на proper logging | Все файлы |
| 10 | **Frontend TypeScript** | Конвертировать `.js` → `.tsx`, добавить типы API | `frontend/app/*.js`, `frontend/lib/api.js` |
| 11 | **React Query / SWR** | Кеширование API-запросов, optimistic updates | `frontend/lib/api.js` |
| 12 | **Progress tracking** | WebSocket прогресс для анализа и обучения | `mod8_analysis/analyzer.py`, `mod7_learning/learner.py` |
| 13 | **Cancellation support** | Отмена задач через API | `src/api/main.py`, `mod9_batch_processing/processor.py` |
| 14 | **Cleanup temp files** | Автоочистка temp директорий | `pipeline.py`, `mod9_batch_processing/processor.py` |
| 15 | **Word-index timing** | LLM работает с индексами слов (как artbyjazi) | `narrative_cluster.py`, `story_builder.py` |

### 7.3 Низкий приоритет (4+ месяцев)

| # | Задача | Описание | Файлы |
|---|--------|----------|-------|
| 16 | **Per-shot crop paths** | Каждый кадр кадрируется отдельно (как artbyjazi) | `mod5_editing.py` |
| 17 | **Timeline export (EDL/XML)** | Экспорт в форматы Premiere/DaVinci | `mod6_export.py` |
| 18 | **Beat-count quantization** | Длительность кадра = N битов | `mod5_editing.py` |
| 19 | **LLM response caching** | Кеш ответов LLM для повторных вызовов | `narrative_cluster.py` |
| 20 | **BGM auto-download** | Поиск музыки по стилю | `mod3_music_ai.py` |
| 21 | **Notification system** | Email/webhook уведомления о завершении | `src/utils/notifications.py` (новый) |
| 22 | **E2E тесты** | End-to-end тесты пайплайна | `tests/test_e2e.py` (новый) |
| 23 | **Docker support** | Docker Compose для развёртывания | `Dockerfile`, `docker-compose.yml` |
| 24 | **Redis/Celery queue** | Горизонтальное масштабирование | `src/worker/` (новый) |
| 25 | **Tauri desktop** | Нативное десктопное приложение | `src-tauri/` (новый) |

---

## 8. РЕКОМЕНДАЦИИ ПО КОДУ

### 8.1 Критические исправления

**`src/api/main.py:1-1092`** — Разбить на роутеры:
```
src/api/
├── main.py              # Только app setup, lifespan, CORS
├── routers/
│   ├── __init__.py
│   ├── categories.py    # CRUD категорий (строки 100-160)
│   ├── videos.py        # CRUD видео (строки 162-220)
│   ├── analysis.py      # Анализ (строки 222-300)
│   ├── learning.py      # Обучение (строки 302-400)
│   ├── batch.py         # Пакетная обработка (строки 400-600)
│   ├── upload.py        # Загрузка файлов (строки 600-700)
│   └── pipeline.py      # Запуск пайплайна (строки 700-800)
```

**`src/core/pipeline.py:1-405`** — Добавить checkpoint:
```python
# После каждого шага сохранять состояние
async def _process_cluster(self, ...):
    checkpoint_file = cluster_temp / "checkpoint.json"
    # Загрузить состояние если есть
    state = load_checkpoint(checkpoint_file) if checkpoint_file.exists() else {}
    
    # Шаг 1: если не выполнен
    if "step1_done" not in state:
        fragments_data = await self._collect_fragments(...)
        save_checkpoint(checkpoint_file, {"step1_done": True, "fragments": fragments_data})
    
    # Шаг 2: если не выполнен
    if "step2_done" not in state:
        story = await self._build_narrative(fragments_data, ...)
        save_checkpoint(checkpoint_file, {"step2_done": True, "story": story})
    # ... и так далее
```

**`src/modules/mod8_analysis/analyzer.py`** — Добавить memory management:
```python
async def analyze(self, video_path, video_id=None):
    # Lazy load моделей
    from src.utils.gpu_detector import GPUDetector
    gpu = GPUDetector()
    
    # Освободить память перед анализом
    import gc
    gc.collect()
    
    # Обработка по чанкам для длинных видео
    duration = get_video_duration(video_path)
    if duration > 600:  # >10 минут
        return await self._analyze_chunked(video_path, video_id)
    
    # Обычный анализ
    return await self._analyze_full(video_path, video_id)
```

### 8.2 Улучшения производительности

**`src/modules/mod1_ingestion.py`** — Добавить VAD trimming:
```python
async def _transcribe_audio(self, audio_path):
    # VAD trimming перед транскрипцией (экономит 30-50% времени)
    from faster_whisper import VADFilter
    # ... существующий код
```

**`src/modules/mod8_analysis/motion_analyzer.py`** — Уменьшение разрешения:
```python
async def analyze_motion(self, video_path):
    # Уменьшить разрешение для анализа движения
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", "scale=320:180",  # Анализ на малом разрешении
        "-f", "rawvideo", "-pix_fmt", "gray", "-"
    ]
```

**`src/modules/mod8_analysis/clip_embedder.py`** — Streaming embeddings:
```python
async def embed_frames(self, frames):
    # Batch processing вместо по одному
    batch_size = self._get_batch_size()  # 1 на слабых, 8 на сильных
    for i in range(0, len(frames), batch_size):
        batch = frames[i:i+batch_size]
        embeddings = self.model(batch)
        yield embeddings
        # Очистка после каждого batch
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
```

---

## 9. ИТОГОВАЯ ОЦЕНКА

- **Общий рейтинг:** 7/10
- **Готовность к продакшену:** Нет (с оговорками)
  - Для single-user/home use — да, с ограничениями
  - Для multi-user/SaaS — нет (нужен Redis/Celery, async DB, memory management)
  - Для слабых ПК — нет (нужен GPU detection, performance modes, chunk processing)

### Ключевые риски:

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| OOM на длинных видео | Высокое | Критическое | Streaming processing, chunk-based analysis |
| Краш без GPU | Высокое | Высокое | GPU detection, CPU fallback |
| Главный поток блокируется sync DB | Среднее | Высокое | Async SQLAlchemy |
| main.py ломается при изменениях | Среднее | Среднее | APIRouter refactoring |
| Временные файлы заполняют диск | Среднее | Среднее | Auto cleanup, disk space check |
| LLM галлюцинации в нарративе | Низкое | Среднее | Word-index timing (artbyjazi approach) |

---

*Анализ составлен на основе полного изучения исходников AI AutoClip Pro 2.0 и 11 эталонных репозиториев: artbyjazi/autoclip, zhouxiaoka/autoclip, notivn/AIEV, zhangzhanglaila/ai-montage-agent, ttfake92-lab/OpenMontage, linyqh/NarratoAI, vizionik25/moviepy-mcp, ZiadAbdelkarim/beat-synced-edit, GordeyZuev/LEAP, superyngo/ffmpeg_toolkit.*
