"""
Пакет базы данных AI AutoClip Pro 2.0.

Содержит:
    - base.py   — DeclarativeBase и общие миксины;
    - models.py — SQLAlchemy-модели (categories, videos, learning_patterns,
                  processing_history, user_feedback, frame_embeddings, batch_jobs);
    - session.py— engine, фабрика сессий, зависимость FastAPI;
    - crud.py   — базовые CRUD-операции.

Используется SQLAlchemy 2.0 стиль (Mapped, mapped_column).
Миграции управляются через Alembic (папка migrations/).
"""

from src.database.base import Base, TimestampMixin
from src.database.session import (
    engine,
    get_db,
    init_db,
    session_scope,
)
from src.database.models import (  # noqa: F401  (регистрация моделей в метаданных)
    BatchJob,
    Category,
    FrameEmbedding,
    LearningPattern,
    ProcessingHistory,
    UserFeedback,
    Video,
)

__all__ = [
    "Base",
    "TimestampMixin",
    "engine",
    "get_db",
    "init_db",
    "session_scope",
    "Category",
    "Video",
    "LearningPattern",
    "ProcessingHistory",
    "UserFeedback",
    "FrameEmbedding",
    "BatchJob",
]