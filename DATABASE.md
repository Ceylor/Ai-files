# 🗄️ База данных AI AutoClip Pro 2.0

SQLAlchemy 2.0 + Alembic. Хранит метаданные видео, категории, паттерны
самообучения, историю обработки и пользовательские оценки.

---

## 📁 Структура

```
src/database/
├── __init__.py   # публичный экспорт пакета
├── base.py       # DeclarativeBase + TimestampMixin
├── models.py     # 5 SQLAlchemy-моделей (Mapped / mapped_column)
├── session.py    # engine, SessionLocal, get_db, session_scope, init_db
└── crud.py       # базовые CRUD-операции (categories, videos)

migrations/
├── alembic.ini
├── env.py
├── script.py.mako
└── versions/
    └── 0001_initial.py   # первая миграция (5 таблиц)
```

---

## 🗃 Таблицы

| Таблица | Назначение | Ключевые поля |
|---------|-----------|----------------|
| `categories` | категории клипов (иерархия) | name (unique), description, parent_id |
| `videos` | видеофайлы | file_path (unique), duration, resolution, category_id, status, metadata (JSON) |
| `learning_patterns` | паттерны самообучения | vector (JSON), structure, tempo, transitions, color_profile, music_profile |
| `processing_history` | история запусков монтажа | input_video_ids, output_video_path, used_pattern_ids, parameters, status, started/finished_at |
| `user_feedback` | оценки пользователя | video_id (FK), rating (1–5), comment |

---

## ⚙️ Конфигурация

URL БД задаётся через переменную окружения `DATABASE_URL`:

```bash
# SQLite (по умолчанию, не требует сервера):
export DATABASE_URL="sqlite:///./data/app.db"

# PostgreSQL:
export DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/aiclip"
```

Если переменная не задана — используется `sqlite:///./data/app.db`.

---

## 🚀 Запуск миграций (Alembic)

Установите зависимости:
```bash
pip install sqlalchemy alembic
```

Примените миграции:
```bash
# Применить все миграции
alembic upgrade head

# Посмотреть статус
alembic current

# Откатиться на одну версию назад
alembic downgrade -1
```

### Авто-генерация новой миграции (при изменении моделей)
```bash
alembic revision --autogenerate -m "add new column"
alembic upgrade head
```

> **Важно для SQLite:** в `env.py` включён `render_as_batch=True` —
> это требуется для ALTER TABLE в SQLite.

---

## 🔌 Интеграция в FastAPI

База инициализируется автоматически при старте приложения через `lifespan`:

```python
# src/api/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()          # создание таблиц (если их ещё нет)
    yield
```

### Зависимость сессии (для эндпоинтов)
```python
from fastapi import Depends
from sqlalchemy.orm import Session
from src.database.session import get_db
from src.database import crud

@app.get("/api/categories")
async def list_categories(db: Session = Depends(get_db)):
    return crud.list_categories(db)
```

### Использование вне FastAPI (фоновые задачи)
```python
from src.database.session import session_scope
from src.database import crud

with session_scope() as db:
    cat = crud.create_category(db, name="travel")
```

---

## 🌐 REST API (CRUD)

### Категории
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/categories` | создать категорию (form: name, description?, parent_id?) |
| GET | `/api/categories` | список (query: parent_id?) |
| GET | `/api/categories/{id}` | категория по id |
| PUT | `/api/categories/{id}` | обновить (form: name?, description?, parent_id?) |
| DELETE | `/api/categories/{id}` | удалить |

### Видео
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/videos` | создать запись видео (form: file_path, duration?, resolution?, category_id?, status?) |
| GET | `/api/videos` | список (query: category_id?, status?) |
| GET | `/api/videos/{id}` | видео по id |
| PATCH | `/api/videos/{id}/status` | обновить статус (form: status) |
| DELETE | `/api/videos/{id}` | удалить |

---

## 🧪 Тесты

```bash
python -m pytest tests/test_database.py -v
```

Проверяют CRUD категорий/видео, иерархию, дубликаты, фильтрацию
и целостность моделей на изолированной временной SQLite-БД.

---

## 🧠 Связь с самообучением

При обучении (`POST /api/learning/train`) паттерны сохраняются **дважды**:
1. В векторное хранилище (для быстрого поиска по сходству).
2. В таблицу `learning_patterns` (для аудита и аналитики) через
   `LearningEngine.save_patterns_to_db()`.

Это позволяет восстанавливать историю обучения и дообучаться
на основе пользовательских оценок (`user_feedback`).