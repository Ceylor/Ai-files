"""
Оркестратор многослойного анализа видео (MultiLayerAnalyzer).

Запускает все слои (эмоции, объекты, движение, золотые моменты, CLIP),
собирает результаты в VideoAnalysisResult, сохраняет в БД (обновляет Video
и таблицу frame_embeddings) и возвращает "золотые моменты" для нарратива.

Тяжёлые операции выполняются в thread-pool через asyncio.to_thread,
чтобы не блокировать event loop.

Длинные видео (> chunk_threshold_sec) обрабатываются по чанкам (по
chunk_duration_sec), чтобы ограничить пиковое потребление памяти.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import ws_manager
from src.modules.mod8_analysis.schemas import (
    VideoAnalysisResult,
    EmotionalFrame,
    DetectedObject,
    MotionSample,
    ClipEmbedding,
    GoldenMoment,
)
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
        chunk_duration_sec: int = 300,
        chunk_threshold_sec: int = 600,
    ) -> None:
        self.emotion_detector = EmotionDetector(frame_interval=emotion_interval)
        self.object_detector = ObjectDetector(frame_interval=object_interval)
        self.motion_analyzer = MotionAnalyzer(step_frames=motion_step)
        self.clip_embedder = ClipEmbedder(frame_group=clip_group)
        self.golden = GoldenMoments(window_sec=2.0, top_k=top_golden)
        self.chunk_duration_sec = chunk_duration_sec
        self.chunk_threshold_sec = chunk_threshold_sec

    # ------------------------------------------------------------------ анализ
    async def analyze(self, video_path: Path, video_id: Optional[int] = None) -> VideoAnalysisResult:
        """
        Полный многослойный анализ видео.

        Видео длиннее chunk_threshold_sec обрабатываются по чанкам, чтобы
        ограничить пиковое потребление памяти. Остальные — целиком.

        Каждый слой имеет graceful fallback (пустой список при сбое).
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Видео не найдено: {video_path}")

        duration = self._get_duration(video_path)
        await ws_manager.broadcast(f"🔍 Многослойный анализ: {video_path.name} (dur={duration:.1f}s)")

        # Длинные видео → чанки (ограничение памяти).
        if duration > self.chunk_threshold_sec:
            await ws_manager.broadcast(
                f"  🧩 Видео длинное ({duration:.0f}s > {self.chunk_threshold_sec}s), "
                f"обработка по чанкам по {self.chunk_duration_sec}s..."
            )
            try:
                return await self._analyze_chunked(video_path, video_id, duration)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Чанковая обработка не удалась (%s), fallback на целый файл", exc)
                await ws_manager.broadcast(f"  ⚠️  Чанковая обработка fallback на полный файл: {exc}")

        return await self._analyze_full(video_path, video_id, duration)

    # ------------------------------------------------------------------ полный анализ
    async def _analyze_full(
        self,
        video_path: Path,
        video_id: Optional[int],
        duration: float,
    ) -> VideoAnalysisResult:
        """Полный многослойный анализ целого видео (без чанков)."""
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

    # ------------------------------------------------------------------ чанковая обработка
    async def _analyze_chunked(
        self,
        video_path: Path,
        video_id: Optional[int],
        total_duration: float,
    ) -> VideoAnalysisResult:
        """
        Обрабатывает длинное видео по чанкам (FFmpeg segment extraction),
        анализирует каждый чанк отдельно, затем объединяет результаты
        со смещением по времени.

        Ограничивает пиковое потребление памяти, т.к. каждый чанк обрабатывается
        независимо, а результат чанка освобождается после анализа.
        """
        chunk_sec = max(30, self.chunk_duration_sec)
        start = 0.0
        chunks: List[Path] = []
        tmp_dir = Path(tempfile.mkdtemp(prefix="aiautoclip_chunk_"))

        emotions: List[EmotionalFrame] = []
        objects: List[DetectedObject] = []
        motion: List[MotionSample] = []
        embeddings: List[ClipEmbedding] = []
        layers_status: Dict[str, str] = {}

        try:
            # 1. Разбиваем видео на чанки.
            chunk_index = 0
            while start < total_duration:
                end = min(start + chunk_sec, total_duration)
                chunk_path = tmp_dir / f"chunk_{chunk_index:03d}.mp4"
                await self._extract_chunk(video_path, start, end, chunk_path)
                chunks.append(chunk_path)
                await ws_manager.broadcast(
                    f"    🧩 Чанк {chunk_index + 1}: {start:.0f}s–{end:.0f}s"
                )
                start = end
                chunk_index += 1

            # 2. Обрабатываем каждый чанк и объединяем результаты с оффсетом.
            for ci, chunk_path in enumerate(chunks):
                chunk_start = ci * chunk_sec
                seg_emotions, seg_objects, seg_motion, seg_embeddings = await self._analyze_chunk(chunk_path)

                for e in seg_emotions:
                    e.timestamp = round(e.timestamp + chunk_start, 2)
                for o in seg_objects:
                    o.timestamp = round(o.timestamp + chunk_start, 2)
                for m in seg_motion:
                    m.timestamp = round(m.timestamp + chunk_start, 2)
                for emb in seg_embeddings:
                    emb.timestamp = round(emb.timestamp + chunk_start, 2)

                emotions.extend(seg_emotions)
                objects.extend(seg_objects)
                motion.extend(seg_motion)
                embeddings.extend(seg_embeddings)

                # Освобождаем память между чанками.
                del seg_emotions, seg_objects, seg_motion, seg_embeddings
                import gc
                gc.collect()

            layers_status = {
                "chunked": "true",
                "chunks": str(len(chunks)),
                "emotions": "ok" if emotions else "empty",
                "objects": "ok" if objects else "empty",
                "motion": "ok" if motion else "empty",
                "clip": "ok" if embeddings else "empty",
            }

            # 3. Золотые моменты по объединённым данным.
            golden_moments = self.golden.compute(emotions, objects, motion, total_duration)
            layers_status["golden_moments"] = "ok" if golden_moments else "empty"

            await ws_manager.broadcast(
                f"✅ Чанковый анализ завершён: эмоции={len(emotions)}, объекты={len(objects)}, "
                f"движение={len(motion)}, эмбеддинги={len(embeddings)}, "
                f"золотые моменты={len(golden_moments)}"
            )

            return VideoAnalysisResult(
                video_id=video_id,
                video_path=str(video_path.resolve()),
                duration=round(total_duration, 2),
                emotions=emotions,
                objects=objects,
                motion=motion,
                golden_moments=golden_moments,
                embeddings=embeddings,
                layers_status=layers_status,
            )
        finally:
            # Очистка временных чанков.
            shutil.rmtree(tmp_dir, ignore_errors=True)

    async def _analyze_chunk(self, chunk_path: Path) -> tuple:
        """Анализирует один чанк (без создания VideoAnalysisResult)."""
        emotions_fut = asyncio.to_thread(self.emotion_detector.analyze_video, chunk_path)
        objects_fut = asyncio.to_thread(self.object_detector.analyze_video, chunk_path)
        motion_fut = asyncio.to_thread(self.motion_analyzer.analyze_video, chunk_path)
        clip_fut = asyncio.to_thread(self.clip_embedder.analyze_video, chunk_path)

        emotions, objects, motion, embeddings = await asyncio.gather(
            emotions_fut, objects_fut, motion_fut, clip_fut,
            return_exceptions=True,
        )
        return (
            emotions if not isinstance(emotions, Exception) else [],
            objects if not isinstance(objects, Exception) else [],
            motion if not isinstance(motion, Exception) else [],
            embeddings if not isinstance(embeddings, Exception) else [],
        )

    @staticmethod
    async def _extract_chunk(video_path: Path, start: float, end: float, out_path: Path) -> None:
        """Извлекает чанк [start, end] из видео через FFmpeg (stream copy когда возможно)."""
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-to", str(end),
            "-i", str(video_path),
            "-c", "copy",  # stream copy — быстро и экономно по CPU
            "-avoid_negative_ts", "make_zero",
            str(out_path),
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            if process.returncode != 0 or not out_path.exists():
                # Если stream copy не дал результат — перекодируем (некоторые контейнеры).
                retry = [
                    "ffmpeg", "-y",
                    "-ss", str(start),
                    "-to", str(end),
                    "-i", str(video_path),
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac",
                    str(out_path),
                ]
                p2 = await asyncio.create_subprocess_exec(
                    *retry,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await p2.communicate()
                if p2.returncode != 0 or not out_path.exists():
                    raise RuntimeError(f"Не удалось извлечь чанк {start}–{end}")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Не удалось извлечь чанк {start}–{end}: {exc}")

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