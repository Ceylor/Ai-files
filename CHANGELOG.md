# CHANGELOG

Все заметные изменения проекта документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

## [0.2.0] — Стадия 7: Самообучение на примерах (AI AutoClip Pro 2.0)

### Добавлено
- **`src/modules/mod7_learning/`** — новый модуль самообучения:
  - `pattern_models.py` — pydantic-модели «паттерна успеха» (структура, темп, переходы, цветокоррекция, музыка) + компактный вектор признаков (10 измерений);
  - `pattern_extractor.py` — извлечение паттернов из референсных клипов: цветокоррекция (OpenCV HSV-сэмплы), ритм/структура/переходы (content-based детекция сцен), музыка (BPM/энергия/Camelot через `audio_analyzer`). Graceful-fallback для всех тяжёлых анализаторов;
  - `vector_store.py` — векторное хранилище с graceful-fallback: FAISS → ChromaDB → NumPy (in-memory cosine). Персистентность в `data/learning_store` (patterns.json + vectors.npy), переживает перезапуск (непрерывное обучение);
  - `learner.py` — оркестратор `LearningEngine`: обучение по папке категории, поиск похожих паттернов (с фильтром по категории), агрегированный профиль стиля категории.
- **REST API** (`src/api/main.py`) — новые эндпоинты:
  - `POST /api/learning/train` — запуск самообучения по категории;
  - `GET /api/learning/status` — статус движка (бэкенд, число паттернов, категории);
  - `GET /api/learning/categories` — список обученных категорий;
  - `GET /api/learning/profile/{category}` — агрегированный профиль стиля;
  - `GET /api/learning/find_similar/{category}` — k ближайших «паттернов успеха»;
  - `POST /api/learning/extract` — извлечение паттерна из загруженного видео без сохранения.
- **`tests/test_mod7_learning.py`** — юнит-тесты на синтетических видео (FFmpeg):
  - извлечение паттерна (все слои + вектор 10 измерений);
  - graceful-fallback для несуществующего файла;
  - нормализация вектора признаков в [0,1];
  - векторное хранилище (numpy fallback): add/search/persist/load/clear, проверка размерности;
  - оркестратор: обучение по папке, статусы, профиль категории, поиск с фильтром.
- **`requirements.txt`** — опциональные ускорители векторного поиска `faiss-cpu` / `chromadb` (extra-маркеры; система работает и без них).

### Изменено
- **`src/api/main.py`** — подключён `LearningEngine`, эндпоинт `/api/status` возвращает статистику обучения.
- **`CHANGELOG.md`** — раздел стадии 7.

### Примечания
- Модуль модульный и не требует тяжёлых ML-зависимостей (FAISS/Chroma — опциональные ускорители; numpy-fallback всегда доступен).
- Паттерны персистентны: накопленный опыт переживает перезапуск сервиса (непрерывное самообучение).
- Документация: см. `SELF_LEARNING.md`.

## [0.1.0] — Стадия 1: Ингестия и нормализация (mod0_ingest)

### Добавлено
- **`src/modules/mod0_ingest.py`** — новый модуль ингестии:
  - сбор ffprobe-метаданных (кодек, разрешение, fps, rotation, длительность, наличие аудио);
  - авто-поворот кадра по метаданным rotate/EXIF (transpose);
  - нормализация fps/размера: приведение к целевым 30 fps и 1080x1920 через pad (не теряет контент);
  - интерполяция fps через `minterpolate` для 24/25 fps (опция `ingest.interpolate`);
  - извлечение аудио (PCM mono) для последующих стадий (whisper, beat-анализ);
  - graceful fallback: битый/нечитаемый файл не роняет обработку, логируется и пропускается;
  - dry-run режим `--analyze-only`: JSON-отчёт о входных файлах без обработки;
  - CLI-точка входа `python -m src.modules.mod0_ingest [--analyze-only] <input_dir>`.
- **`tests/test_mod0_ingest.py`** — юнит-тесты на синтетических видео (FFmpeg testsrc + sine):
  - проверка сбора метаданных;
  - проверка нормализации разрешения до 1080x1920;
  - проверка извлечения аудио;
  - graceful fallback для отсутствующего/битого файла;
  - проверка dry-run отчёта;
  - fallback-конфигурация по умолчанию.
- **`pytest.ini`** — конфигурация pytest (asyncio_mode=auto, testpaths=tests).
- **`requirements.txt`** — добавлены `pytest>=8.0.0` и `pytest-asyncio>=0.23.0`.

### Изменено
- **`configs/config.yaml`** — добавлена секция `ingest` с настройками нормализации.

### Примечания
- Код использует `pathlib.Path`, pydantic-модель `IngestConfig` (не dict), логирование через `logging`.
- Тяжёлые ML-зависимости (torch/ultralytics/open_clip) НЕ добавлены — реализованы graceful fallback в последующих стадиях (MediaPipe/ONNX).

## [0.0.1] — Базовый проект AI AutoClip Pro

- Исходная структура репозитория (src/modules, src/utils, src/core, configs, assets, web_ui).
- Существующие модули mod1..mod6, пайплайн, Web UI.