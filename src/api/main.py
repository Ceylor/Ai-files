"""
FastAPI Backend для AI AutoClip Pro
Версия с категориями, ссылками и авто-очисткой памяти
"""
import json
import asyncio
from pathlib import Path
from typing import List, Optional, Optional
from fastapi import FastAPI, WebSocket, UploadFile, File, WebSocketDisconnect, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import aiofiles

from src.core.pipeline import run_pipeline
from src.utils.logger import ws_manager
from src.utils.style_profiler import analyze_reference_clips
from src.utils.auto_tagger import analyze_music_library
from src.utils.security import sanitize_filename, sanitize_category
from src.modules.mod7_learning.learner import LearningEngine
from src.modules.mod7_learning.pattern_extractor import extract_pattern_async

app = FastAPI(title="AI AutoClip Pro - Multi-Category")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
WEB_UI_DIR = BASE_DIR / "web_ui"
DATA_DIR = BASE_DIR / "data"
REF_DIR = DATA_DIR / "reference_clips"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
LEARNING_STORE_DIR = DATA_DIR / "learning_store"

# Движок самообучения (непрерывное накопление паттернов).
learning_engine = LearningEngine(LEARNING_STORE_DIR)

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return FileResponse(WEB_UI_DIR / "index.html")

try:
    app.mount("/static", StaticFiles(directory=WEB_UI_DIR), name="static")
except Exception:
    pass

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

# --- САМООБУЧЕНИЕ НА ПРИМЕРАХ (модуль 7) ---

@app.post("/api/learning/train")
async def learning_train(category: str = Form("default")):
    """
    Запускает самообучение по референсным клипам категории.
    Анализирует готовые клипы, извлекает "паттерны успеха" и сохраняет в векторное хранилище.
    """
    category = sanitize_category(category)
    cat_dir = REF_DIR / category
    if not cat_dir.exists() or not any(cat_dir.iterdir()):
        raise HTTPException(status_code=404, detail=f"Папка категории '{category}' пуста или не найдена")

    await ws_manager.broadcast(f"🧠 Запуск самообучения категории '{category}'...")
    asyncio.create_task(run_learning_task(category))
    return {"status": "started", "category": category}

async def run_learning_task(category: str):
    """Фоновая задача самообучения по категории."""
    try:
        cat_dir = REF_DIR / category
        await learning_engine.learn_from_references(cat_dir, category=category)
    except Exception as e:
        await ws_manager.broadcast(f"❌ Ошибка самообучения '{category}': {e}")
        import traceback
        traceback.print_exc()

@app.get("/api/learning/status")
async def learning_status():
    """Статус движка самообучения: бэкенд, число паттернов, категории."""
    return learning_engine.stats()

@app.get("/api/learning/categories")
async def learning_categories():
    """Список категорий с обученными паттернами."""
    return {"categories": learning_engine.list_categories()}

@app.get("/api/learning/profile/{category}")
async def learning_profile(category: str):
    """
    Агрегированный профиль стиля категории (усреднённый "паттерн успеха").
    Применяется к новым видео для монтажа в стиле категории.
    """
    category = sanitize_category(category)
    profile = learning_engine.get_category_profile(category)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Для категории '{category}' нет обученных паттернов")
    return profile.serialize()

@app.get("/api/learning/find_similar/{category}")
async def learning_find_similar(category: str, k: int = 5):
    """
    Возвращает k ближайших "паттернов успеха" в категории.
    Используется для выбора наиболее подходящего стиля под новое видео.
    """
    category = sanitize_category(category)
    profile = learning_engine.get_category_profile(category)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Для категории '{category}' нет обученных паттернов")
    hits = learning_engine.find_similar(profile, category=category, k=k)
    return {
        "category": category,
        "hits": [
            {"score": round(h.score, 4), "source_path": h.metadata.get("source_path", "")}
            for h in hits
        ],
    }

