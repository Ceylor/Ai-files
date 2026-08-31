"""
Эндпоинты многослойного анализа контента (модуль 8).
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from src.database.session import get_db, session_scope
from src.database import crud as db_crud
from src.modules.mod8_analysis.schemas import VideoAnalysisResult
from src.utils.logger import ws_manager

logger = logging.getLogger("api.analysis")

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/analyze/{video_id}")
async def api_analyze_video(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    performance_mode: str = Form("normal"),
):
    """
    Асинхронный запуск полного многослойного анализа видео.

    Запускается в фоне (BackgroundTasks). Результаты сохраняются в БД.

    performance_mode: 'fast' | 'normal' | 'quality' — профиль производительности.
    """
    video = db_crud.get_video(db, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Видео не найдено")

    video_path = Path(video.file_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Файл видео не найден: {video.file_path}")

    db_crud.update_video_status(db, video_id, status="analyzing")

    background_tasks.add_task(run_analysis_task, video_id, video_path, performance_mode)
    return {"status": "started", "video_id": video_id, "message": "Анализ запущен в фоне"}


async def run_analysis_task(video_id: int, video_path: Path, performance_mode: str = "normal"):
    """Фоновая задача многослойного анализа + сохранение в БД."""
    try:
        await ws_manager.broadcast(
            f"🎬 Старт многослойного анализа видео id={video_id}... (performance={performance_mode})"
        )
        from src.core.config_loader import load_performance_config
        performance = load_performance_config(performance_mode)
        from src.modules.mod8_analysis.analyzer import MultiLayerAnalyzer
        kwargs: dict = {}
        if performance.get("chunk_duration_seconds"):
            kwargs["chunk_duration_sec"] = int(performance["chunk_duration_seconds"])
        if performance.get("clip_batch_size"):
            kwargs["clip_batch_size"] = int(performance["clip_batch_size"])
        analyzer_local = MultiLayerAnalyzer(**kwargs)
        result: VideoAnalysisResult = await analyzer_local.analyze(video_path, video_id=video_id)

        with session_scope() as db:
            db_crud.save_analysis_results(
                db,
                video_id,
                analysis={
                    "emotions": [e.model_dump() for e in result.emotions],
                    "objects": [o.model_dump() for o in result.objects],
                    "motion": [m.model_dump() for m in result.motion],
                    "duration": result.duration,
                    "layers_status": result.layers_status,
                },
                golden_moments=[g.model_dump() for g in result.golden_moments],
            )
            if result.embeddings:
                db_crud.save_frame_embeddings(
                    db,
                    video_id,
                    [{"timestamp": e.timestamp, "embedding": e.embedding} for e in result.embeddings],
                )

        await ws_manager.broadcast(
            f"✅ Анализ видео id={video_id} завершён и сохранён в БД. "
            f"Золотых моментов: {len(result.golden_moments)}"
        )
    except Exception as e:
        await ws_manager.broadcast(f"❌ Ошибка анализа видео id={video_id}: {e}")
        logger.exception("Ошибка анализа видео id=%s", video_id)
        try:
            with session_scope() as db:
                db_crud.update_video_status(db, video_id, status="error")
        except Exception:
            pass


@router.get("/{video_id}")
async def api_get_analysis(video_id: int, db: Session = Depends(get_db)):
    """Возвращает результаты анализа видео."""
    result = db_crud.get_analysis(db, video_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    if not result["analysis_results"] and not result["golden_moments"]:
        return {"status": "not_analyzed", "video_id": video_id}
    return {"status": "analyzed", "video_id": video_id, **result}


@router.get("/{video_id}/embeddings")
async def api_get_embeddings(video_id: int, db: Session = Depends(get_db)):
    """Возвращает CLIP-эмбеддинги кадров видео."""
    embeddings = db_crud.get_frame_embeddings(db, video_id)
    return {"video_id": video_id, "count": len(embeddings), "embeddings": embeddings}
