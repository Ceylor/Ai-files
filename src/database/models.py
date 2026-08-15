"""
SQLAlchemy 2.0 модели базы данных AI AutoClip Pro 2.0.

Таблицы:
    categories          — категории клипов (с иерархией через parent_id);
    videos              — загруженные видеофайлы;
    learning_patterns   — паттерны, извлечённые из референсов (самообучение);
    processing_history  — история запусков монтажа;
    user_feedback       — оценки пользователя (для будущего дообучения);
    frame_embeddings    — CLIP-эмбеддинги кадров (многослойный анализ).

Стиль: SQLAlchemy 2.0 (Mapped, mapped_column, relationship).
Все JSON-поля хранятся как JSON (SQLite/PostgreSQL-совместимо через generic JSON).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin


# ==============================================================================
# 1. Категории клипов
# ==============================================================================
class Category(Base, TimestampMixin):
    """Категория клипов (путешествия, спорт, туториалы, ...). Поддерживает иерархию."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    # created_at — из TimestampMixin.

    # --- отношения -------------------------------------------------------
    parent: Mapped[Optional["Category"]] = relationship(
        remote_side="Category.id", back_populates="children"
    )
    children: Mapped[List["Category"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    videos: Mapped[List["Video"]] = relationship(back_populates="category")
    patterns: Mapped[List["LearningPattern"]] = relationship(back_populates="category")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Category id={self.id} name={self.name!r}>"


# ==============================================================================
# 2. Видеофайлы
# ==============================================================================
class Video(Base, TimestampMixin):
    """Загруженный видеофайл с метаданными и результатами анализа."""

    __tablename__ = "videos"
    __table_args__ = (UniqueConstraint("file_path", name="uq_videos_file_path"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="uploaded", nullable=False
    )
    # Доп. параметры видео. Название extra_metadata — т.к. "metadata"
    # зарезервировано в Declarative API SQLAlchemy.
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # --- результаты многослойного анализа (JSON) -------------------------
    analysis_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    golden_moments: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # --- отношения -------------------------------------------------------
    category: Mapped[Optional["Category"]] = relationship(back_populates="videos")
    patterns: Mapped[List["LearningPattern"]] = relationship(back_populates="video")
    feedback: Mapped[List["UserFeedback"]] = relationship(back_populates="video")
    embeddings: Mapped[List["FrameEmbedding"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Video id={self.id} path={self.file_path!r}>"


# ==============================================================================
# 3. Паттерны самообучения
# ==============================================================================
class LearningPattern(Base, TimestampMixin):
    """Паттерн успеха, извлечённый из референсного клипа (самообучение)."""

    __tablename__ = "learning_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("videos.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    # Вектор признаков (10 чисел). JSON — для SQLite/PostgreSQL.
    vector: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    structure: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    tempo: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    transitions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    color_profile: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    music_profile: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # created_at — из TimestampMixin.

    # --- отношения -------------------------------------------------------
    video: Mapped[Optional["Video"]] = relationship(back_populates="patterns")
    category: Mapped[Optional["Category"]] = relationship(back_populates="patterns")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<LearningPattern id={self.id} category_id={self.category_id}>"


# ==============================================================================
# 4. История обработки
# ==============================================================================
class ProcessingHistory(Base, TimestampMixin):
    """Запись о запуске монтажа (история обработки)."""

    __tablename__ = "processing_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    input_video_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    output_video_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    used_pattern_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="started", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProcessingHistory id={self.id} status={self.status!r}>"


# ==============================================================================
# 5. Оценки пользователя
# ==============================================================================
class UserFeedback(Base, TimestampMixin):
    """Оценка пользователя (1–5) для будущего дообучения."""

    __tablename__ = "user_feedback"
    __table_args__ = (UniqueConstraint("video_id", name="uq_user_feedback_video_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..5
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # created_at — из TimestampMixin.

    # --- отношения -------------------------------------------------------
    video: Mapped["Video"] = relationship(back_populates="feedback")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserFeedback id={self.id} video_id={self.video_id} rating={self.rating}>"


# ==============================================================================
# 6. CLIP-эмбеддинги кадров (многослойный анализ)
# ==============================================================================
class FrameEmbedding(Base, TimestampMixin):
    """CLIP-эмбеддинг кадра видео (для поиска/кластеризации по смыслу)."""

    __tablename__ = "frame_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)

    # --- отношения -------------------------------------------------------
    video: Mapped["Video"] = relationship(back_populates="embeddings")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FrameEmbedding id={self.id} video_id={self.video_id} t={self.timestamp}>"