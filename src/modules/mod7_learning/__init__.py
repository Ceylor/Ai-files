"""
Модуль 7: САМООБУЧЕНИЕ НА ПРИМЕРАХ (AI AutoClip Pro 2.0).

Система анализирует готовые референсные клипы по категориям, извлекает
"паттерны успеха" (структура, темп, переходы, цветокоррекция, музыка),
хранит их в векторном хранилище и позволяет находить похожие паттерны
для применения к новым видео.

Публичный API:
    LearningEngine         — оркестратор самообучения.
    EditPattern            — модель извлечённого паттерна.
    extract_pattern        — извлечение паттерна из одного видео.
    get_vector_store       — фабрика векторного хранилища.
"""

from src.modules.mod7_learning.pattern_models import (
    ColorProfile,
    EditPattern,
    MusicProfile,
    StructurePhase,
    StructureProfile,
    TempoProfile,
    TransitionStats,
)
from src.modules.mod7_learning.pattern_extractor import extract_pattern
from src.modules.mod7_learning.vector_store import get_vector_store
from src.modules.mod7_learning.learner import LearningEngine

__all__ = [
    "ColorProfile",
    "EditPattern",
    "LearningEngine",
    "MusicProfile",
    "StructurePhase",
    "StructureProfile",
    "TempoProfile",
    "TransitionStats",
    "extract_pattern",
    "get_vector_store",
]