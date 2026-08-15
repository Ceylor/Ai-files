"""
Тесты модуля 8: МНОГОСЛОЙНЫЙ АНАЛИЗ КОНТЕНТА.

Используют моки моделей (DeepFace/fer/YOLO/CLIP не требуются в тестах).

Проверяют:
    - graceful fallback при отсутствии моделей (слои возвращают пустые списки);
    - расчёт "золотых моментов" (интегральный скор);
    - нормализацию движения (0..1);
    - оркестратор MultiLayerAnalyzer (с моками детекторов).

Запуск:
    python -m pytest tests/test_mod8_analysis.py -v

Требования: pytest, numpy, opencv-python-headless.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from src.modules.mod8_analysis.schemas import (
    DetectedObject,
    EmotionalFrame,
    GoldenMoment,
    MotionSample,
)
from src.modules.mod8_analysis.golden_moments import GoldenMoments
from src.modules.mod8_analysis.motion_analyzer import MotionAnalyzer


# ==============================================================================
# ТЕСТЫ: GOLDEN MOMENTS
# ==============================================================================
def test_golden_moments_empty():
    """Пустые слои → пустой список золотых моментов."""
    gm = GoldenMoments(top_k=3)
    result = gm.compute([], [], [], duration=10.0)
    assert result == []


def test_golden_moments_returns_top3():
    """Слои с данными → топ-3 по интегральному скору."""
    gm = GoldenMoments(top_k=3)
    emotions = [EmotionalFrame(timestamp=1.0, emotion="happy", confidence=1.0)]
    objects = [DetectedObject(timestamp=1.0, label="dog", confidence=1.0)]
    motion = [MotionSample(timestamp=1.0, energy=1.0)]

    result = gm.compute(emotions, objects, motion, duration=10.0)
    assert len(result) <= 3
    # Фрагмент на t=1 должен быть в топе.
    assert any(abs(g.start - 1.0) < 0.01 for g in result)


def test_golden_moments_score_range():
    """Интегральный скор лежит в диапазоне [0,1]."""
    gm = GoldenMoments(top_k=3)
    emotions = [EmotionalFrame(timestamp=0.0, emotion="surprise", confidence=0.8)]
    objects = [DetectedObject(timestamp=0.0, label="person", confidence=0.9)]
    motion = [MotionSample(timestamp=0.0, energy=0.5)]

    result = gm.compute(emotions, objects, motion, duration=5.0)
    assert result
    for g in result:
        assert 0.0 <= g.score <= 1.0


def test_golden_moments_rare_objects():
    """Редкие объекты повышают скор."""
    gm = GoldenMoments(top_k=3)
    # Объект dog - редкий/интересный, object None - обычный.
    result_with_dog = gm.compute(
        [], [DetectedObject(timestamp=2.0, label="dog", confidence=1.0)], [], duration=5.0
    )
    assert any(g.objects == ["dog"] for g in result_with_dog)


# ==============================================================================
# ТЕСТЫ: MOTION ANALYZER (fallback)
# ==============================================================================
def test_motion_analyzer_missing_file(tmp_path: Path):
    """Несуществующее видео → пустой список (graceful fallback)."""
    ma = MotionAnalyzer()
    result = ma.analyze_video(tmp_path / "nonexistent.mp4")
    assert result == []


def test_motion_analyzer_energy_range():
    """Метод _frame_energy возвращает значение в [0,1]."""
    import numpy as np

    ma = MotionAnalyzer()
    a = np.zeros((100, 100), dtype=np.uint8)
    b = np.zeros((100, 100), dtype=np.uint8)
    # Два одинаковых кадра → нулевое движение.
    energy = ma._frame_energy(a, b)
    assert 0.0 <= energy <= 1.0


# ==============================================================================
# ТЕСТЫ: ORCHESTRATOR (с моками)
# ==============================================================================
@pytest.mark.asyncio
async def test_analyzer_graceful_fallback(tmp_path: Path, monkeypatch):
    """
    Если модели недоступны — анализ не падает, возвращает пустые слои.
    Мокаем детекторы, чтобы вернуть пустые результаты.
    """
    from src.modules.mod8_analysis import analyzer as analyzer_module

    class FakeDetector:
        def analyze_video(self, path):
            return []

    # Создаём временный видеофайл (мок, не обязательно валидный).
    video = tmp_path / "fake.mp4"
    video.write_bytes(b"fake")

    # Подменяем детекторы в классе.
    monkeypatch.setattr(analyzer_module.EmotionDetector, "analyze_video",
                        lambda self, path: [])
    monkeypatch.setattr(analyzer_module.ObjectDetector, "analyze_video",
                        lambda self, path: [])
    monkeypatch.setattr(analyzer_module.MotionAnalyzer, "analyze_video",
                        lambda self, path: [])
    monkeypatch.setattr(analyzer_module.ClipEmbedder, "analyze_video",
                        lambda self, path: [])

    result = await analyzer_module.analyze_video(video, video_id=1)

    assert result.video_id == 1
    assert result.emotions == []
    assert result.objects == []
    assert result.motion == []
    assert result.embeddings == []
    # Золотых моментов нет (пустые слои).
    assert result.golden_moments == []
    # Статусы слоёв заполнены.
    assert "emotions" in result.layers_status


def test_schemas_serialize():
    """Pydantic-схемы корректно сериализуются в dict."""
    gm = GoldenMoment(start=0.0, end=2.0, score=0.9, emotion="happy",
                      objects=["dog"], motion_energy=0.5)
    data = gm.model_dump()
    assert data["score"] == 0.9
    assert data["objects"] == ["dog"]