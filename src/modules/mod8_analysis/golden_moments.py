"""
"Золотые моменты" — фрагменты видео, оптимальные для хука.

Интегральный скор = (эмоция + движение + редкость объекта) / 3.

Слой агрегирует результаты детекции эмоций, движения и объектов,
нормализует их к [0,1] и выдаёт топ-N фрагментов (по умолчанию 3).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List

from src.modules.mod8_analysis.schemas import (
    DetectedObject,
    EmotionalFrame,
    GoldenMoment,
    MotionSample,
)

logger = logging.getLogger("analysis.golden")

# Объекты, считающиеся "редкими/интересными" для хука.
_RARE_OBJECTS = {
    "person", "dog", "cat", "car", "motorcycle", "surfboard", "skateboard",
    "snowboard", "horse", "airplane", "boat", "bird", "wild", "fire",
}

# Эмоции, повышающие хук.
_STRONG_EMOTIONS = {"happy", "surprise", "fear", "angry"}


class GoldenMoments:
    """Вычисление топ-N "золотых моментов" из слоёв анализа."""

    def __init__(self, window_sec: float = 2.0, top_k: int = 3) -> None:
        self.window_sec = window_sec  # длительность фрагмента
        self.top_k = top_k

    # ------------------------------------------------------------------ вычисление
    def compute(
        self,
        emotions: List[EmotionalFrame],
        objects: List[DetectedObject],
        motion: List[MotionSample],
        duration: float,
    ) -> List[GoldenMoment]:
        """
        Вычисляет топ-K "золотых моментов".

        Args:
            emotions: результаты детекции эмоций.
            objects: результаты детекции объектов.
            motion: сэмплы энергии движения.
            duration: длительность видео (сек).

        Returns:
            Список GoldenMoment (топ-3 по интегральному скору).
        """
        if duration <= 0:
            return []

        # Привязываем сэмплы к временным окнам (бинам по 1 сек).
        emotion_by_bin: Dict[int, List[EmotionalFrame]] = defaultdict(list)
        for e in emotions:
            bin_idx = int(e.timestamp)
            emotion_by_bin[bin_idx].append(e)

        obj_by_bin: Dict[int, List[DetectedObject]] = defaultdict(list)
        for o in objects:
            bin_idx = int(o.timestamp)
            obj_by_bin[bin_idx].append(o)

        motion_by_bin: Dict[int, List[float]] = defaultdict(list)
        for m in motion:
            motion_by_bin[int(m.timestamp)].append(m.energy)

        total_bins = max(1, int(duration))

        # Считаем интегральный скор по каждому временному окну.
        scored: List[GoldenMoment] = []
        for bin_idx in range(total_bins):
            # 1) Эмоциональная составляющая.
            emotion_score = 0.0
            dominant_emotion = None
            for e in emotion_by_bin.get(bin_idx, []):
                if e.emotion in _STRONG_EMOTIONS:
                    emotion_score = max(emotion_score, e.confidence)
                    dominant_emotion = e.emotion

            # 2) Движение.
            motion_vals = motion_by_bin.get(bin_idx, [])
            motion_energy = sum(motion_vals) / len(motion_vals) if motion_vals else 0.0

            # 3) Редкость объекта.
            object_score = 0.0
            rare_objects: List[str] = []
            for o in obj_by_bin.get(bin_idx, []):
                if o.label in _RARE_OBJECTS:
                    object_score = max(object_score, o.confidence)
                    if o.label not in rare_objects:
                        rare_objects.append(o.label)

            if emotion_score == 0.0 and motion_energy == 0.0 and object_score == 0.0:
                continue  # пустой бин пропускаем

            integral = (emotion_score + motion_energy + object_score) / 3.0
            scored.append(GoldenMoment(
                start=round(float(bin_idx), 2),
                end=round(float(bin_idx) + self.window_sec, 2),
                score=round(integral, 4),
                emotion=dominant_emotion,
                objects=rare_objects,
                motion_energy=round(motion_energy, 4),
            ))

        # Сортируем по скору, берём топ-K.
        scored.sort(key=lambda g: g.score, reverse=True)
        top = scored[: self.top_k]
        logger.info("Золотые моменты: выбрано %d из %d кандидатов", len(top), len(scored))
        return top