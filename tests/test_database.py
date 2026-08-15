"""
Тесты схемы базы данных (SQLAlchemy 2.0) и CRUD-операций.

Проверяют:
    - создание всех таблиц через init_db;
    - CRUD для категорий (создание, иерархия, дубликаты, обновление, удаление);
    - CRUD для видео (создание, дубликаты, фильтрация, статусы, удаление);
    - целостность связей (категория → видео, FK-ограничения).

Для изоляции используются временные SQLite-базы (tmp_path), чтобы не
затрагивать продакшен-файл data/app.db.

Запуск:
    python -m pytest tests/test_database.py -v

Требования: pytest, sqlalchemy.
"""
from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.base import Base
from src.database import crud
from src.database.models import Category, Video


# ==============================================================================
# FIXTURES: изолированная временная БД
# ==============================================================================
@pytest.fixture()
def db_session(tmp_path: Path) -> Generator[Session, None, None]:
    """Создаёт временную SQLite-БД и сессию для тестов."""
    db_file = tmp_path / "test_app.db"
    engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# ==============================================================================
# ТЕСТЫ: КАТЕГОРИИ
# ==============================================================================
def test_create_category(db_session: Session):
    """Создание категории и чтение по id."""
    cat = crud.create_category(db_session, name="travel", description="Путешествия")
    assert cat.id is not None
    assert cat.name == "travel"
    assert cat.description == "Путешествия"

    fetched = crud.get_category(db_session, cat.id)
    assert fetched is not None
    assert fetched.name == "travel"


def test_create_category_duplicate_raises(db_session: Session):
    """Дубликат имени категории вызывает ValueError."""
    crud.create_category(db_session, name="sport")
    with pytest.raises(ValueError):
        crud.create_category(db_session, name="sport")


def test_category_hierarchy(db_session: Session):
    """Иерархия категорий через parent_id."""
    parent = crud.create_category(db_session, name="video")
    child = crud.create_category(db_session, name="shorts", parent_id=parent.id)

    assert child.parent_id == parent.id
    # Проверяем, что child отображается как подкатегория.
    children = crud.list_categories(db_session, parent_id=parent.id)
    assert len(children) == 1
    assert children[0].name == "shorts"


def test_create_category_bad_parent_raises(db_session: Session):
    """Несуществующий родитель вызывает ValueError."""
    with pytest.raises(ValueError):
        crud.create_category(db_session, name="bad", parent_id=999)


def test_update_category(db_session: Session):
    """Обновление имени категории."""
    cat = crud.create_category(db_session, name="old")
    updated = crud.update_category(db_session, cat.id, name="new")
    assert updated is not None
    assert updated.name == "new"


def test_update_category_missing_returns_none(db_session: Session):
    """Обновление несуществующей категории возвращает None."""
    assert crud.update_category(db_session, 999, name="x") is None


def test_delete_category(db_session: Session):
    """Удаление категории."""
    cat = crud.create_category(db_session, name="temp")
    assert crud.delete_category(db_session, cat.id) is True
    assert crud.get_category(db_session, cat.id) is None


def test_delete_category_missing_returns_false(db_session: Session):
    """Удаление несуществующей категории возвращает False."""
    assert crud.delete_category(db_session, 999) is False


# ==============================================================================
# ТЕСТЫ: ВИДЕО
# ==============================================================================
def test_create_video(db_session: Session):
    """Создание записи видео."""
    cat = crud.create_category(db_session, name="travel")
    video = crud.create_video(
        db_session, "/data/input/clip1.mp4", duration=10.5,
        resolution="1920x1080", category_id=cat.id,
    )
    assert video.id is not None
    assert video.file_path == "/data/input/clip1.mp4"
    assert video.duration == 10.5
    assert video.status == "uploaded"
    assert video.category_id == cat.id


def test_create_video_duplicate_raises(db_session: Session):
    """Дубликат пути вызывает ValueError."""
    crud.create_video(db_session, "/data/clip.mp4")
    with pytest.raises(ValueError):
        crud.create_video(db_session, "/data/clip.mp4")


def test_create_video_bad_category_raises(db_session: Session):
    """Несуществующая категория вызывает ValueError."""
    with pytest.raises(ValueError):
        crud.create_video(db_session, "/data/clip.mp4", category_id=999)


def test_list_videos_by_category(db_session: Session):
    """Фильтрация видео по категории."""
    cat_a = crud.create_category(db_session, name="a")
    cat_b = crud.create_category(db_session, name="b")
    crud.create_video(db_session, "/data/1.mp4", category_id=cat_a.id)
    crud.create_video(db_session, "/data/2.mp4", category_id=cat_a.id)
    crud.create_video(db_session, "/data/3.mp4", category_id=cat_b.id)

    vids_a = crud.list_videos(db_session, category_id=cat_a.id)
    assert len(vids_a) == 2
    assert crud.list_videos(db_session).__len__() == 3


def test_update_video_status(db_session: Session):
    """Обновление статуса видео."""
    video = crud.create_video(db_session, "/data/clip.mp4")
    updated = crud.update_video_status(db_session, video.id, status="processed")
    assert updated is not None
    assert updated.status == "processed"


def test_delete_video(db_session: Session):
    """Удаление записи видео."""
    video = crud.create_video(db_session, "/data/clip.mp4")
    assert crud.delete_video(db_session, video.id) is True
    assert crud.get_video(db_session, video.id) is None


def test_models_registered():
    """Модели корректно зарегистрированы в метаданных."""
    table_names = set(Base.metadata.tables.keys())
    assert "categories" in table_names
    assert "videos" in table_names
    assert "learning_patterns" in table_names
    assert "processing_history" in table_names
    assert "user_feedback" in table_names