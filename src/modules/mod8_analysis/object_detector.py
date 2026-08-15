"""
Детекция объектов в кадре.

Использует YOLO (ultralytics) или Detectron2, если установлены.
Graceful fallback: при отсутствии моделей слой пропускается.

Извлекает кадры из видео и прогоняет через модель объектной детекции.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from src.modules.mod8_analysis.schemas import DetectedObject

logger = logging.getLogger("analysis.object")


class ObjectDetector:
    """Обнаружение объектов с graceful fallback."""

    def __init__(self, frame_interval: float = 1.0, conf_threshold: float = 0.3) -> None:
        self.frame_interval = frame_interval
        self.conf_threshold = conf_threshold
        self._model = None
        self._backend = None

    # ------------------------------------------------------------------ lazy init
    def _ensure_model(self) -> bool:
        """Лениво загружает модель YOLO/Detectron2. Возвращает True при успехе."""
        if self._model is not None:
            return True
        # Пробуем ultralytics YOLO.
        try:
            from ultralytics import YOLO  # type: ignore

            self._backend = "yolo"
            self._model = {"yolo": YOLO("yolov8n.pt")}
            logger.info("ObjectDetector: бэкенд YOLOv8 активен")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("YOLO недоступен: %s", exc)

        logger.warning("ObjectDetector: модели не найдены, слой пропускается")
        return False

    # ------------------------------------------------------------------ детекция
    def _analyze_frame(self, bgr_frame: np.ndarray) -> List[DetectedObject]:
        """Анализирует один кадр, возвращает список объектов."""
        results: List[DetectedObject] = []
        try:
            if self._backend == "yolo":
                model = self._model["yolo"]
                detections = model(bgr_frame, verbose=False)
                for det in detections:
                    boxes = det.boxes
                    if boxes is None:
                        continue
                    for box in boxes:
                        conf = float(box.conf[0])
                        if conf < self.conf_threshold:
                            continue
                        label = model.names[int(box.cls[0])]
                        coords = box.xyxy[0].tolist()
                        results.append(DetectedObject(
                            timestamp=0.0,  # заполняется вызывающим
                            label=label,
                            confidence=round(conf, 4),
                            box=coords,
                        ))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Ошибка детекции объектов кадра: %s", exc)
        return results

    # ------------------------------------------------------------------ публичный API
    def analyze_video(self, video_path: Path) -> List[DetectedObject]:
        """
        Анализирует видео и возвращает список объектов по временной шкале.

        Возвращает пустой список, если модель недоступна (graceful fallback).
        """
        if not self._ensure_model():
            return []

        objects: List[DetectedObject] = []
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
                for obj in self._analyze_frame(frame):
                    obj.timestamp = round(pos / fps, 2)
                    objects.append(obj)
                pos += step
            cap.release()
            logger.info("Объекты: обнаружено %d объектов", len(objects))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Слой объектов пропущен: %s", exc)
        return objects