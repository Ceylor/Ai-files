"""
Оркестратор многослойного анализа видео (MultiLayerAnalyzer).

Запускает все слои (эмоции, объекты, движение, золотые моменты, CLIP),
собирает результаты в VideoAnalysisResult, сохраняет в БД (обновляет Video
и таблицу frame_embeddings) и возвращает "золотые моменты" для нарратива.

Тяжёлые операции выполняются в thread-pool через asyncio.to_thread,
чтобы не блокировать event loop.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import ws_manager
from src.modules.mod8_analysis.schemas import VideoAnalysisResult
from src.modules.mod8_analysis.emotion_detector import EmotionDetector
from src.modules.mod8_analysis.object_detector import ObjectDetector
from src.modules.mod8_analysis.motion_analyzer import MotionAnalyzer
from src.modules.mod8_analysis.golden_moments import GoldenMoments
from src.modules.mod8_analysis.clip_embedder import ClipEmbedder

logger = logging.getLogger("analysis.analyzer")


class MultiLayerAnalyzer:
    """Оркестратор многослойного анализа контента."""

    def __init__(
        self,
        emotion_interval: float = 1.0,
        object_interval: float = 1.0,
        motion_step: int = 5,
        clip_group: int = 5,
        top_golden: int = 3,
    ) -> None:
        self.emotion_detector = EmotionDetector(frame_interval=emotion_interval)
        self.object_detector = ObjectDetector(frame_interval=object_interval)
        self.motion_analyzer = MotionAnalyzer(step_frames=motion_step)
        self.clip_embedder = ClipEmbedder(frame_group=clip_group)
        self.golden = GoldenMoments(window_sec=2.0, top_k=top_golden)

    # ------------------------------------------------------------------ анализ
    async def analyze(self, video_path: Path, video_id: Optional[int] = None) -> VideoAnalysisResult:
        """
        Полный многослойный анализ видео.

        Каждый слой выполняется в thread-pool, имеет graceful fallback
        (при недоступности модели возвращает пустой список).

        Returns:
            VideoAnalysisResult с результатами всех слоёв.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Видео не найдено: {video_path}")

        duration = self._get_duration(video_path)
        await ws_manager.broadcast(f"🔍 Многослойный анализ: {video_path.name} (dur={duration:.1f}s)")

        # Запускаем слои параллельно в thread-pool.
        emotions_fut = asyncio.to_thread(self.emotion_detector.analyze_video, video_path)
        objects_fut = asyncio.to_thread(self.object_detector.analyze_video, video_path)
        motion_fut = asyncio.to_thread(self.motion_analyzer.analyze_video, video_path)
        clip_fut = asyncio.to_thread(self.clip_embedder.analyze_video, video_path)

        emotions, objects, motion, embeddings = await asyncio.gather(
            emotions_fut, objects_fut, motion_fut, clip_fut,
            return_exceptions=True,
        )

        # Обрабатываем возможные исключения (graceful fallback).
        layers_status: Dict[str, str] = {}
        emotions = self._safe(emotions, "emotions", layers_status)
        objects = self._safe(objects, "objects", layers_status)
        motion = self._safe(motion, "motion", layers_status)
        embeddings = self._safe(embeddings, "clip", layers_status)

        # Золотые моменты.
        golden_moments = self.golden.compute(emotions, objects, motion, duration)
        layers_status["golden_moments"] = "ok" if golden_moments else "empty"

        result = VideoAnalysisResult(
            video_id=video_id,
            video_path=str(video_path.resolve()),
            duration=round(duration, 2),
            emotions=emotions,
            objects=objects,
            motion=motion,
            golden_moments=golden_moments,
            embeddings=embeddings,
            layers_status=layers_status,
        )

        await ws_manager.broadcast(
            f"✅ Анализ завершён: эмоции={len(emotions)}, объекты={len(objects)}, "
            f"движение={len(motion)}, эмбеддинги={len(embeddings)}, "
            f"золотые моменты={len(golden_moments)}"
        )
        return result

    @staticmethod
    def _safe(value, layer: str, status: Dict[str, str]) -> List:
        """Обрабатывает результат слоя, нормализуя исключения в пустой список."""
        if isinstance(value, Exception):
            logger.warning("Слой %s завершился ошибкой: %s", layer, value)
            status[layer] = f"error: {value}"
            return []
        status[layer] = "ok" if value else "empty"
        return value or []

    @staticmethod
    def _get_duration(video_path: Path) -> float:
        """Возвращает длительность видео через OpenCV."""
        try:
            import cv2

            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return 0.0
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            return (count / fps) if fps > 0 else 0.0
        except Exception:  # noqa: BLE001
            return 0.0


# ==============================================================================
# Высокоуровневая функция анализа
# ==============================================================================
async def analyze_video(video_path: Path, video_id: Optional[int] = None) -> VideoAnalysisResult:
    """Удобная обёртка: создаёт анализатор и запускает полный анализ."""
    analyzer = MultiLayerAnalyzer()
    return await analyzer.analyze(video_path, video_id=video_id)