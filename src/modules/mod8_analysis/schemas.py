"""
Модели данных для многослойного анализа контента.

Все слои анализа возвращают типизированные структуры (pydantic), которые
затем агрегируются оркестратором и сохраняются в БД.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EmotionalFrame(BaseModel):
    """Результат детекции эмоций в кадре."""

    timestamp: float = Field(0.0, description="Время кадра (сек)")
    emotion: str = Field("neutral", description="Доминирующая эмоция (joy, surprise, anger, ...)")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Уверенность 0..1")
    emotions: Dict[str, float] = Field(default_factory=dict, description="Все эмоции с весами")


class DetectedObject(BaseModel):
    """Результат детекции объекта в кадре."""

    timestamp: float = Field(0.0, description="Время кадра (сек)")
    label: str = Field("", description="Класс объекта (person, car, dog, ...)")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Уверенность 0..1")
    box: List[float] = Field(default_factory=list, description="Bounding box [x1,y1,x2,y2]")


class MotionSample(BaseModel):
    """Оценка энергии движения в момент времени."""

    timestamp: float = Field(0.0, description="Время (сек)")
    energy: float = Field(0.0, ge=0.0, le=1.0, description="Энергия движения 0..1")


class GoldenMoment(BaseModel):
    """"Золотой момент" — фрагмент, оптимальный для хука."""

    start: float = Field(0.0, description="Начало фрагмента (сек)")
    end: float = Field(0.0, description="Конец фрагмента (сек)")
    score: float = Field(0.0, ge=0.0, le=1.0, description="Интегральный скор 0..1")
    emotion: Optional[str] = Field(None, description="Доминирующая эмоция в фрагменте")
    objects: List[str] = Field(default_factory=list, description="Ключевые объекты")
    motion_energy: float = Field(0.0, description="Средняя энергия движения")


class ClipEmbedding(BaseModel):
    """CLIP-эмбеддинг кадра."""

    timestamp: float = Field(0.0, description="Время кадра (сек)")
    embedding: List[float] = Field(default_factory=list, description="Вектор эмбеддинга")


class VideoAnalysisResult(BaseModel):
    """Полный результат многослойного анализа видео."""

    video_id: Optional[int] = Field(None, description="ID видео в БД")
    video_path: str = Field("", description="Путь к видео")
    duration: float = Field(0.0, description="Длительность видео (сек)")
    emotions: List[EmotionalFrame] = Field(default_factory=list)
    objects: List[DetectedObject] = Field(default_factory=list)
    motion: List[MotionSample] = Field(default_factory=list)
    golden_moments: List[GoldenMoment] = Field(default_factory=list)
    embeddings: List[ClipEmbedding] = Field(default_factory=list)
    layers_status: Dict[str, str] = Field(default_factory=dict, description="Статус каждого слоя")