"""
Детекция эмоций по лицам в кадре.

Использует DeepFace или fer (если установлены). Graceful fallback:
при отсутствии моделей/зависимостей слой пропускается, анализ не падает.

Извлекает кадры из видео через OpenCV и прогоняет через модель эмоций.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from src.modules.mod8_analysis.schemas import EmotionalFrame

logger = logging.getLogger("analysis.emotion")

# Набор известных эмоций DeepFace/fer.
_KNOWN_EMOTIONS = [
    "angry", "disgust", "fear", "happy", "sad", "surprise", "neutral",
]


class EmotionDetector:
    """Обнаружение эмоций по лицам в кадре с graceful fallback."""

    def __init__(self, frame_interval: float = 1.0, sample_fps: int = 10) -> None:
        self.frame_interval = frame_interval  # шаг анализа (сек)
        self.sample_fps = sample_fps
        self._model = None
        self._backend = None

    # ------------------------------------------------------------------ lazy init
    def _ensure_model(self) -> bool:
        """Лениво загружает модель эмоций. Возвращает True при успехе."""
        if self._model is not None:
            return True
        # Пробуем DeepFace.
        try:
            from deepface import DeepFace  # type: ignore

            self._backend = "deepface"
            self._model = {"deepface": DeepFace}
            logger.info("EmotionDetector: бэкенд DeepFace активен")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("DeepFace недоступен: %s", exc)

        # Пробуем fer.
        try:
            from fer import FER  # type: ignore

            self._backend = "fer"
            self._model = {"fer": FER(mtcnn=False)}
            logger.info("EmotionDetector: бэкенд FER активен")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("FER недоступен: %s", exc)

        logger.warning("EmotionDetector: модели не найдены, слой пропускается")
        return False

    # ------------------------------------------------------------------ детекция
    def _analyze_frame(self, bgr_frame: np.ndarray) -> Optional[EmotionalFrame]:
        """Анализирует один кадр. Возвращает EmotionalFrame или None."""
        try:
            if self._backend == "deepface":
                from deepface import DeepFace  # type: ignore

                faces = DeepFace.analyze(bgr_frame, actions=["emotion"], enforce_detection=False, silent=True)
                if isinstance(faces, list) and faces:
                    face = faces[0]
                    emotions = face.get("emotion", {})
                    if emotions:
                        dominant = max(emotions, key=emotions.get)
                        return EmotionalFrame(
                            timestamp=0.0,  # заполняется вызывающим
                            emotion=dominant,
                            confidence=float(emotions[dominant]) / 100.0,
                            emotions={k: float(v) / 100.0 for k, v in emotions.items()},
                        )
                return None

            if self._backend == "fer":
                fer_model = self._model["fer"]
                detections = fer_model.detect_emotions(bgr_frame)
                if detections:
                    top = max(detections, key=lambda d: max(d["emotions"].values()))
                    emotions = top["emotions"]
                    dominant = max(emotions, key=emotions.get)
                    return EmotionalFrame(
                        timestamp=0.0,
                        emotion=dominant,
                        confidence=float(emotions[dominant]),
                        emotions=emotions,
                    )
                return None
        except Exception as exc:  # noqa: BLE001
            logger.debug("Ошибка анализа эмоций кадра: %s", exc)
            return None
        return None

    # ------------------------------------------------------------------ публичный API
    def analyze_video(self, video_path: Path) -> List[EmotionalFrame]:
        """
        Анализирует видео и возвращает список эмоций по временной шкале.

        Возвращает пустой список, если модель недоступна (graceful fallback).
        """
        if not self._ensure_model():
            return []

        frames: List[EmotionalFrame] = []
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.warning("Не удалось открыть видео %s", video_path)
                return []

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_count = max(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), 1)
            step = max(1, int(self.frame_interval * fps))
            pos = 0
            while pos < frame_count:
                cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
                ok, frame = cap.read()
                if not ok:
                    break
                result = self._analyze_frame(frame)
                if result is not None:
                    result.timestamp = round(pos / fps, 2)
                    frames.append(result)
                pos += step
            cap.release()
            logger.info("Эмоции: обработано %d кадров", len(frames))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Слой эмоций пропущен: %s", exc)
        return frames