@app.post("/api/learning/extract")
async def learning_extract(files: List[UploadFile] = File(...), category: str = Form("default")):
    """Извлекает паттерн из загруженного видео без сохранения в хранилище."""
    category = sanitize_category(category)
    patterns = []
    tmp_dir = DATA_DIR / "temp" / "learning_extract"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    for file in files:
        safe_name = sanitize_filename(file.filename)
        file_path = tmp_dir / safe_name
        async with aiofiles.open(file_path, "wb") as out_file:
            await out_file.write(await file.read())
        try:
            pattern = await extract_pattern_async(file_path, category=category)
            patterns.append(pattern.serialize())
        except Exception as e:
            await ws_manager.broadcast(f"⚠️  Ошибка извлечения паттерна {safe_name}: {e}")
        finally:
            if file_path.exists():
                file_path.unlink()
    return {"status": "success", "category": category, "patterns": patterns}

# --- ЗАГРУЗКА РЕФЕРЕНСОВ ПО КАТЕГОРИЯМ ---

@app.post("/api/upload_references")
async def upload_references(
    files: List[UploadFile] = File(...),
    category: str = Form("default")
):
    """Загрузка референсных видео в папку категории"""
    category = sanitize_category(category)
    cat_dir = REF_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    
    saved = []
    for file in files:
        safe_name = sanitize_filename(file.filename)
        file_path = cat_dir / safe_name
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
        saved.append(safe_name)
    
    await ws_manager.broadcast(f"✅ Загружено {len(saved)} файлов в категорию '{category}'")
    return {"status": "success", "count": len(saved), "files": saved}

# --- ОБУЧЕНИЕ ПО ССЫЛКАМ ---

@app.post("/api/train_links")
async def train_links(
    category: str = Form(...),
    links: str = Form(...)
):
    """Скачивает видео по ссылкам в папку категории (720p для экономии места)"""
    category = sanitize_category(category)
    cat_dir = REF_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    
    link_list = [link.strip() for link in links.split('\n') if link.strip()]
    if not link_list:
        return {"status": "error", "message": "Список ссылок пуст"}

    await ws_manager.broadcast(f"📥 [Категория: {category}] Начинаю скачивание {len(link_list)} видео...")
    
    # Запускаем в фоне, чтобы не блокировать UI
    asyncio.create_task(_download_links_task(category, link_list))
    
    return {"status": "started", "count": len(link_list)}

