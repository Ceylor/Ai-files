"""
Базовый DeclarativeBase и общие миксины для SQLAlchemy 2.0.

Здесь определён общий предок всех моделей (Base), а также миксины,
используемые несколькими таблицами (например, временные метки created_at).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Единый базовый класс для всех ORM-моделей проекта."""

    # Канонический способ объявления именованных типов в SQLAlchemy 2.0.
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


class TimestampMixin:
    """Добавляет столбец created_at с автозаполнением текущим временем."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )