"""
Статус приложения.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.state import REF_DIR, learning_engine
from src.database.session import get_db
from src.database import crud as db_crud

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status")
async def get_status(db: Session = Depends(get_db)):
    try:
        db_categories = db_crud.list_categories(db)
        db_videos = db_crud.list_videos(db)
        db_batches = db_crud.list_batch_jobs(db)
        db_summary = {
            "categories": len(db_categories),
            "videos": len(db_videos),
            "batches": len(db_batches),
        }
    except Exception as e:
        db_summary = {"error": str(e)}
    return {
        "status": "running",
        "version": "2.0",
        "categories": [d.name for d in REF_DIR.iterdir() if d.is_dir()] if REF_DIR.exists() else [],
        "learning": learning_engine.stats(),
        "database": db_summary,
    }