async def _download_links_task(category: str, link_list: List[str]):
    """Фоновая задача скачивания ссылок"""
    cat_dir = REF_DIR / category
    
    for i, link in enumerate(link_list, 1):
        await ws_manager.broadcast(f"    📥 Скачивание {i}/{len(link_list)}...")
        try:
            # Скачиваем в 720p для экономии места (для анализа стиля этого достаточно)
            cmd = [
                "yt-dlp",
                "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
                "--merge-output-format", "mp4",
                "--no-playlist",
                "-o", f"{cat_dir}/%(title).50s.%(ext)s",
                link
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                await ws_manager.broadcast(f"    ✅ Видео {i} скачано")
            else:
                await ws_manager.broadcast(f"    ⚠️  Видео {i}: ошибка ({stderr.decode()[:100]})")
        except Exception as e:
            await ws_manager.broadcast(f"    ❌ Ошибка скачивания {i}: {e}")
        
        # Небольшая пауза между скачиваниями
        await asyncio.sleep(1)
    
    await ws_manager.broadcast(f"🎉 Все ссылки для категории '{category}' обработаны!")

# --- АНАЛИЗ СТИЛЯ С АВТО-ОЧИСТКОЙ ---

@app.post("/api/analyze_style")
async def analyze_style(
    category: str = Form("default"),
    auto_cleanup: bool = Form(False)
):
    """Анализ стиля категории с опциональным удалением оригиналов после"""
    category = sanitize_category(category)
    cat_dir = REF_DIR / category
    if not cat_dir.exists() or not any(cat_dir.iterdir()):
        return {"status": "error", "message": f"Папка категории '{category}' пуста."}
    
    await ws_manager.broadcast(f"🧠 Запуск анализа стиля для категории: {category}...")
    asyncio.create_task(run_style_profiler_task(category, auto_cleanup))
    return {"status": "started"}

async def run_style_profiler_task(category: str, auto_cleanup: bool = False):
    """Фоновая задача анализа + опциональная очистка"""
    try:
        cat_dir = REF_DIR / category
        files_before = list(cat_dir.glob("*.mp4")) + list(cat_dir.glob("*.mov"))
        await ws_manager.broadcast(f"    Найдено {len(files_before)} видео для анализа")
        
        profile = await analyze_reference_clips(str(cat_dir))
        
        # Сохраняем профиль для категории
        profile_path = BASE_DIR / "configs" / f"profile_{category}.json"
        async with aiofiles.open(profile_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(profile, indent=2, ensure_ascii=False))
        
        await ws_manager.broadcast(f"✅ Профиль стиля '{category}' сохранен!")
        
        # АВТО-ОЧИСТКА если включена
        if auto_cleanup and files_before:
            await ws_manager.broadcast(f"🧹 Авто-очистка: удаляю {len(files_before)} оригиналов...")
            for file in files_before:
                file.unlink()
            await ws_manager.broadcast(f"   🗑️  Освобождено место. Папка '{category}' очищена.")
        
    except Exception as e:
        await ws_manager.broadcast(f"❌ Ошибка анализа: {e}")
        import traceback
        traceback.print_exc()

# --- РУЧНАЯ ОЧИСТКА ПАМЯТИ ---

@app.post("/api/cleanup_references")
async def cleanup_references(
    category: str = Form(...),
    mode: str = Form("delete")
):
    """Ручная очистка: delete (удалить) или compress (сжать до 360p)"""
    category = sanitize_category(category)
    cat_dir = REF_DIR / category
    
    if not cat_dir.exists():
        return {"status": "error", "message": f"Папка '{category}' не найдена"}
    
    files = list(cat_dir.glob("*.mp4")) + list(cat_dir.glob("*.mov"))
    if not files:
        return {"status": "error", "message": "Папка пуста"}
    
    await ws_manager.broadcast(f" Очистка '{category}': {len(files)} файлов, режим '{mode}'...")
    asyncio.create_task(_cleanup_task(cat_dir, files, mode))
    
    return {"status": "started", "count": len(files)}

async def _cleanup_task(cat_dir: Path, files: List[Path], mode: str):
    """Фоновая задача очистки"""
    if mode == "delete":
        for file in files:
            file.unlink()
            await ws_manager.broadcast(f"   🗑️  Удален: {file.name}")
        await ws_manager.broadcast(f"✅ Все файлы удалены!")
    
    elif mode == "compress":
        for i, file in enumerate(files, 1):
            await ws_manager.broadcast(f"   🗜️  Сжатие {i}/{len(files)}: {file.name}")
            
            temp_file = file.with_suffix(".temp.mp4")
            cmd = [
                "ffmpeg", "-y",
                "-i", str(file),
                "-vf", "scale=-1:360",
                "-c:v", "libx264", "-preset", "fast", "-crf", "28",
                "-c:a", "aac", "-b:a", "32k",
                str(temp_file)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0 and temp_file.exists():
                original_size = file.stat().st_size
                compressed_size = temp_file.stat().st_size
                saved_mb = (original_size - compressed_size) / 1024 / 1024
                
                file.unlink()
                temp_file.rename(file)
                await ws_manager.broadcast(f"      ✅ Сжато (освобождено {saved_mb:.1f} MB)")
            else:
                if temp_file.exists():
                    temp_file.unlink()
                await ws_manager.broadcast(f"       Ошибка сжатия: {file.name}")
        
        await ws_manager.broadcast(f"✅ Все файлы сжаты до 360p!")

# --- ТЕГГИРОВКА МУЗЫКАЛЬНОЙ БИБЛИОТЕКИ ---

@app.post("/api/tag_music")
async def tag_music():
    """Запускает анализ музыкальной библиотеки и создание JSON-метаданных"""
    MUSIC_DIR = DATA_DIR / "music_library"
    if not MUSIC_DIR.exists():
        MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    
    mp3_files = list(MUSIC_DIR.glob("*.mp3"))
    if not mp3_files:
        return {"status": "error", "message": "Музыкальная библиотека пуста"}
    
    await ws_manager.broadcast(f"🎵 Запуск теггинга музыкальной библиотеки ({len(mp3_files)} треков)...")
    asyncio.create_task(_tag_music_task(str(MUSIC_DIR)))
    return {"status": "started", "count": len(mp3_files)}

async def _tag_music_task(music_dir: str):
    """Фоновая задача теггинга музыки"""
    try:
        await analyze_music_library(music_dir)
        await ws_manager.broadcast("🎉 Теггинг музыкальной библиотеки завершён!")
    except Exception as e:
        await ws_manager.broadcast(f"❌ Ошибка теггинга: {e}")
        import traceback
        traceback.print_exc()

# --- ЗАГРУЗКА ИСХОДНИКОВ ДЛЯ МОНТАЖА ---

@app.post("/api/upload_input")
async def upload_input(files: List[UploadFile] = File(...)):
    """Загрузка исходных видео для монтажа"""
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    saved = []
    for file in files:
        safe_name = sanitize_filename(file.filename)
        file_path = INPUT_DIR / safe_name
        async with aiofiles.open(file_path, "wb") as out_file:
            await out_file.write(await file.read())
        saved.append(safe_name)
    
    await ws_manager.broadcast(f"✅ Загружено {len(saved)} исходных клипов")
    return {"status": "success", "count": len(saved)}

# --- ЗАПУСК ПИПАЙЛА С КАТЕГОРИЕЙ ---

@app.post("/api/start_pipeline")
async def start_pipeline(
    category: str = Form("default"),
    files: Optional[List[UploadFile]] = File(None)
):
    """Запуск AI-монтажа с применением стиля категории"""
    category = sanitize_category(category)
    if files:
        INPUT_DIR.mkdir(parents=True, exist_ok=True)
        for file in files:
            safe_name = sanitize_filename(file.filename)
            file_path = INPUT_DIR / safe_name
            async with aiofiles.open(file_path, "wb") as out_file:
                await out_file.write(await file.read())
    
    # Проверяем наличие профиля
    profile_path = BASE_DIR / "configs" / f"profile_{category}.json"
    if not profile_path.exists():
        await ws_manager.broadcast(f"⚠️  Профиль для '{category}' не найден. Использую базовые настройки.")
    else:
        await ws_manager.broadcast(f"📋 Загружен профиль стиля: {category}")
    
    await ws_manager.broadcast(f"🚀 Запуск AI-монтажа в стиле '{category}'...")
    asyncio.create_task(run_full_pipeline_task(category))
    return {"status": "started"}

async def run_full_pipeline_task(category: str):
    """Фоновая задача полного пайплайна"""
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Загружаем профиль стиля категории (если есть)
        profile_path = BASE_DIR / "configs" / f"profile_{category}.json"
        style_profile = None
        if profile_path.exists():
            async with aiofiles.open(profile_path, "r", encoding="utf-8") as f:
                style_profile = json.loads(await f.read())

        await run_pipeline(str(INPUT_DIR), style_profile=style_profile, category=category)
        await ws_manager.broadcast(f"🎉 ГОТОВО! Клипы сохранены в: {OUTPUT_DIR}")

    except Exception as e:
        await ws_manager.broadcast(f"❌ Ошибка пайплайна: {e}")
        import traceback
        traceback.print_exc()

# --- СТАТУС ---

@app.get("/api/status")
async def get_status():
    return {
        "status": "running",
        "version": "2.0",
        "categories": [d.name for d in REF_DIR.iterdir() if d.is_dir()] if REF_DIR.exists() else [],
        "learning": learning_engine.stats(),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)