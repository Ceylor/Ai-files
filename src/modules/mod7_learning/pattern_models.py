"""
Pydantic-модели "паттерна успеха" — типизированное представление того,
как смонтирован успешный референсный клип.

Паттерн состоит из 5 ключевых слоёв:
    - structure  : структура/нарратив (фазы, hook-позиция);
    - tempo      : темп и ритм монтажа (частота склеек, динамика);
    - transitions: переходы между сценами;
    - color      : цветокоррекция (яркость, насыщенность, контраст, температура);
    - music      : музыкальное сопровождение (BPM, энергия, тональность).

Каждый паттерн имеет компактный числовой вектор (feature vector),
который используется для векторного поиска похожих паттернов.
"""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


# ==============================================================================
# Вложенные профили
# ==============================================================================
class StructurePhase(BaseModel):
    """Одна фаза нарративной структуры клипа."""

    name: str = Field(..., description="Название фазы (hook, setup, climax, ...)")
    start: float = Field(0.0, description="Начало фазы в секундах")
    end: float = Field(0.0, description="Конец фазы в секундах")
    duration: float = Field(0.0, description="Длительность фазы в секундах")


class StructureProfile(BaseModel):
    """Структурный профиль клипа."""

    hook_position_sec: float = Field(0.0, description="Позиция хука от начала (сек)")
    hook_at_start: bool = Field(False, description="Хук расположен в первые 3 секунды")
    phase_count: int = Field(0, description="Число обнаруженных фаз")
    phases: List[StructurePhase] = Field(default_factory=list)


class TempoProfile(BaseModel):
    """Темп и ритм монтажа."""

    avg_cut_duration: float = Field(3.0, description="Средняя длительность склейки (сек)")
    cuts_per_minute: float = Field(20.0, description="Число склеек в минуту")
    tempo_label: str = Field("balanced", description="fast / balanced / slow")


class TransitionStats(BaseModel):
    """Статистика переходов между сценами."""

    total_transitions: int = Field(0)
    avg_transition_duration: float = Field(0.0, description="Средняя длительность перехода (сек)")


class ColorProfile(BaseModel):
    """Цветокоррекция клипа (усреднённая по кадрам)."""

    brightness: float = Field(0.5, ge=0.0, le=1.0, description="Средняя яркость (0..1)")
    saturation: float = Field(0.5, ge=0.0, le=1.0, description="Средняя насыщенность (0..1)")
    contrast: float = Field(0.5, ge=0.0, le=1.0, description="Средний контраст (0..1)")
    color_temp: float = Field(0.0, ge=-1.0, le=1.0, description="Температура: -1 холодный, +1 тёплый")


class MusicProfile(BaseModel):
    """Музыкальное сопровождение."""

    bpm: Optional[float] = Field(None, description="Темп музыки")
    energy_percent: Optional[int] = Field(None, description="Энергия 0..100")
    camelot: Optional[str] = Field(None, description="Тональность в системе Camelot (8B, 4A, ...)")
    mood: str = Field("neutral", description="Настроение: energetic / calm / neutral / ...")


# ==============================================================================
# Основной паттерн
# ==============================================================================
class EditPattern(BaseModel):
    """
    Полный "паттерн успеха", извлечённый из референсного клипа.

    Помимо профилей хранит исходную метаинформацию (категория, путь)
    и компактный вектор признаков для векторного поиска.
    """

    category: str = Field("default", description="Категория клипа (travel, sport, ...)")
    source_path: str = Field("", description="Путь к исходному референсному файлу")
    duration_sec: float = Field(0.0, description="Длительность клипа (сек)")

    structure: StructureProfile = Field(default_factory=StructureProfile)
    tempo: TempoProfile = Field(default_factory=TempoProfile)
    transitions: TransitionStats = Field(default_factory=TransitionStats)
    color: ColorProfile = Field(default_factory=ColorProfile)
    music: MusicProfile = Field(default_factory=MusicProfile)

    # --- векторное представление для поиска -------------------------------
    vector: List[float] = Field(default_factory=list, description="Компактный вектор признаков")

    # --- метаданные обучения ---------------------------------------------
    extracted_by: str = Field("extractor", description="Версия экстрактора, создавшего паттерн")

    def to_feature_dict(self) -> Dict[str, float]:
        """Возвращает именованный словарь признаков (для отладки и CRUD)."""
        return {
            "hook_at_start": float(self.structure.hook_at_start),
            "phase_count": float(self.structure.phase_count),
            "avg_cut_duration": self.tempo.avg_cut_duration,
            "cuts_per_minute": self.tempo.cuts_per_minute,
            "brightness": self.color.brightness,
            "saturation": self.color.saturation,
            "contrast": self.color.contrast,
            "color_temp": self.color.color_temp,
            "bpm": float(self.music.bpm or 0.0),
            "energy_percent": float(self.music.energy_percent or 0.0),
        }

    def serialize(self) -> Dict[str, Any]:
        """Сериализация для сохранения в хранилище (JSON-совместимая)."""
        return self.model_dump()

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "EditPattern":
        """Восстановление паттерна из словаря."""
        return cls(**data)