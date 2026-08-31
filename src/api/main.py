"""
FastAPI Backend для AI AutoClip Pro 2.0
Многослойный анализ контента, самообучение, категории, видео, монтаж, пакетная обработка.

Точка сборки приложения: здесь только инициализация, lifespan, CORS,
web-интерфейс, WebSocket-каналы и подключение роутеров.
"""
import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.state import limiter, ws_manager, batch_ws_manager, BASE_DIR, WEB_UI_DIR
from src.api.routers import categories, videos, analysis, learning, batch, pipeline, status
from src.database import init_db

logger = logging.getLogger("api.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения: инициализация БД при старте."""
    try:
        init_db()
        await ws_manager.broadcast("🗄️  База данных инициализирована")
    except Exception as e:
        await ws_manager.broadcast(f"⚠️  Ошибка инициализации БД: {e}")
        import traceback
        traceback.print_exc()
    yield


app = FastAPI(title="AI AutoClip Pro - Multi-Category", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware (настраивается через CORS_ORIGINS в .env).
_cors_origins_str = os.getenv("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_str.split(",") if o.strip()] if _cors_origins_str else []
if not _cors_origins:
    _cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- WEB-ИНТЕРФЕЙС И СТАТИКА ---

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return FileResponse(WEB_UI_DIR / "index.html")


try:
    app.mount("/static", StaticFiles(directory=WEB_UI_DIR), name="static")
except Exception:
    pass


# --- WEBSOCKET-КАНАЛЫ ---

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.websocket("/ws/batch/{task_id}")
async def websocket_batch_endpoint(websocket: WebSocket, task_id: int):
    """WebSocket для отслеживания прогресса конкретной batch-задачи."""
    await batch_ws_manager.connect(websocket, task_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        batch_ws_manager.disconnect(websocket, task_id)


# --- ПОДКЛЮЧЕНИЕ РОУТЕРОВ ---

app.include_router(categories.router)
app.include_router(videos.router)
app.include_router(analysis.router)
app.include_router(learning.router)
app.include_router(batch.router)
app.include_router(pipeline.router)
app.include_router(status.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
