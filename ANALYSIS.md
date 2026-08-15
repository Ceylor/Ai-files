# 🧠 Многослойный анализ контента (Модуль 8)

Ультра-умный анализ каждого видеофайла: сцены, эмоции, лица, объекты,
движение, аудиоэнергия, текст. Автоматическое определение **«золотых
моментов»** — наилучших фрагментов для хука.

---

## 🏗 Архитектура

```
src/modules/mod8_analysis/
├── __init__.py           # публичный API
├── schemas.py            # pydantic-модели (EmotionalFrame, DetectedObject, ...)
├── emotion_detector.py   # эмоции лиц (DeepFace / FER) — graceful fallback
├── object_detector.py    # объекты (YOLO/ultralytics) — graceful fallback
├── motion_analyzer.py    # движение (optical flow, Farneback)
├── golden_moments.py     # «золотые моменты» (интегральный скор)
├── clip_embedder.py      # CLIP-эмбеддинги кадров
└── analyzer.py           # оркестратор MultiLayerAnalyzer
```

### Слои анализа

| Слой | Что даёт | Модель | Fallback |
|------|----------|--------|----------|
| 🎭 **Эмоции** | временные метки с эмоциями + confidence | DeepFace / FER | пустой список |
| 📦 **Объекты** | классы объектов + confidence | YOLOv8 (ultralytics) | пустой список |
| 🎥 **Движение** | «энергия движения» (0–1) | optical flow (Farneback) | пустой список |
| 💎 **Золотые моменты** | топ-3 фрагмента для хука | интегральный скор | пустой список |
| 🧬 **CLIP** | эмбеддинги кадров | openai/clip-vit-base-patch32 | пустой список |

### Золотые моменты (интегральный скор)

```
score = (эмоция + движение + редкость объекта) / 3
```

- **Эмоция**: радость/удивление/страх/злость повышают скор.
- **Движение**: высокая энергия optical flow повышает скор.
- **Редкость объекта**: person, dog, cat, car, fire и т.п. повышают скор.

Результат — топ-3 фрагмента с временными метками для хука.

---

## 🚀 Установка зависимостей

### Обязательные (для движения и инфраструктуры)
```bash
pip install opencv-python-headless numpy
```

### Опциональные слои (устанавливаются по желанию)

**Эмоции (DeepFace):**
```bash
pip install deepface
```
или **FER**:
```bash
pip install fer
```

**Объекты (YOLO):**
```bash
pip install ultralytics
```

**CLIP-эмбеддинги (torch + transformers):**
```bash
pip install torch torchvision transformers
```

> Все слои **graceful fallback**: если зависимость не установлена,
> слой пропускается, общий анализ не падает.

---

## 🔌 API

### Запуск анализа
```bash
# Асинхронный запуск полного анализа (BackgroundTasks)
curl -X POST http://127.0.0.1:8000/api/analysis/analyze/1

# Результаты анализа
curl http://127.0.0.1:8000/api/analysis/1

# CLIP-эмбеддинги кадров
curl http://127.0.0.1:8000/api/analysis/1/embeddings
```

### Результаты сохраняются в БД
- `Video.analysis_results` (JSON): эмоции, объекты, движение, статусы слоёв.
- `Video.golden_moments` (JSON): топ-3 фрагмента для хука.
- Таблица `frame_embeddings`: `(video_id, timestamp, embedding)`.

---

## 🎬 Интеграция с нарративом

`story_builder.py` принимает параметр `golden_moments` и выбирает хук
из топ-3 самых ярких фрагментов (см. `_apply_golden_moments`).

---

## 🧪 Тесты

```bash
python -m pytest tests/test_mod8_analysis.py -v
```

Тесты используют моки и не требуют тяжёлых ML-моделей.

---

## 📦 Миграции

Новая таблица `frame_embeddings` и поля анализа в `videos`:

```bash
alembic upgrade head
```