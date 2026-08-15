# 🚀 Массовая обработка и композиция (Модуль 9)

Асинхронная пакетная обработка целых папок видео с автономной цепочкой:
**ingest → анализ → паттерны → нарратив → монтаж → экспорт**, плюс
композиция нескольких клипов из набора фрагментов по смысловой близости
(CLIP-кластеризация).

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
| **BatchProcessor** | Оркестратор: очередь видео из папки, цепочка шагов, статусы в БД, graceful shutdown |

### Цепочка обработки одного видео

```
ingest → анализ (mod8) → паттерны (mod7) → сторибилдер → монтаж → экспорт
```

- **Ingest** — нормализация видео через `mod0_ingest`.
- **Анализ** — многослойный анализ через `MultiLayerAnalyzer` (эмоции, объекты, движение, золотые моменты).
- **Паттерны** — поиск профиля самообучения для категории.
- **Нарратив** — `story_builder` с учётом «золотых моментов».
- **Монтаж/экспорт** — обёртка над основным пайплайном (fallback-копия).

### Graceful shutdown

`BatchProcessor.shutdown()` устанавливает флаг `stop_event`. Очередь
проверяет его перед каждым видео и корректно завершает обработку,
не прерывая уже запущенное видео.

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
Запускает `BatchProcessor.process_folder` в фоне (BackgroundTasks).

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
- graceful shutdown через `stop_event`.

Тесты используют моки и не требуют тяжёлых ML-моделей.