"""
Анализ движения через optical flow (Farneback).

Оценивает "энергию движения" в каждом кадре и возвращает массив значений
0..1 по временной шкале. Используется для определения динамики и
приоритизации "золотых моментов".
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import cv2
import numpy as np

from src.modules.mod8_analysis.schemas import MotionSample

logger = logging.getLogger("analysis.motion")


class MotionAnalyzer:
    """Оценка энергии движения по optical flow (Farneback)."""

    def __init__(self, step_frames: int = 5) -> None:
        self.step_frames = step_frames  # анализируем каждый N-й кадр

    # ------------------------------------------------------------------ flow
    def _frame_energy(self, prev_gray: np.ndarray, curr_gray: np.ndarray) -> float:
        """Вычисляет нормализованную энергию движения между двумя кадрами."""
        try:
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
            )
            # Магнитуда векторов движения.
            mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            # Нормализуем среднюю магнитуду к 0..1 (порог ~20 пикс среднего движения).
            energy = float(np.mean(mag) / 20.0)
            return max(0.0, min(1.0, energy))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Ошибка optical flow: %s", exc)
            return 0.0

    # ------------------------------------------------------------------ публичный API
    def analyze_video(self, video_path: Path) -> List[MotionSample]:
        """
        Возвращает массив значений "энергии движения" (0..1) по временной шкале.

        Работает на OpenCV (всегда доступен), graceful fallback — пустой список.
        """
        samples: List[MotionSample] = []
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.warning("Не удалось открыть видео %s", video_path)
                return []

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_count = max(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), 1)

            prev_gray = None
            pos = 0
            processed = 0
            while True:
                cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
                ok, frame = cap.read()
                if not ok:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, (320, 180))  # ускоряем анализ

                if prev_gray is not None:
                    energy = self._frame_energy(prev_gray, gray)
                    samples.append(MotionSample(timestamp=round(pos / fps, 2), energy=round(energy, 4)))
                    processed += 1

                prev_gray = gray
                pos += self.step_frames
                if processed >= 500:  # ограничиваем число сэмплов
                    break

            cap.release()
            logger.info("Движение: собрано %d сэмплов энергии", len(samples))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Слой движения пропущен: %s", exc)
        return samples