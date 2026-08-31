"""
Загрузка исходников и запуск AI-монтажа (пайплайн).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Form, UploadFile, File
import aiofiles

from src.api.state import INPUT_DIR, OUTPUT_DIR, BASE_DIR, ws_manager
from src.utils.security import sanitize_filename

logger = logging.getLogger("api.pipeline")

router = APIRouter(prefix="/api", tags=["pipeline"])


@router.post("/upload_input")
async def upload_input(files: List[UploadFile] = File(...)):
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


@router.post("/start_pipeline")
async def start_pipeline(
    category: str = Form("default"),
    files: Optional[List[UploadFile]] = File(None),
):
    from src.utils.security import sanitize_category
    category = sanitize_category(category)
    if files:
        INPUT_DIR.mkdir(parents=True, exist_ok=True)
        for file in files:
            safe_name = sanitize_filename(file.filename)
            file_path = INPUT_DIR / safe_name
            async with aiofiles.open(file_path, "wb") as out_file:
                await out_file.write(await file.read())

    profile_path = BASE_DIR / "configs" / f"profile_{category}.json"
    if not profile_path.exists():
        await ws_manager.broadcast(f"⚠️  Профиль для '{category}' не найден. Использую базовые настройки.")
    else:
        await ws_manager.broadcast(f"📋 Загружен профиль стиля: {category}")

    await ws_manager.broadcast(f"🚀 Запуск AI-монтажа в стиле '{category}'...")
    asyncio.create_task(run_full_pipeline_task(category))
    return {"status": "started"}


async def run_full_pipeline_task(category: str):
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        profile_path = BASE_DIR / "configs" / f"profile_{category}.json"
        style_profile = None
        if profile_path.exists():
            async with aiofiles.open(profile_path, "r", encoding="utf-8") as f:
                style_profile = json.loads(await f.read())
        from src.core.pipeline import run_pipeline
        await run_pipeline(str(INPUT_DIR), style_profile=style_profile, category=category)
        await ws_manager.broadcast(f"🎉 ГОТОВО! Клипы сохранены в: {OUTPUT_DIR}")
    except Exception as e:
        await ws_manager.broadcast(f"❌ Ошибка пайплайна: {e}")
        import traceback
        traceback.print_exc()
