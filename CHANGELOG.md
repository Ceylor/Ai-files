# CHANGELOG

Все заметные изменения проекта документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

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