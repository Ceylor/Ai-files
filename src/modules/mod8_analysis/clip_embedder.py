"""
CLIP-векторизация кадров.

Для каждого кадра (или группы из N кадров) получаем эмбеддинг через
openai/clip-vit-base-patch32 (transformers). Graceful fallback: если
torch/transformers не установлены — слой пропускается.

Эмбеддинги сохраняются в БД в таблице frame_embeddings.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from src.modules.mod8_analysis.schemas import ClipEmbedding

logger = logging.getLogger("analysis.clip")


class ClipEmbedder:
    """CLIP-эмбеддинги кадров с graceful fallback."""

    def __init__(self, frame_group: int = 5, model_name: str = "openai/clip-vit-base-patch32") -> None:
        self.frame_group = frame_group  # анализируем каждый N-й кадр
        self.model_name = model_name
        self._model = None
        self._processor = None

    # ------------------------------------------------------------------ lazy init
    def _ensure_model(self) -> bool:
        """Лениво загружает CLIP-модель. Возвращает True при успехе."""
        if self._model is not None:
            return True
        try:
            import torch  # noqa: F401
            from transformers import CLIPModel, CLIPProcessor  # type: ignore

            self._model = CLIPModel.from_pretrained(self.model_name)
            self._processor = CLIPProcessor.from_pretrained(self.model_name)
            logger.info("ClipEmbedder: модель %s активна", self.model_name)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("ClipEmbedder: недоступен (%s), слой пропускается", exc)
            return False

    # ------------------------------------------------------------------ эмбеддинг
    def _embed_frame(self, bgr_frame: np.ndarray) -> Optional[List[float]]:
        """Вычисляет CLIP-эмбеддинг кадра. Возвращает вектор или None."""
        try:
            rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            inputs = self._processor(images=rgb, return_tensors="pt")
            with np.errstate(all="ignore"):
                import torch  # noqa: F401

                with torch.no_grad():
                    features = self._model.get_image_features(**inputs)
                features = features / features.norm(dim=-1, keepdim=True)
                vec = features.cpu().numpy().flatten().tolist()
            return vec
        except Exception as exc:  # noqa: BLE001
            logger.debug("Ошибка CLIP-эмбеддинга кадра: %s", exc)
            return None

    # ------------------------------------------------------------------ публичный API
    def analyze_video(self, video_path: Path) -> List[ClipEmbedding]:
        """
        Возвращает CLIP-эмбеддинги кадров (каждый N-й кадр).

        Возвращает пустой список, если модель недоступна (graceful fallback).
        """
        if not self._ensure_model():
            return []

        embeddings: List[ClipEmbedding] = []
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.warning("Не удалось открыть видео %s", video_path)
                return []

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_count = max(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), 1)
            step = max(1, int(self.frame_group))
            pos = 0
            while pos < frame_count:
                cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
                ok, frame = cap.read()
                if not ok:
                    break
                vec = self._embed_frame(frame)
                if vec:
                    embeddings.append(ClipEmbedding(timestamp=round(pos / fps, 2), embedding=vec))
                pos += step
            cap.release()
            logger.info("CLIP: получено %d эмбеддингов", len(embeddings))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Слой CLIP пропущен: %s", exc)
        return embeddings