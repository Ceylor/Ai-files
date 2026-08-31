"""
CLIP-векторизация кадров.

Для каждого кадра (или группы из N кадров) получаем эмбеддинг через
openai/clip-vit-base-patch32 (transformers). Graceful fallback: если
torch/transformers не установлены — слой пропускается.

Эмбеддинги сохраняются в БД в таблице frame_embeddings.
"""
from __future__ import annotations

import gc
import logging
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from src.modules.mod8_analysis.schemas import ClipEmbedding
from src.utils.gpu_detector import gpu

logger = logging.getLogger("analysis.clip")


class ClipEmbedder:
    """CLIP-эмбеддинги кадров с graceful fallback."""

    def __init__(self, frame_group: int = 5, model_name: str = "openai/clip-vit-base-patch32",
                 batch_size: int = 1) -> None:
        self.frame_group = frame_group  # анализируем каждый N-й кадр
        self.model_name = model_name
        self.batch_size = max(1, batch_size)
        self._model = None
        self._processor = None
        self._device = "cpu"

    # ------------------------------------------------------------------ lazy init
    def _ensure_model(self) -> bool:
        """Лениво загружает CLIP-модель. Возвращает True при успехе."""
        if self._model is not None:
            return True
        try:
            import torch  # noqa: F401
            from transformers import CLIPModel, CLIPProcessor  # type: ignore

            self._device = gpu.get_clip_device()
            self._model = CLIPModel.from_pretrained(self.model_name).to(self._device)
            self._processor = CLIPProcessor.from_pretrained(self.model_name)
            logger.info("ClipEmbedder: модель %s активна (device=%s)", self.model_name, self._device)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("ClipEmbedder: недоступен (%s), слой пропускается", exc)
            return False

    # ------------------------------------------------------------------ эмбеддинг
    def _embed_frames_batch(self, bgr_frames: List[np.ndarray]) -> List[Optional[List[float]]]:
        """Вычисляет CLIP-эмбеддинги для батча кадров."""
        if not bgr_frames:
            return []
        try:
            import torch  # noqa: F401

            rgbs = [cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in bgr_frames]
            inputs = self._processor(images=rgbs, return_tensors="pt").to(self._device)
            with torch.no_grad():
                features = self._model.get_image_features(**inputs)
                features = features / features.norm(dim=-1, keepdim=True)
                vecs = features.cpu().numpy()
            return [vec.flatten().tolist() for vec in vecs]
        except Exception as exc:  # noqa: BLE001
            logger.debug("Ошибка CLIP-эмбеддинга батча: %s", exc)
            return [None] * len(bgr_frames)

    def _embed_frame(self, bgr_frame: np.ndarray) -> Optional[List[float]]:
        """Вычисляет CLIP-эмбеддинг одного кадра. Возвращает вектор или None."""
        results = self._embed_frames_batch([bgr_frame])
        return results[0] if results else None

    # ------------------------------------------------------------------ публичный API
    def analyze_video(self, video_path: Path) -> List[ClipEmbedding]:
        """
        Возвращает CLIP-эмбеддинги кадров (каждый N-й кадр).

        Обрабатывает кадры батчами (self.batch_size) и очищает память
        после каждого батча, чтобы избежать OOM на длинных видео.

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

            batch_positions: List[int] = []
            batch_frames: List[np.ndarray] = []

            while pos < frame_count:
                cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
                ok, frame = cap.read()
                if not ok:
                    break
                batch_frames.append(frame)
                batch_positions.append(pos)
                if len(batch_frames) >= self.batch_size:
                    vecs = self._embed_frames_batch(batch_frames)
                    for bpos, vec in zip(batch_positions, vecs):
                        if vec:
                            embeddings.append(ClipEmbedding(timestamp=round(bpos / fps, 2), embedding=vec))
                    batch_frames = []
                    batch_positions = []
                    # Free memory between batches
                    del vecs
                    gc.collect()
                    if self._device == "cuda":
                        import torch
                        torch.cuda.empty_cache()
                pos += step

            # Flush remaining frames
            if batch_frames:
                vecs = self._embed_frames_batch(batch_frames)
                for bpos, vec in zip(batch_positions, vecs):
                    if vec:
                        embeddings.append(ClipEmbedding(timestamp=round(bpos / fps, 2), embedding=vec))

            cap.release()
            logger.info("CLIP: получено %d эмбеддингов", len(embeddings))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Слой CLIP пропущен: %s", exc)
        return embeddings