"""
Engine, фабрика сессий и зависимость FastAPI для базы данных.

URL базы данных берётся из переменной окружения DATABASE_URL.
По умолчанию — SQLite файл data/app.db (не требует внешнего сервера).

Экспортируемые элементы:
    engine         — SQLAlchemy Engine (создаётся один раз);
    SessionLocal   — фабрика сессий;
    get_db         — генератор-зависимость для FastAPI (yield session);
    session_scope  — контекстный менеджер для использования вне FastAPI;
    init_db        — создание всех таблиц (для простоты, при первом запуске).
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import AsyncIterator, Iterator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.base import Base

logger = logging.getLogger("database.session")

# По умолчанию SQLite в папке data/. Можно переопределить через DATABASE_URL.
DEFAULT_DB_URL = "sqlite:///./data/app.db"


def _resolve_db_url() -> str:
    """Возвращает URL БД из окружения или дефолтный (SQLite)."""
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url
    # Гарантируем существование папки для SQLite-файла.
    db_path = Path("./data")
    db_path.mkdir(parents=True, exist_ok=True)
    return DEFAULT_DB_URL


def _configure_sqlite(engine: Engine) -> None:
    """Включает FK-ограничения для SQLite (по умолчанию выключены)."""

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        except Exception:  # noqa: BLE001
            pass


_db_url = _resolve_db_url()

# echo=False — чистое логирование; при отладке можно включить.
engine = create_engine(_db_url, echo=False, future=True)

# Для SQLite включаем поддержку внешних ключей.
if _db_url.startswith("sqlite"):
    _configure_sqlite(engine)

# Пул подключений: для SQLite check_same_thread=False требуется при
# использовании из нескольких потоков (asyncio.to_thread).
if _db_url.startswith("sqlite"):
    engine = create_engine(
        _db_url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )
    _configure_sqlite(engine)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Создаёт все таблицы, если они ещё не существуют (для первого запуска)."""
    import src.database.models  # noqa: F401  (регистрирует модели)

    Base.metadata.create_all(bind=engine)
    logger.info("База данных инициализирована (созданы таблицы)")


# ---------------------------------------------------------------------------
# Зависимость для FastAPI
# ---------------------------------------------------------------------------
def get_db() -> Iterator[Session]:
    """
    FastAPI-зависимость: выдаёт сессию БД на время запроса и закрывает её.

    Использование:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Контекстный менеджер сессии (вне FastAPI)
# ---------------------------------------------------------------------------
@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Контекстный менеджер сессии с авто-коммитом/откатом.

    Использование:
        with session_scope() as db:
            db.add(obj)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()