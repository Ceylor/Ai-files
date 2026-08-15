# 🚀 Массовая обработка и композиция (Модуль 9)

Асинхронная пакетная обработка целых папок видео с автономной цепочкой:
**ingest → анализ → паттерны → нарратив → монтаж → экспорт**, плюс
композиция нескольких клипов из набора фрагментов по смысловой близости
(CLIP-кластеризация) с сохранением результата в БД.

---

## 🏗 Архитектура

```
src/modules/mod9_batch_processing/
├── __init__.py           # публичный API (ClipComposer, BatchProcessor)
├── composer.py           # ClipComposer: кластеризация CLIP + объединение в клипы
└── processor.py          # BatchProcessor: асинхронная очередь пакетной обработки
```

### Компоненты

| Компонент | Что делает |
|-----------|------------|
| **ClipComposer** | Кластеризует фрагменты по средним CLIP-эмбеддингам (косинусное сходство), создаёт планы нескольких клипов |
| **BatchProcessor** | Оркестратор: очередь видео из папки, цепочка шагов, статусы в БД, graceful shutdown, композиция и сохранение результата |

### Цепочка обработки одного видео

```
ingest → анализ (mod8) → паттерны (mod7) → сторибилдер → монтаж → экспорт
```

- **Ingest** — нормализация видео через `mod0_ingest`.
- **Анализ** — многослойный анализ через `MultiLayerAnalyzer` (эмоции, объекты, движение, золотые моменты).
- **Паттерны** — поиск профиля самообучения для категории.
- **Нарратив** — `story_builder` с учётом «золотых моментов».
- **Монтаж** — **реальный монтаж** через `VideoPipeline.process_batch` (модули mod1–mod6), с graceful fallback на копирование исходника при сбое.

### Композиция клипов (после обработки всех видео)

`BatchProcessor` собирает CLIP-эмбеддинги обработанных видео, вызывает
`ClipComposer.compose_clips()` и сохраняет созданные композиции в БД как
новые записи `videos` со статусом `composed`, привязанные к `batch_job_id`.

### Graceful shutdown

`BatchProcessor.shutdown()` устанавливает флаг `stop_event`. Очередь
проверяет его перед каждым видео и корректно завершает обработку,
не прерывая уже запущенное видео. При остановке композиция не запускается.

---

## 🗄 Данные в БД

Новая таблица **`batch_jobs`** и поле **`videos.batch_job_id`**:

| Поле | Описание |
|------|----------|
| `folder_path` | Папка с исходными видео |
| `status` | `pending` / `processing` / `completed` / `error` |
| `total_videos` | Всего видео в задаче |
| `processed_videos` | Сколько успешно обработано |
| `created_at` / `finished_at` | Время создания и завершения |

Каждое видео пакетной задачи привязывается к `batch_jobs.id` через
`videos.batch_job_id` (FK, `ON DELETE SET NULL`).

Созданные композиции сохраняются в `videos` со статусом `composed`; в
`extra_metadata` хранится `{ "kind": "composed", "name": ..., "source_video_ids": [...] }`.

Миграция:

```bash
alembic upgrade head
```

---

## 🔌 API

### Зарегистрировать папку (создать пакетную задачу)
```bash
curl -X POST http://127.0.0.1:8000/api/batch/upload_folder \
  -d "folder_path=/path/to/videos"
```
Сканирует папку на видео (`mp4/mov/avi/mkv/webm/m4v`), создаёт `BatchJob`
и регистрирует найденные файлы как `pending`-записи `Video`.

### Запустить обработку
```bash
curl -X POST http://127.0.0.1:8000/api/batch/process/1
```
Запускает `BatchProcessor.process_folder` в фоне (BackgroundTasks). После
обработки всех видео выполняет композицию клипов и сохраняет их в БД.

### Статус задачи
```bash
curl http://127.0.0.1:8000/api/batch/status/1
```

### Результаты (видео и их статусы)
```bash
curl http://127.0.0.1:8000/api/batch/results/1
```

---

## 🧪 Тесты

```bash
python -m pytest tests/test_mod9_batch_processing.py -v
```

Покрытие:
- кластеризация `ClipComposer` (похожие фрагменты, лимит размера);
- `compose_clips` — создание нескольких планов клипов;
- `group_by_time` — fallback-группировка без CLIP;
- `process_folder` — очередь с моками шагов;
- graceful shutdown через `stop_event`;
- `_run_editing` — реальный монтаж через `VideoPipeline` и fallback-копия;
- `_compose_and_save` — сохранение композиций в БД.

Тесты используют моки и не требуют тяжёлых ML-моделей.