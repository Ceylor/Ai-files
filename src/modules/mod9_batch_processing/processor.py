"""
Пакетная обработка видео (BatchProcessor).

Асинхронная очередь последовательной обработки видео:
    ingest → анализ → паттерны → сторибилдер → монтаж → экспорт.

Устойчивость к ошибкам: при сбое одного видео обработка продолжается,
статус помечается "error". Graceful shutdown: очередь проверяет флаг
stop_event и корректно завершает работу.

Интеграция с БД: обновляет статус batch_jobs и videos через CRUD-функции.
После обработки всех видео выполняется композиция клипов по CLIP-эмбеддингам
(ClipComposer) с сохранением результата в БД (новые записи videos).
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import ws_manager
from src.database.session import session_scope
from src.database import crud as db_crud
from src.modules.mod9_batch_processing.composer import ClipComposer

logger = logging.getLogger("batch.processor")


class BatchProcessor:
    """
    Оркестратор пакетной обработки видео.

    Args:
        work_dir: папка для временных файлов и результатов.
        output_dir: папка для итоговых клипов.
        category: категория по умолчанию.
    """

    def __init__(
        self,
        work_dir: Path,
        output_dir: Path,
        category: str = "default",
        similarity_threshold: float = 0.75,
    ) -> None:
        self.work_dir = Path(work_dir)
        self.output_dir = Path(output_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.category = category
        self.composer = ClipComposer(similarity_threshold=similarity_threshold)
        self._stop_event = asyncio.Event()

    # ------------------------------------------------------------------ обработка
    async def process_folder(self, folder_id: int, settings: dict | None = None) -> Dict[str, Any]:
        """
        Обрабатывает все "pending" видео пакетной задачи.

        Обновляет статус batch_job: processing → completed/error.
        После обработки всех видео выполняет композицию клипов и сохраняет
        результат в БД.
        """
        import time
        self._settings = settings or {}
        await self._broadcast(f"🚀 Запуск пакетной обработки задачи #{folder_id}")
        await self._set_batch_status(folder_id, "processing")

        try:
            videos = self._get_pending_videos(folder_id)
            total = len(videos)
            await self._broadcast(f"📁 Найдено видео для обработки: {total}")

            processed = 0
            total_time = 0.0
            for video in videos:
                if self._stop_event.is_set():
                    await self._broadcast("⏹️  Остановлено (graceful shutdown)")
                    break
                try:
                    start = time.monotonic()
                    await self._process_one(video, folder_id)
                    elapsed = time.monotonic() - start
                    total_time += elapsed
                    processed += 1
                    await self._update_batch_progress(folder_id, processed)

                    # Прогресс и оставшееся время.
                    pct = (processed / total) * 100 if total else 0
                    avg = total_time / processed if processed else 0
                    remaining = avg * (total - processed)
                    remaining_min = int(remaining // 60)
                    remaining_sec = int(remaining % 60)
                    await self._broadcast(
                        f"  📊 Прогресс: {processed}/{total} ({pct:.0f}%) "
                        f"— осталось ~{remaining_min}м {remaining_sec}с"
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Ошибка обработки видео %s", video.get("id"))
                    await self._broadcast(f"  ❌ Ошибка видео {video.get('id')}: {exc}")
                    await self._set_video_status(video.get("id"), "error")

            # Доработка 2: композиция клипов и сохранение в БД.
            if not self._stop_event.is_set():
                await self._compose_and_save(folder_id)

            await self._finish_batch(folder_id, processed, total)
            return {"folder_id": folder_id, "processed": processed, "total": total}
        except Exception as exc:  # noqa: BLE001
            logger.exception("Сбой пакетной обработки %s", folder_id)
            await self._set_batch_status(folder_id, "error")
            await self._broadcast(f"❌ Сбой пакетной обработки: {exc}")
            raise

    # ------------------------------------------------------------------ шаги
    async def _process_one(self, video: Dict[str, Any], folder_id: int) -> None:
        """Обрабатывает одно видео: ingest → анализ → паттерны → монтаж → экспорт.

        Каждый шаг выполняется с graceful fallback: если модуль недоступен или
        падает, обработка продолжается со следующими шагами, а итоговый клип
        всё равно создаётся (при полном сбое — копия исходника).
        """
        video_id = video.get("id")
        video_path = Path(video.get("file_path", ""))
        if not video_path.exists():
            raise FileNotFoundError(f"Видео не найдено: {video_path}")

        await self._broadcast(f"  🎬 Обработка видео id={video_id}: {video_path.name}")
        await self._set_video_status(video_id, "processing")

        # Шаг 1: Ingest (нормализация). Graceful fallback — анализ продолжится по исходнику.
        await self._broadcast("    📥 Ingest...")
        ingest_result = await self._run_ingest(video_path)

        # Шаг 2: Многослойный анализ. Graceful fallback — пустой анализ.
        await self._broadcast("    🔍 Анализ...")
        analysis = await self._run_analysis(video_path, video_id)

        # Шаг 2.5: Многослойный скоринг сцен.
        scenes = analysis.get("scenes", []) or ingest_result.get("scenes", [])
        scored_scenes = []
        if scenes:
            await self._broadcast("    📊 Скоринг сцен...")
            scored_scenes = await self._score_scenes(video_path, scenes, analysis)
            if scored_scenes:
                top = scored_scenes[0]
                await self._broadcast(
                    f"    🏆 Лучшая сцена: {top.get('start_sec', 0):.1f}–{top.get('end_sec', 0):.1f}с (скор: {top['score']})"
                )

        # Шаг 3: Поиск паттернов (самообучение). Fallback — None.
        await self._broadcast("    🧠 Паттерны...")
        pattern_profile = await self._find_pattern(video_id)

        # Шаг 4: Сторибилдер + золотые моменты. Fallback — линейная структура.
        await self._broadcast("    📖 Нарратив...")
        story = await self._build_story(video_path, analysis, pattern_profile)

        # Шаг 5: Монтаж + экспорт (через основной пайплайн). Fallback — копия.
        await self._broadcast("    ✂️ Монтаж и экспорт...")
        output_path = await self._run_editing(video_path, story)

        await self._set_video_status(video_id, "completed")
        await self._broadcast(f"    ✅ Готово: {output_path}")

    async def _run_ingest(self, video_path: Path) -> Dict[str, Any]:
        """Нормализация видео через mod0_ingest.

        Graceful fallback: при любой ошибке возвращает исходный путь,
        чтобы последующие шаги продолжили работу.
        """
        try:
            from src.modules.mod0_ingest import VideoIngest0, IngestConfig
            from src.core.config_loader import load_config

            config = load_config()
            ingest_cfg = IngestConfig(
                fast_mode=self._settings.get("fast_mode", False),
            )
            ingest = VideoIngest0(self.work_dir, ingest_cfg)
            result = await ingest.process_video(video_path)
            if result.get("success"):
                return result
            await self._broadcast(f"    ⚠️  Ingest не удался: {result.get('error', 'unknown')}")
            return {"success": False, "meta": {}, "normalized_path": str(video_path)}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ingest упал (%s), продолжаю с исходником", exc)
            await self._broadcast(f"    ⚠️  Ingest fallback: {exc}")
            return {"success": False, "meta": {}, "normalized_path": str(video_path)}

    async def _score_scenes(
        self,
        video_path: Path,
        scenes: List[Dict[str, Any]],
        analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Вычисляет скор интереса для каждой сцены через SceneScorer."""
        try:
            from src.modules.mod8_analysis.scene_scorer import SceneScorer
            scorer = SceneScorer()
            return scorer.score_scenes(video_path, scenes, analysis)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Скоринг сцен не удался: %s", exc)
            return scenes  # fallback — без скоринга

    async def _run_analysis(self, video_path: Path, video_id: int) -> Dict[str, Any]:
        """Многослойный анализ через mod8_analysis.

        Graceful fallback: при недоступности модуля возвращает пустой анализ.
        """
        try:
            from src.modules.mod8_analysis.analyzer import MultiLayerAnalyzer

            analyzer = MultiLayerAnalyzer()
            result = await analyzer.analyze(video_path, video_id=video_id)
            return result.model_dump()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Анализ упал (%s), использую пустой результат", exc)
            await self._broadcast(f"    ⚠️  Анализ fallback: {exc}")
            return {
                "emotions": [],
                "objects": [],
                "motion": [],
                "golden_moments": [],
                "duration": 0,
                "layers_status": {"error": str(exc)},
            }

    async def _find_pattern(self, video_id: int) -> Optional[Dict[str, Any]]:
        """Поиск подходящего паттерна самообучения для видео."""
        try:
            from src.modules.mod7_learning.learner import LearningEngine

            engine = LearningEngine()
            profile = engine.get_category_profile(self.category)
            if profile is not None:
                return profile.serialize()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Паттерны недоступны: %s", exc)
        return None

    async def _build_story(
        self,
        video_path: Path,
        analysis: Dict[str, Any],
        pattern_profile: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Строит нарратив, используя золотые моменты.

        Graceful fallback: при недоступности сторибилдера возвращает None —
        далее используется линейная структура (все фрагменты).
        """
        try:
            from src.utils.story_builder import build_story

            golden = analysis.get("golden_moments", [])
            fragments = [{
                "index": 1,
                "path": str(video_path),
                "filename": video_path.name,
                "duration": analysis.get("duration", 0),
            }]
            return await build_story(
                fragments,
                style_profile=pattern_profile,
                golden_moments=golden,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Сторибилдер недоступен: %s", exc)
            return None

    async def _run_editing(
        self, video_path: Path, story: Optional[Dict[str, Any]]
    ) -> str:
        """
        Реальный монтаж видео через VideoPipeline (модули mod1..mod6).

        Использует тот же полный конвейер, что и run_pipeline, но для одного
        видео. При сбое — graceful fallback на копирование исходника.
        """
        output = self.output_dir / f"{video_path.stem}_clip.mp4"
        try:
            from src.core.config_loader import load_config
            from src.core.pipeline import VideoPipeline

            config = load_config()
            pipeline = VideoPipeline(config)
            output_files = await pipeline.process_batch(
                [video_path],
                style_profile=None,
                category=self.category,
            )
            if output_files:
                await self._broadcast(f"    🎬 Клип смонтирован: {output_files[0].name}")
                return str(output_files[0])
            logger.warning("Пайплайн вернул пустой результат для %s", video_path.name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Реальный монтаж не удался (%s), fallback-копия", exc)
            await self._broadcast(f"    ⚠️  Монтаж fallback: {exc}")

        # Fallback: копируем исходник в output, чтобы не ронять задачу.
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(video_path), str(output))
            await self._broadcast(f"    🎬 Клип сохранён (копия): {output.name}")
            return str(output)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Экспорт (fallback-копия) не удался: %s", exc)
            return str(video_path)

    # ------------------------------------------------------------------ композиция
    async def _compose_and_save(self, folder_id: int) -> None:
        """
        Композиция клипов по CLIP-эмбеддингам обработанных видео и сохранение
        созданных клипов в БД (новые записи videos со статусом 'composed',
        привязанные к batch_job).
        """
        try:
            await self._broadcast("🧩 Композиция клипов по CLIP-эмбеддингам...")
            fragments: List[Dict[str, Any]] = []
            with session_scope() as db:
                videos = db_crud.list_videos(db, batch_job_id=folder_id)
                for v in videos:
                    if v.status != "completed":
                        continue
                    # Выходной путь клипа.
                    output_path = self.output_dir / f"{Path(v.file_path).stem}_clip.mp4"
                    embeddings = db_crud.get_frame_embeddings(db, v.id)
                    emb = None
                    if embeddings:
                        emb = embeddings[0].get("embedding")
                    fragments.append({
                        "video_id": v.id,
                        "path": str(output_path),
                        "embedding": emb,
                    })

            if not fragments:
                await self._broadcast("  ⚠️  Нет обработанных видео для композиции")
                return

            max_clips = self._settings.get("max_clips_per_video", 5)
            plans = self.composer.compose_clips(
                fragments,
                output_dir=self.output_dir,
                prefix="composed",
            )
            if len(plans) > max_clips:
                plans = plans[:max_clips]
                await self._broadcast(
                    f"  📊 Ограничено до {max_clips} композиций (настройка)"
                )
            await self._broadcast(f"  💡 Создано композиций: {len(plans)}")

            with session_scope() as db:
                for plan in plans:
                    out_path = plan.get("output_path")
                    if not out_path:
                        continue
                    try:
                        db_crud.create_video(
                            db,
                            str(out_path),
                            status="composed",
                            category_id=None,
                            batch_job_id=folder_id,
                            extra_metadata={
                                "kind": "composed",
                                "plan_index": plan.get("index"),
                                "name": plan.get("name"),
                                "source_video_ids": [
                                    f.get("video_id") for f in plan.get("fragments", [])
                                ],
                            },
                        )
                    except ValueError:
                        logger.warning("Композиция уже существует, пропуск: %s", out_path)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Не удалось сохранить композицию %s: %s", out_path, exc)
            await self._broadcast("✅ Композиции сохранены в БД")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Сбой композиции %s", folder_id)
            await self._broadcast(f"❌ Ошибка композиции: {exc}")

    # ------------------------------------------------------------------ БД-операции
    def _get_pending_videos(self, folder_id: int) -> list:
        """Возвращает pending-видео пакетной задачи."""
        with session_scope() as db:
            videos = db_crud.get_batch_pending_videos(db, folder_id)
            return [
                {"id": v.id, "file_path": v.file_path, "status": v.status}
                for v in videos
            ]

    async def _set_batch_status(self, folder_id: int, status: str) -> None:
        """Обновляет статус пакетной задачи."""
        try:
            with session_scope() as db:
                db_crud.update_batch_job_status(db, folder_id, status=status)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось обновить статус batch %s: %s", folder_id, exc)

    async def _update_batch_progress(self, folder_id: int, processed: int) -> None:
        try:
            with session_scope() as db:
                db_crud.update_batch_job_progress(db, folder_id, processed)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось обновить прогресс batch %s: %s", folder_id, exc)

    async def _finish_batch(self, folder_id: int, processed: int, total: int) -> None:
        try:
            with session_scope() as db:
                db_crud.finish_batch_job(db, folder_id, processed, total)
            await self._broadcast(f"✅ Пакет #{folder_id} завершён: {processed}/{total}")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось завершить batch %s: %s", folder_id, exc)

    async def _set_video_status(self, video_id: int, status: str) -> None:
        try:
            with session_scope() as db:
                db_crud.update_video_status(db, video_id, status=status)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось обновить статус видео %s: %s", video_id, exc)

    # ------------------------------------------------------------------ утилиты
    async def shutdown(self) -> None:
        """Устанавливает флаг graceful shutdown."""
        await self._broadcast("⏹️  Получен сигнал завершения, останавливаю очередь...")
        self._stop_event.set()

    async def _broadcast(self, message: str) -> None:
        await ws_manager.broadcast(message)
        logger.info(message)