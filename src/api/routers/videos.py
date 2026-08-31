"""
CRUD-эндпоинты для видео.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database import crud as db_crud

router = APIRouter(prefix="/api/videos", tags=["videos"])


def _video_to_dict(v) -> dict:
    return {
        "id": v.id,
        "file_path": v.file_path,
        "duration": v.duration,
        "resolution": v.resolution,
        "category_id": v.category_id,
        "upload_date": v.upload_date.isoformat() if v.upload_date else None,
        "status": v.status,
        "extra_metadata": v.extra_metadata,
        "analysis_results": v.analysis_results,
        "golden_moments": v.golden_moments,
        "batch_job_id": v.batch_job_id,
    }


@router.post("", response_model=dict)
async def api_create_video(
    file_path: str = Form(...),
    duration: Optional[float] = Form(None),
    resolution: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    status: str = Form("uploaded"),
    db: Session = Depends(get_db),
):
    try:
        v = db_crud.create_video(
            db, file_path=file_path, duration=duration, resolution=resolution,
            category_id=category_id, status=status,
        )
        return _video_to_dict(v)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=dict)
async def api_list_videos(category_id: Optional[int] = None, status: Optional[str] = None,
                          batch_job_id: Optional[int] = None,
                          db: Session = Depends(get_db)):
    videos = db_crud.list_videos(db, category_id=category_id, status=status, batch_job_id=batch_job_id)
    return {"videos": [_video_to_dict(v) for v in videos]}


@router.get("/{video_id}", response_model=dict)
async def api_get_video(video_id: int, db: Session = Depends(get_db)):
    v = db_crud.get_video(db, video_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    return _video_to_dict(v)


@router.patch("/{video_id}/status", response_model=dict)
async def api_update_video_status(
    video_id: int, status: str = Form(...), db: Session = Depends(get_db)
):
    v = db_crud.update_video_status(db, video_id, status=status)
    if v is None:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    return _video_to_dict(v)


@router.delete("/{video_id}", response_model=dict)
async def api_delete_video(video_id: int, db: Session = Depends(get_db)):
    ok = db_crud.delete_video(db, video_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    return {"status": "deleted", "id": video_id}
