"""
Эндпоинты самообучения, референсов, стиля и теггинга.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Form, HTTPException, UploadFile, File
import aiofiles

from src.api.state import REF_DIR, DATA_DIR, BASE_DIR, MAX_UPLOAD_SIZE
from src.api.state import learning_engine, ws_manager
from src.utils.security import sanitize_filename, sanitize_category
from src.utils.style_profiler import analyze_reference_clips
from src.utils.auto_tagger import analyze_music_library
from src.modules.mod7_learning.pattern_extractor import extract_pattern_async

logger = logging.getLogger("api.learning")

router = APIRouter(prefix="/api", tags=["learning"])


# --- САМООБУЧЕНИЕ НА ПРИМЕРАХ (модуль 7) ---

@router.post("/learning/train")
async def learning_train(category: str = Form("default")):
    category = sanitize_category(category)
    cat_dir = REF_DIR / category
    if not cat_dir.exists() or not any(cat_dir.iterdir()):
        raise HTTPException(status_code=404, detail=f"Папка категории '{category}' пуста или не найдена")

    await ws_manager.broadcast(f"🧠 Запуск самообучения категории '{category}'...")
    asyncio.create_task(run_learning_task(category))
    return {"status": "started", "category": category}


async def run_learning_task(category: str):
    try:
        cat_dir = REF_DIR / category
        await learning_engine.learn_from_references(cat_dir, category=category)
    except Exception as e:
        await ws_manager.broadcast(f"❌ Ошибка самообучения '{category}': {e}")
        import traceback
        traceback.print_exc()


@router.get("/learning/status")
async def learning_status():
    return learning_engine.stats()


@router.get("/learning/categories")
async def learning_categories():
    return {"categories": learning_engine.list_categories()}


@router.get("/learning/profile/{category}")
async def learning_profile(category: str):
    category = sanitize_category(category)
    profile = learning_engine.get_category_profile(category)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Для категории '{category}' нет обученных паттернов")
    return profile.serialize()


@router.get("/learning/find_similar/{category}")
async def learning_find_similar(category: str, k: int = 5):
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


@router.post("/learning/extract")
async def learning_extract(files: List[UploadFile] = File(...), category: str = Form("default")):
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

@router.post("/upload_references")
async def upload_references(
    files: List[UploadFile] = File(...),
    category: str = Form("default")
):
    category = sanitize_category(category)
    cat_dir = REF_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for file in files:
        safe_name = sanitize_filename(file.filename)
        if file.size and file.size > MAX_UPLOAD_SIZE:
            max_mb = MAX_UPLOAD_SIZE // (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"Файл '{safe_name}' слишком большой. Максимум: {max_mb} МБ",
            )
        file_path = cat_dir / safe_name
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
        saved.append(safe_name)

    await ws_manager.broadcast(f"✅ Загружено {len(saved)} файлов в категорию '{category}'")
    return {"status": "success", "count": len(saved), "files": saved}


# --- ОБУЧЕНИЕ ПО ССЫЛКАМ ---

@router.post("/train_links")
async def train_links(category: str = Form(...), links: str = Form(...)):
    category = sanitize_category(category)
    cat_dir = REF_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)

    link_list = [link.strip() for link in links.split('\n') if link.strip()]
    if not link_list:
        return {"status": "error", "message": "Список ссылок пуст"}

    await ws_manager.broadcast(f"📥 [Категория: {category}] Начинаю скачивание {len(link_list)} видео...")
    asyncio.create_task(_download_links_task(category, link_list))
    return {"status": "started", "count": len(link_list)}


async def _get_video_duration(url: str) -> float:
    """Запрашивает длительность видео через yt-dlp (без скачивания)."""
    try:
        cmd = ["yt-dlp", "--get-duration", "--no-download", url]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        duration_str = stdout.decode(errors="ignore").strip()
        if duration_str:
            parts = duration_str.split(":")
            if len(parts) == 3:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return float(parts[0]) * 60 + float(parts[1])
            else:
                return float(parts[0])
    except Exception:
        pass
    return 0.0


async def _download_links_task(category: str, link_list: List[str]):
    cat_dir = REF_DIR / category
    for i, link in enumerate(link_list, 1):
        await ws_manager.broadcast(f"    📥 Скачивание {i}/{len(link_list)}...")
        try:
            duration = await _get_video_duration(link)
            if duration > 0:
                timeout = max(3600, min(int(duration * 3), 14400))
                await ws_manager.broadcast(
                    f"    ⏱  Видео: ~{int(duration // 60)} мин, таймаут: {int(timeout // 60)} мин"
                )
            else:
                timeout = 7200

            cmd = [
                "yt-dlp",
                "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
                "--merge-output-format", "mp4",
                "--no-playlist",
                "-o", f"{cat_dir}/%(title).50s.%(ext)s",
                link
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            try:
                await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                process.kill()
                await ws_manager.broadcast(f"    ⏰ Видео {i}: таймаут скачивания")
                continue
            if process.returncode == 0:
                await ws_manager.broadcast(f"    ✅ Видео {i} скачано")
            else:
                await ws_manager.broadcast(f"    ⚠️  Видео {i}: ошибка")
        except Exception as e:
            await ws_manager.broadcast(f"    ❌ Ошибка скачивания {i}: {e}")
        await asyncio.sleep(1)
    await ws_manager.broadcast(f"🎉 Все ссылки для категории '{category}' обработаны!")


# --- АНАЛИЗ СТИЛЯ С АВТО-ОЧИСТКОЙ ---

@router.post("/analyze_style")
async def analyze_style(category: str = Form("default"), auto_cleanup: bool = Form(False)):
    category = sanitize_category(category)
    cat_dir = REF_DIR / category
    if not cat_dir.exists() or not any(cat_dir.iterdir()):
        return {"status": "error", "message": f"Папка категории '{category}' пуста."}

    await ws_manager.broadcast(f"🧠 Запуск анализа стиля для категории: {category}...")
    asyncio.create_task(run_style_profiler_task(category, auto_cleanup))
    return {"status": "started"}


async def run_style_profiler_task(category: str, auto_cleanup: bool = False):
    try:
        cat_dir = REF_DIR / category
        files_before = list(cat_dir.glob("*.mp4")) + list(cat_dir.glob("*.mov"))
        await ws_manager.broadcast(f"    Найдено {len(files_before)} видео для анализа")

        profile = await analyze_reference_clips(str(cat_dir))
        profile_path = BASE_DIR / "configs" / f"profile_{category}.json"
        async with aiofiles.open(profile_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(profile, indent=2, ensure_ascii=False))

        await ws_manager.broadcast(f"✅ Профиль стиля '{category}' сохранен!")

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

@router.post("/cleanup_references")
async def cleanup_references(category: str = Form(...), mode: str = Form("delete")):
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
                "ffmpeg", "-y", "-i", str(file),
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

@router.post("/tag_music")
async def tag_music():
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
    try:
        await analyze_music_library(music_dir)
        await ws_manager.broadcast("🎉 Теггинг музыкальной библиотеки завершён!")
    except Exception as e:
        await ws_manager.broadcast(f"❌ Ошибка теггинга: {e}")
        import traceback
        traceback.print_exc()
