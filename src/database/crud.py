"""
Базовые CRUD-операции для работы с категориями и видео.

Реализованы как независимые функции, принимающие сессию SQLAlchemy —
это позволяет использовать их как из FastAPI (через Depends(get_db)),
так и из фоновых задач (через session_scope()).

Функции покрывают:
    Categories: create/get/list/update/delete (+ получение подкатегорий).
    Videos:     create/get/list/update_status/delete.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import Category, Video

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
    """
    Список категорий.

    Args:
        parent_id: если указан — только подкатегории данного parent;
            иначе все категории.
        include_root: включать ли категории без parent (корневые) при
            filter по parent_id.
    """
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
) -> Video:
    """Создаёт запись о видеофайле. Бросает ValueError при дубликате пути."""
    if get_video_by_path(db, file_path) is not None:
        raise ValueError(f"Видео с путём '{file_path}' уже существует")
    if category_id is not None and get_category(db, category_id) is None:
        raise ValueError(f"Категория id={category_id} не найдена")

    video = Video(
        file_path=file_path, duration=duration, resolution=resolution,
        category_id=category_id, status=status, extra_metadata=extra_metadata,
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
) -> List[Video]:
    """Список видео с опциональной фильтрацией по категории и статусу."""
    stmt = select(Video).order_by(Video.upload_date.desc())
    if category_id is not None:
        stmt = stmt.where(Video.category_id == category_id)
    if status is not None:
        stmt = stmt.where(Video.status == status)
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