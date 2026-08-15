"""
Базовые CRUD-операции для работы с категориями, видео, анализом и пакетной обработкой.

Реализованы как независимые функции, принимающие сессию SQLAlchemy —
это позволяет использовать их как из FastAPI (через Depends(get_db)),
так и из фоновых задач (через session_scope()).

Функции покрывают:
    Categories:   create/get/list/update/delete (+ получение подкатегорий).
    Videos:       create/get/list/update_status/delete.
    Анализ:       save_analysis_results, save_frame_embeddings, get_analysis.
    BatchJobs:    create/update_status/update_progress/finish/get/list/
                  get_pending_videos/get_by_folder.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import BatchJob, Category, FrameEmbedding, Video

logger = logging.getLogger("database.crud")


# ==============================================================================
# CATEGORIES
# ==============================================================================
def create_category(
    db: Session, name: str, description: Optional[str] = None,
    parent_id: Optional[int] = None,
) -> Category:
    """Создаёт новую категорию. Бросает ValueError при дубликате имени."""
    if get_category_by_name(db, name):
        raise ValueError(f"Категория с именем '{name}' уже существует")
    if parent_id is not None and get_category(db, parent_id) is None:
        raise ValueError(f"Родительская категория id={parent_id} не найдена")

    category = Category(name=name, description=description, parent_id=parent_id)
    db.add(category)
    db.commit()
    db.refresh(category)
    logger.info("Создана категория: %s (id=%s)", name, category.id)
    return category


def get_category(db: Session, category_id: int) -> Optional[Category]:
    """Возвращает категорию по id или None."""
    return db.get(Category, category_id)


def get_category_by_name(db: Session, name: str) -> Optional[Category]:
    """Возвращает категорию по имени или None."""
    return db.scalar(select(Category).where(Category.name == name))


def list_categories(
    db: Session, parent_id: Optional[int] = None, include_root: bool = False,
) -> List[Category]:
    """Список категорий (опционально по родителю)."""
    stmt = select(Category).order_by(Category.name)
    if parent_id is not None:
        if include_root and parent_id is None:
            stmt = stmt.where(Category.parent_id.is_(None))
        else:
            stmt = stmt.where(Category.parent_id == parent_id)
    return list(db.scalars(stmt))


def update_category(
    db: Session, category_id: int, *,
    name: Optional[str] = None, description: Optional[str] = None,
    parent_id: Optional[int] = None,
) -> Optional[Category]:
    """Обновляет поля категории. Возвращает None, если категория не найдена."""
    category = get_category(db, category_id)
    if category is None:
        return None
    if name is not None:
        existing = get_category_by_name(db, name)
        if existing and existing.id != category_id:
            raise ValueError(f"Категория с именем '{name}' уже существует")
        category.name = name
    if description is not None:
        category.description = description
    if parent_id is not None:
        if parent_id == category_id:
            raise ValueError("Категория не может быть родителем самой себя")
        if get_category(db, parent_id) is None:
            raise ValueError(f"Родительская категория id={parent_id} не найдена")
        category.parent_id = parent_id
    db.commit()
    db.refresh(category)
    logger.info("Категория обновлена: id=%s", category_id)
    return category


def delete_category(db: Session, category_id: int) -> bool:
    """Удаляет категорию. Возвращает True при успехе, False если не найдена."""
    category = get_category(db, category_id)
    if category is None:
        return False
    db.delete(category)
    db.commit()
    logger.info("Категория удалена: id=%s", category_id)
    return True


# ==============================================================================
# VIDEOS
# ==============================================================================
def create_video(
    db: Session, file_path: str, *,
    duration: Optional[float] = None, resolution: Optional[str] = None,
    category_id: Optional[int] = None, status: str = "uploaded",
    extra_metadata: Optional[Dict[str, Any]] = None,
    batch_job_id: Optional[int] = None,
) -> Video:
    """Создаёт запись о видеофайле. Бросает ValueError при дубликате пути."""
    if get_video_by_path(db, file_path) is not None:
        raise ValueError(f"Видео с путём '{file_path}' уже существует")
    if category_id is not None and get_category(db, category_id) is None:
        raise ValueError(f"Категория id={category_id} не найдена")

    video = Video(
        file_path=file_path, duration=duration, resolution=resolution,
        category_id=category_id, status=status, extra_metadata=extra_metadata,
        batch_job_id=batch_job_id,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    logger.info("Создана запись видео: %s (id=%s)", file_path, video.id)
    return video


def get_video(db: Session, video_id: int) -> Optional[Video]:
    """Возвращает видео по id или None."""
    return db.get(Video, video_id)


def get_video_by_path(db: Session, file_path: str) -> Optional[Video]:
    """Возвращает видео по пути или None."""
    return db.scalar(select(Video).where(Video.file_path == file_path))


def list_videos(
    db: Session, category_id: Optional[int] = None, status: Optional[str] = None,
    batch_job_id: Optional[int] = None,
) -> List[Video]:
    """Список видео с опциональной фильтрацией по категории и статусу."""
    stmt = select(Video).order_by(Video.upload_date.desc())
    if category_id is not None:
        stmt = stmt.where(Video.category_id == category_id)
    if status is not None:
        stmt = stmt.where(Video.status == status)
    if batch_job_id is not None:
        stmt = stmt.where(Video.batch_job_id == batch_job_id)
    return list(db.scalars(stmt))


def update_video_status(
    db: Session, video_id: int, status: str,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Video]:
    """Обновляет статус (и, опционально, extra_metadata) видео."""
    video = get_video(db, video_id)
    if video is None:
        return None
    video.status = status
    if extra_metadata is not None:
        video.extra_metadata = extra_metadata
    db.commit()
    db.refresh(video)
    logger.info("Статус видео обновлён: id=%s -> %s", video_id, status)
    return video


def delete_video(db: Session, video_id: int) -> bool:
    """Удаляет запись о видео. Возвращает True при успехе, False если не найдена."""
    video = get_video(db, video_id)
    if video is None:
        return False
    db.delete(video)
    db.commit()
    logger.info("Видео удалено: id=%s", video_id)
    return True


# ==============================================================================
# АНАЛИЗ (многослойный)
# ==============================================================================
def save_analysis_results(
    db: Session, video_id: int,
    analysis: Dict[str, Any], golden_moments: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Video]:
    """
    Сохраняет результаты многослойного анализа в запись Video.

    Обновляет поля analysis_results и golden_moments, а также статус на "analyzed".

    Returns:
        Video или None, если видео не найдено.
    """
    video = get_video(db, video_id)
    if video is None:
        return None
    video.analysis_results = analysis
    video.golden_moments = golden_moments or []
    video.status = "analyzed"
    db.commit()
    db.refresh(video)
    logger.info("Результаты анализа сохранены для видео id=%s", video_id)
    return video


def save_frame_embeddings(
    db: Session, video_id: int, embeddings: List[Dict[str, Any]],
) -> int:
    """
    Сохраняет CLIP-эмбеддинги кадров в таблицу frame_embeddings.

    Args:
        embeddings: список dict [{"timestamp": float, "embedding": [..]}, ...]

    Returns:
        Число сохранённых эмбеддингов.
    """
    if get_video(db, video_id) is None:
        logger.warning("Видео id=%s не найдено, эмбеддинги не сохранены", video_id)
        return 0

    # Очищаем старые эмбеддинги видео.
    db.query(FrameEmbedding).filter(FrameEmbedding.video_id == video_id).delete()
    db.flush()

    saved = 0
    for item in embeddings:
        db.add(FrameEmbedding(
            video_id=video_id,
            timestamp=float(item.get("timestamp", 0.0)),
            embedding=item.get("embedding"),
        ))
        saved += 1
    db.commit()
    logger.info("Сохранено эмбеддингов для видео id=%s: %d", video_id, saved)
    return saved


def get_analysis(db: Session, video_id: int) -> Optional[Dict[str, Any]]:
    """Возвращает результаты анализа видео (analysis_results + golden_moments)."""
    video = get_video(db, video_id)
    if video is None:
        return None
    return {
        "analysis_results": video.analysis_results,
        "golden_moments": video.golden_moments,
    }


def get_frame_embeddings(db: Session, video_id: int) -> List[Dict[str, Any]]:
    """Возвращает эмбеддинги кадров видео."""
    rows = (
        db.query(FrameEmbedding)
        .filter(FrameEmbedding.video_id == video_id)
        .order_by(FrameEmbedding.timestamp)
        .all()
    )
    return [
        {"timestamp": r.timestamp, "embedding": r.embedding}
        for r in rows
    ]


# ==============================================================================
# ПАКЕТНАЯ ОБРАБОТКА (mod9)
# ==============================================================================
def create_batch_job(
    db: Session, folder_path: str, *,
    status: str = "pending", total_videos: int = 0,
) -> BatchJob:
    """Создаёт пакетную задачу для папки с видео."""
    batch = BatchJob(
        folder_path=folder_path,
        status=status,
        total_videos=total_videos,
        processed_videos=0,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    logger.info("Создана пакетная задача id=%s (путь: %s)", batch.id, folder_path)
    return batch


def get_batch_job(db: Session, batch_id: int) -> Optional[BatchJob]:
    """Возвращает пакетную задачу по id или None."""
    return db.get(BatchJob, batch_id)


def list_batch_jobs(
    db: Session, status: Optional[str] = None,
) -> List[BatchJob]:
    """Список пакетных задач (опционально по статусу)."""
    stmt = select(BatchJob).order_by(BatchJob.created_at.desc())
    if status is not None:
        stmt = stmt.where(BatchJob.status == status)
    return list(db.scalars(stmt))


def update_batch_job_status(
    db: Session, batch_id: int, status: str,
) -> Optional[BatchJob]:
    """Обновляет статус пакетной задачи."""
    batch = get_batch_job(db, batch_id)
    if batch is None:
        return None
    batch.status = status
    db.commit()
    db.refresh(batch)
    logger.info("Статус пакетной задачи обновлён: id=%s -> %s", batch_id, status)
    return batch


def update_batch_job_progress(
    db: Session, batch_id: int, processed_videos: int,
) -> Optional[BatchJob]:
    """Обновляет счётчик обработанных видео пакетной задачи."""
    batch = get_batch_job(db, batch_id)
    if batch is None:
        return None
    batch.processed_videos = processed_videos
    db.commit()
    db.refresh(batch)
    logger.info(
        "Прогресс пакетной задачи id=%s: %d обработано", batch_id, processed_videos
    )
    return batch


def finish_batch_job(
    db: Session, batch_id: int, processed_videos: int, total_videos: int,
    status: str = "completed",
) -> Optional[BatchJob]:
    """Завершает пакетную задачу: статус, счётчики и finished_at."""
    batch = get_batch_job(db, batch_id)
    if batch is None:
        return None
    batch.status = status
    batch.processed_videos = processed_videos
    batch.total_videos = total_videos
    batch.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(batch)
    logger.info("Пакетная задача завершена: id=%s (%s)", batch_id, status)
    return batch


def get_batch_pending_videos(db: Session, batch_id: int) -> List[Video]:
    """Возвращает видео пакетной задачи со статусом 'pending'."""
    stmt = (
        select(Video)
        .where(Video.batch_job_id == batch_id, Video.status == "pending")
        .order_by(Video.upload_date)
    )
    return list(db.scalars(stmt))