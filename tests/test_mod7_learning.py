"""
Тесты модуля 7: САМООБУЧЕНИЕ НА ПРИМЕРАХ.

Проверяют:
    - извлечение паттерна из синтетического видео (все слои заполнены);
    - построение вектора признаков (размерность и нормализация);
    - работу векторного хранилища (numpy fallback): add/search/persist/load/clear;
    - оркестратор LearningEngine: обучение, поиск похожих, агрегированный профиль;
    - graceful-fallback при отсутствии тяжёлых бэкендов (faiss/chroma).

Запуск:
    python -m pytest tests/test_mod7_learning.py -v

Требования: ffmpeg/ffprobe в PATH, pytest, numpy, opencv-python-headless.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.modules.mod7_learning import (
    EditPattern,
    LearningEngine,
    extract_pattern,
    get_vector_store,
)
from src.modules.mod7_learning.pattern_extractor import build_pattern_vector
from src.modules.mod7_learning.vector_store import VectorStore


# ==============================================================================
# HELPERS: генерация синтетических видео
# ==============================================================================
def _ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _make_video(path: Path, duration: float = 2.0, color: str = "red") -> Path:
    """Генерирует синтетическое видео: цветной testsrc-кадр + синусоидальный звук."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={color}:s=320x240:d={duration}:r=30",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-shortest",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        str(path),
    ]
    subprocess.run(cmd, capture_output=True, timeout=60)
    return path


# ==============================================================================
# FIXTURES
# ==============================================================================
@pytest.fixture()
def tmp_store(tmp_path: Path) -> Path:
    return tmp_path / "learning_store"


@pytest.fixture()
def ref_video(tmp_path: Path) -> Path:
    return _make_video(tmp_path / "ref_travel.mp4", duration=2.0, color="red")


@pytest.fixture()
def ref_video2(tmp_path: Path) -> Path:
    return _make_video(tmp_path / "ref_sport.mp4", duration=2.0, color="blue")


