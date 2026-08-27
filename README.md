# 🎬 AI AutoClip Pro 2.0

Система ИИ-генерации клипов с многослойным анализом контента, самообучением
и пакетной обработкой.

## ✨ Возможности

- **Многослойный анализ** — эмоции, объекты, движение, «золотые моменты», CLIP-эмбеддинги.
- **Самообучение** — извлечение и накопление паттернов успеха из референсных клипов.
- **Массовая обработка** — асинхронная пакетная обработка папок с видео и композиция клипов.
- **Веб-интерфейс** — современный интерфейс на Next.js + Tailwind CSS (тёмная тема).
- **База данных** — SQLAlchemy 2.0 + Alembic (SQLite по умолчанию).

## 🚀 Быстрый запуск

### Автоматическое развёртывание (рекомендуется)

**Windows:** дважды кликните на **`deploy.bat`** — проверит Python, Node, FFmpeg, установит зависимости, применит миграции и запустит систему.

**Linux/macOS:** `bash deploy.sh`

### Ручная установка

1. **Зависимости:** `install_deps.bat` (Windows) или `pip install -r requirements.txt && cd frontend && npm install`
2. **Запуск:** `start_all.bat` (Windows) или запустите бэкенд и фронтенд отдельно

> Требуется: **Python 3.9+**, **Node.js 18+**, **FFmpeg** в PATH.

### Запуск системы

Дважды кликните на **`start_all.bat`**. Скрипт:

1. Активирует виртуальное окружение;
2. Применяет миграции базы данных (`alembic upgrade head`);
3. Запускает бэкенд (FastAPI) на `http://127.0.0.1:8000`;
4. Через 3 секунды запускает фронтенд (Next.js) на `http://localhost:3000`;
5. Автоматически открывает браузер с интерфейсом.

> После двойного клика по `start_all.bat` откроются два окна (бэкенд и фронтенд)
> с логами и браузер с интерфейсом — можно сразу пользоваться.

### Остановка

Закройте окна «AI AutoClip — Бэкенд» и «AI AutoClip — Фронтенд».

## 🧭 Структура

```
start_all.bat      — запуск системы (бэкенд + фронтенд + браузер)
install_deps.bat   — установка всех зависимостей (первый запуск)
frontend/          — веб-интерфейс (Next.js)
src/               — бэкенд (FastAPI, модули)
src/api/main.py    — точка входа бэкенда
migrations/        — Alembic-миграции
tests/             — тесты (pytest)
```

## 🛠 Ручной запуск (для разработчиков)

### Бэкенд

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

### Фронтенд

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Откройте http://localhost:3000.

## 🧪 Тесты

```bash
python -m pytest -v
```

## 🏥 Проверка здоровья

```bash
python health_check.py
```

Проверяет: компиляцию Python, импорт main.py, наличие API-эндпоинтов, целостность фронтенда.

## ❓ FAQ

**Q: FFmpeg не найден?**
A: Установите FFmpeg и добавьте в PATH. Windows: `winget install Gyan.FFmpeg`

**Q: Порт 8000 занят?**
A: Остановите другой процесс или измените порт в `start_all.bat`

**Q: Ошибка 500 на API?**
A: Проверьте логи в `logs/backend.log`. Убедитесь, что миграции применены (`alembic upgrade head`).

**Q: Фронтенд не подключается к бэкенду?**
A: Убедитесь, что бэкенд запущен на порту 8000. Проверьте `frontend/next.config.js` (rewrites).

## 📚 Документация

- [frontend/README.md](frontend/README.md) — интерфейс.
- `docs/USER_GUIDE.md` — руководство пользователя.
- `docs/ARCHITECTURE.md` — архитектура системы.
- `CHANGELOG.md` — история изменений.