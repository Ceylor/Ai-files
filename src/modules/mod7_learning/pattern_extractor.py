"""
Экстрактор "паттернов успеха" из референсных клипов.

Для каждого готового референсного клипа модуль извлекает 5 слоёв паттерна:
    - structure  : эвристическая структура (положение хука, число фаз);
    - tempo      : ритм монтажа через детекцию сцен (частота склеек);
    - transitions: статистика переходов (на основе смен сцен);
    - color      : цветокоррекция (яркость, насыщенность, контраст, температура);
    - music      : аудио-профиль (BPM, энергия, Camelot) через audio_analyzer.

Вектор признаков (10 измерений) вычисляется функцией build_pattern_vector.

Все тяжёлые анализаторы имеют graceful-fallback: если что-то недоступно,
слой заполняется нейтральными значениями по умолчанию, обучение не падает.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.utils.audio_analyzer import analyze_audio_track
from src.modules.mod7_learning.pattern_models import (
    ColorProfile,
    EditPattern,
    MusicProfile,
    StructurePhase,
    StructureProfile,
    TempoProfile,
    TransitionStats,
)

logger = logging.getLogger("learning.extractor")

# Вектор признаков состоит из 10 измерений (см. build_pattern_vector).
FEATURE_KEYS: List[str] = [
    "hook_at_start",
    "phase_count",
    "avg_cut_duration",
    "cuts_per_minute",
    "brightness",
    "saturation",
    "contrast",
    "color_temp",
    "bpm",
    "energy_percent",
]

EXTRACTOR_VERSION = "2.0.0"

# Диапазоны для нормализации признаков к [0, 1] (кроме бинарных).
_NORM_RANGES: Dict[str, Tuple[float, float]] = {
    "phase_count": (1.0, 8.0),
    "avg_cut_duration": (0.5, 10.0),
    "cuts_per_minute": (5.0, 120.0),
    "brightness": (0.0, 1.0),
    "saturation": (0.0, 1.0),
    "contrast": (0.0, 1.0),
    "color_temp": (-1.0, 1.0),
    "bpm": (60.0, 200.0),
    "energy_percent": (0.0, 100.0),
}


# ==============================================================================
# Слой: ЦВЕТ (OpenCV-сэмплы кадров)
# ==============================================================================
def _analyze_color(video_path: Path, sample_limit: int = 40) -> ColorProfile:
    """
    Усреднённый цветовой профиль клипа по равномерной выборке кадров.

    Яркость/насыщенность/контраст — из HSV/Luma; температура — из каналов R/B.
    Всё аккуратно нормализуется к диапазону моделей.
    """
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError("Не удалось открыть видео")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = max(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), 1)
        total_sec = frame_count / fps if fps > 0 else 60.0

        # Равномерно выбираем кадры по времени.
        step = max(1, int(frame_count / sample_limit))
        brightnesses, saturations, contrasts, temps = [], [], [], []
        pos = 0
        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ok, frame = cap.read()
            if not ok:
                break
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

            # Яркость (V) и насыщенность (S) из HSV.
            brightnesses.append(float(np.mean(hsv[:, :, 2]) / 255.0))
            saturations.append(float(np.mean(hsv[:, :, 1]) / 255.0))

            # Контраст = стандартное отклонение яркости (нормированное).
            contrasts.append(float(np.std(hsv[:, :, 2]) / 255.0))

            # Температура: соотношение красного и синего каналов.
            r = float(np.mean(bgr[:, :, 2]))
            b = float(np.mean(bgr[:, :, 0]))
            temp = 0.0
            if b > 0:
                temp = np.clip((r - b) / (r + b), -1.0, 1.0)  # +1 тёплый, -1 холодный
            temps.append(float(temp))

            pos += step

        cap.release()

        if not brightnesses:
            raise RuntimeError("Не извлечено ни одного кадра")

        return ColorProfile(
            brightness=float(np.mean(brightnesses)),
            saturation=float(np.mean(saturations)),
            contrast=float(np.mean(contrasts)),
            color_temp=float(np.mean(temps)),
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("Цветовой анализ недоступен (%s), нейтральный профиль", exc)
        return ColorProfile()


# ==============================================================================
# Слой: РИТМ / СТРУКТУРА / ПЕРЕХОДЫ (детекция сцен через OpenCV)
# ==============================================================================
def _detect_cut_durations(video_path: Path, sample_limit: int = 400) -> List[float]:
    """
    Детектирует границы сцен по разнице кадров (content-based).

    Простая и надёжная эвристика: разница гистограмм соседних сэмплов кадров
    превышает порог -> считаем границу склейки. Возвращает длительности сцен.
    """
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError("Не удалось открыть видео")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = max(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), 1)

        step = max(1, int(frame_count / sample_limit))
        prev_hist: Optional[np.ndarray] = None
        cut_times: List[float] = []
        pos = 0
        frame_idx = 0
        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ok, frame = cap.read()
            if not ok:
                break
            small = cv2.resize(frame, (64, 36))
            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
            hist = cv2.normalize(hist, hist).flatten()

            if prev_hist is not None:
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                if diff > 0.35:  # порог смены сцены
                    cut_times.append(frame_idx * step / fps)

            prev_hist = hist
            frame_idx += 1
            pos += step

        cap.release()

        # Длительности сцен между границами.
        durations: List[float] = []
        if cut_times:
            prev_t = 0.0
            total = frame_count / fps
            for t in cut_times:
                durations.append(t - prev_t)
                prev_t = t
            durations.append(total - prev_t)
        return [d for d in durations if d > 0.3]
    except Exception as exc:  # noqa: BLE001
        logger.debug("Детекция сцен недоступна (%s)", exc)
        return []


def _analyze_rhythm(video_path: Path) -> Tuple[TempoProfile, TransitionStats, StructureProfile]:
    """
    Считает темп, переходы и эвристическую структуру на основе склеек.
    """
    durations = _detect_cut_durations(video_path)

    if not durations:
        tempo = TempoProfile()  # нейтральный
        return tempo, TransitionStats(), StructureProfile()

    avg_cut = float(np.mean(durations))
    total_sec = float(sum(durations))
    cuts_per_minute = (len(durations) / total_sec * 60.0) if total_sec > 0 else 0.0

    if avg_cut < 2.0:
        label = "fast"
    elif avg_cut > 5.0:
        label = "slow"
    else:
        label = "balanced"

    tempo = TempoProfile(
        avg_cut_duration=round(avg_cut, 2),
        cuts_per_minute=round(cuts_per_minute, 1),
        tempo_label=label,
    )

    transitions = TransitionStats(
        total_transitions=max(0, len(durations) - 1),
        avg_transition_duration=round(min(avg_cut * 0.15, 1.0), 2),
    )

    # Эвристическая структура: хук = самая короткая сцена (пик динамики).
    hook_idx = int(np.argmin(durations))
    hook_position = float(np.sum(durations[:hook_idx])) if hook_idx > 0 else 0.0
    structure = StructureProfile(
        hook_position_sec=round(hook_position, 2),
        hook_at_start=hook_position <= 3.0,
        phase_count=len(durations),
        phases=[
            StructurePhase(name=f"scene_{i}", start=float(np.sum(durations[:i])),
                           end=float(np.sum(durations[: i + 1])), duration=float(d))
            for i, d in enumerate(durations)
        ],
    )
    return tempo, transitions, structure


# ==============================================================================
# Слой: МУЗЫКА (через существующий audio_analyzer)
# ==============================================================================
def _analyze_music(video_path: Path) -> MusicProfile:
    """Аудио-профиль клипа через audio_analyzer (BPM, энергия, Camelot)."""
    try:
        data = analyze_audio_track(video_path, duration_limit=60.0)
        if not data.get("success"):
            return MusicProfile()
        energy = data.get("energy_percent", 50)
        mood = "energetic" if energy > 60 else ("calm" if energy < 40 else "neutral")
        return MusicProfile(
            bpm=data.get("bpm"),
            energy_percent=int(energy),
            camelot=data.get("camelot") if data.get("camelot") != "Unknown" else None,
            mood=mood,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("Аудио-анализ недоступен (%s), нейтральный профиль", exc)
        return MusicProfile()


# ==============================================================================
# Вектор признаков
# ==============================================================================
def _normalize_feature(value: float, low: float, high: float) -> float:
    """Нормализует значение в диапазон [0, 1]."""
    if high <= low:
        return 0.0
    return float(np.clip((value - low) / (high - low), 0.0, 1.0))


def build_pattern_vector(pattern: EditPattern) -> List[float]:
    """
    Строит компактный вектор признаков (10 измерений) из паттерна.

    Используется для векторного поиска похожих паттернов.
    """
    feats = pattern.to_feature_dict()
    vector: List[float] = []
    for key in FEATURE_KEYS:
        value = feats[key]
        if key == "hook_at_start":
            vector.append(float(value))
        else:
            low, high = _NORM_RANGES[key]
            vector.append(_normalize_feature(float(value), low, high))
    return vector


# ==============================================================================
# Публичный API экстрактора
# ==============================================================================
def extract_pattern(
    video_path: Path,
    category: str = "default",
    async_mode: bool = False,
) -> EditPattern:
    """
    Извлекает полный "паттерн успеха" из одного референсного клипа.

    Args:
        video_path: Путь к референсному видео.
        category: Категория клипа (travel, sport, tutorial, reaction, ...).
        async_mode: Если True, аудио-анализ выполняется через asyncio (не блокирует).
            (Оставлено для совместимости; текущая реализация — синхронная обёртка.)

    Returns:
        EditPattern с заполненными слоями и вектором признаков.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Референсный файл не найден: {video_path}")

    duration_sec = 0.0
    try:
        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            duration_sec = cap.get(cv2.CAP_PROP_FRAME_COUNT) / (cap.get(cv2.CAP_PROP_FPS) or 30.0)
            cap.release()
    except Exception:  # noqa: BLE001
        pass

    color = _analyze_color(video_path)
    tempo, transitions, structure = _analyze_rhythm(video_path)
    music = _analyze_music(video_path)

    pattern = EditPattern(
        category=category,
        source_path=str(video_path.resolve()),
        duration_sec=round(duration_sec, 2),
        structure=structure,
        tempo=tempo,
        transitions=transitions,
        color=color,
        music=music,
        extracted_by=f"pattern_extractor:{EXTRACTOR_VERSION}",
    )
    pattern.vector = build_pattern_vector(pattern)
    logger.info(
        "Паттерн извлечён: %s (dur=%.1fs, cuts=%.1f/min, bpm=%s, label=%s)",
        video_path.name, duration_sec, tempo.cuts_per_minute, music.bpm, tempo.tempo_label,
    )
    return pattern


async def extract_pattern_async(video_path: Path, category: str = "default") -> EditPattern:
    """Асинхронная обёртка над extract_pattern (тяжёлые части выполняются в executor)."""
    return await asyncio.to_thread(extract_pattern, video_path, category)