# ==============================================================================
# ТЕСТЫ: ЭКСТРАКЦИЯ ПАТТЕРНА
# ==============================================================================
@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg не найден в PATH")
def test_extract_pattern_fills_layers(ref_video: Path):
    """Паттерн извлекается, все слои заполнены."""
    pattern = extract_pattern(ref_video, category="travel")

    assert pattern.category == "travel"
    assert pattern.duration_sec > 0
    assert pattern.extracted_by.startswith("pattern_extractor:")
    # Цветовой слой непустой.
    assert 0.0 <= pattern.color.brightness <= 1.0
    assert 0.0 <= pattern.color.saturation <= 1.0
    # Вектор признаков собран.
    assert len(pattern.vector) == 10


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg не найден в PATH")
def test_extract_pattern_missing_file(tmp_path: Path):
    """Несуществующий файл роняет extract_pattern c FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        extract_pattern(tmp_path / "nonexistent.mp4")


def test_build_pattern_vector_known_size():
    """Вектор признаков имеет фиксированную размерность 10."""
    pattern = EditPattern()
    vector = build_pattern_vector(pattern)
    assert len(vector) == 10
    # hook_at_start — бинарный признак.
    assert vector[0] in (0.0, 1.0)


def test_build_pattern_vector_normalized_ranges():
    """Нормализация значений в диапазон [0, 1]."""
    pattern = EditPattern()
    pattern.tempo.avg_cut_duration = 5.0
    pattern.tempo.cuts_per_minute = 60.0
    pattern.color.brightness = 0.8
    vector = build_pattern_vector(pattern)
    assert all(0.0 <= v <= 1.0 for v in vector)


# ==============================================================================
# ТЕСТЫ: ВЕКТОРНОЕ ХРАНИЛИЩЕ (numpy fallback)
# ==============================================================================
def test_vector_store_add_and_search(tmp_store: Path):
    """Добавление и поиск похожих паттернов."""
    store = get_vector_store(tmp_store, vector_size=4, prefer_backend="numpy")

    store.add([1.0, 0.0, 0.0, 0.0], {"category": "travel", "name": "a"})
    store.add([0.0, 1.0, 0.0, 0.0], {"category": "sport", "name": "b"})
    store.add([0.9, 0.1, 0.0, 0.0], {"category": "travel", "name": "c"})

    assert store.count() == 3

    hits = store.search([1.0, 0.0, 0.0, 0.0], k=2)
    assert len(hits) == 2
    # Самое похожее — первый паттерн.
    assert hits[0].metadata["name"] == "a"
    assert hits[0].score >= hits[1].score


def test_vector_store_persist_and_load(tmp_store: Path):
    """Персистентность: сохранённые паттерны переживают пересоздание хранилища."""
    store = get_vector_store(tmp_store, vector_size=4, prefer_backend="numpy")
    store.add([1.0, 0.0, 0.0, 0.0], {"category": "travel"})
    store.persist()

    # Пересоздаём хранилище на той же папке.
    store2 = get_vector_store(tmp_store, vector_size=4, prefer_backend="numpy")
    assert store2.count() == 1


def test_vector_store_wrong_dimension(tmp_store: Path):
    """Неверная размерность вектора вызывает ValueError."""
    store = get_vector_store(tmp_store, vector_size=4, prefer_backend="numpy")
    with pytest.raises(ValueError):
        store.add([1.0, 0.0, 0.0], {})
    with pytest.raises(ValueError):
        store.search([1.0, 0.0, 0.0], k=1)


def test_vector_store_clear(tmp_store: Path):
    """Очистка хранилища: после добавления элемента и clear() размер = 0."""
    store = get_vector_store(tmp_store, vector_size=2, prefer_backend="numpy")
    store.add([1.0, 0.0], {"dummy": "value"})
    assert store.count() == 1
    store.clear()
    assert store.count() == 0


# ==============================================================================
# ТЕСТЫ: ORCHESTRATOR (LearningEngine)
# ==============================================================================
def test_learning_engine_stats_empty(tmp_store: Path):
    """Новый движок без обучения."""
    engine = LearningEngine(tmp_store)
    stats = engine.stats()
    assert stats["total_patterns"] == 0
    assert stats["categories"] == []
    assert engine.get_category_profile("travel") is None


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg не найден в PATH")
@pytest.mark.asyncio
async def test_learn_from_references(tmp_store: Path, ref_video: Path, ref_video2: Path):
    """Обучение по папке референсов пополняет хранилище и категории."""
    ref_dir = ref_video.parent
    engine = LearningEngine(tmp_store)

    # Добавляем второй файл в ту же папку.
    _make_video(ref_dir / "ref_travel2.mp4", duration=1.5, color="green")

    patterns = await engine.learn_from_references(ref_dir, category="travel")

    assert len(patterns) >= 2
    assert engine.store.count() >= 2
    assert "travel" in engine.list_categories()

    profile = engine.get_category_profile("travel")
    assert profile is not None
    assert profile.category == "travel"
    assert 0.0 <= profile.color.brightness <= 1.0


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg не найден в PATH")
@pytest.mark.asyncio
async def test_learn_from_references_empty_dir(tmp_store: Path, tmp_path: Path):
    """Пустая папка вызывает ValueError."""
    empty = tmp_path / "empty_refs"
    empty.mkdir()
    engine = LearningEngine(tmp_store)
    with pytest.raises(ValueError):
        await engine.learn_from_references(empty, category="travel")


def test_find_similar_filters_by_category(tmp_store: Path):
    """Поиск похожих паттернов с фильтром по категории."""
    engine = LearningEngine(tmp_store)
    engine.store.add([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                     {"category": "travel", "pattern": EditPattern(category="travel").serialize()})
    engine.store.add([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                     {"category": "sport", "pattern": EditPattern(category="sport").serialize()})

    query = EditPattern()
    query.vector = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    hits = engine.find_similar(query, category="travel", k=5)
    assert len(hits) == 1
    assert hits[0].metadata["category"] == "travel"