"""
Пакетная обработка видео (модуль 9).
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, UploadFile, File
from slowapi import Limiter
from sqlalchemy.orm import Session
import aiofiles

from src.api.state import (
    INPUT_DIR,
    DOWNLOAD_DIR,
    ws_manager,
    limiter,
)

from src.database.session import get_db, session_scope
from src.database import crud as db_crud

logger = logging.getLogger("api.batch")

router = APIRouter(prefix="/api/batch", tags=["batch"])


def _batch_to_dict(b) -> dict:
    return {
        "id": b.id,
        "folder_path": b.folder_path,
        "status": b.status,
        "total_videos": b.total_videos,
        "processed_videos": b.processed_videos,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "finished_at": b.finished_at.isoformat() if b.finished_at else None,
    }


@router.post("/upload_folder")
@limiter.limit("5/minute")
async def api_batch_upload_folder(
    request: Request,
    folder_path: str = Form(...),
    db: Session = Depends(get_db),
):
    """Сканирует папку с видео, создаёт пакетную задачу (BatchJob)."""
    folder = Path(folder_path)
    if not folder.is_dir():
        raise HTTPException(status_code=404, detail=f"Папка не найдена: {folder_path}")

    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
    files = sorted([p for p in folder.iterdir() if p.suffix.lower() in video_exts])
    if not files:
        raise HTTPException(status_code=409, detail="В папке нет видеофайлов")

    batch = db_crud.create_batch_job(db, str(folder), status="pending", total_videos=len(files))
    created = []
    for file in files:
        try:
            v = db_crud.create_video(
                db,
                str(file),
                status="pending",
                batch_job_id=batch.id,
            )
            created.append({"id": v.id, "file_path": v.file_path})
        except ValueError:
            logger.warning("Видео уже существует, пропуск: %s", file)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось зарегистрировать %s: %s", file, exc)

    db_crud.update_batch_job_status(db, batch.id, status="pending")
    return {
        "status": "created",
        "batch_id": batch.id,
        "folder_path": str(folder),
        "total_videos": len(files),
        "registered": len(created),
    }


@router.get("/list")
async def api_batch_list(status: Optional[str] = None, db: Session = Depends(get_db)):
    batches = db_crud.list_batch_jobs(db, status=status)
    return {"tasks": [_batch_to_dict(b) for b in batches]}


async def run_batch_task(folder_id: int, settings: dict | None = None) -> None:
    """Фоновая задача пакетной обработки."""
    try:
        from src.api.state import batch_processor
        await batch_processor.process_folder(folder_id, settings=settings)
    except Exception as exc:
        logger.exception("Ошибка пакетной обработки задачи %s", folder_id)
        await ws_manager.broadcast(f"❌ Ошибка пакетной обработки #{folder_id}: {exc}")


@router.post("/process/{folder_id}")
async def api_batch_process(
    folder_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    max_clips_per_video: int = Form(5),
    fast_mode: bool = Form(False),
    performance_mode: str = Form("normal"),
):
    """Запускает пакетную обработку папки в фоне."""
    logger.info("Запрос на запуск пакетной обработки задачи #%s", folder_id)
    batch = db_crud.get_batch_job(db, folder_id)
    if batch is None:
        logger.warning("Пакетная задача #%s не найдена", folder_id)
        raise HTTPException(status_code=404, detail="Пакетная задача не найдена")
    if batch.status in ("processing", "completed"):
        logger.warning("Пакетная задача #%s уже в статусе '%s'", folder_id, batch.status)
        raise HTTPException(status_code=409, detail=f"Задача уже в статусе '{batch.status}'")

    from src.core.config_loader import load_performance_config
    performance = load_performance_config(performance_mode)

    settings = {
        "max_clips_per_video": max_clips_per_video,
        "fast_mode": fast_mode,
        "performance_mode": performance_mode,
        "performance": performance,
    }
    background_tasks.add_task(run_batch_task, folder_id, settings)
    logger.info("Пакетная обработка задачи #%s поставлена в очередь (performance=%s)", folder_id, performance_mode)
    return {
        "status": "started",
        "batch_id": folder_id,
        "message": "Пакетная обработка запущена в фоне",
    }


@router.post("/upload_files")
@limiter.limit("5/minute")
async def api_batch_upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Загружает видеофайлы с ПК и регистрирует их как новую пакетную задачу."""
    if not files:
        raise HTTPException(status_code=400, detail="Файлы не переданы")

    from src.utils.security import sanitize_filename
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
    saved_paths: List[Path] = []
    for file in files:
        safe_name = sanitize_filename(file.filename or f"upload_{len(saved_paths)}")
        if not Path(safe_name).suffix or Path(safe_name).suffix.lower() not in video_exts:
            logger.warning("Пропущен файл с неподдерживаемым расширением: %s", safe_name)
            continue
        file_path = INPUT_DIR / safe_name
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            if not content:
                logger.warning("Пустой файл, пропуск: %s", safe_name)
                continue
            await out_file.write(content)
        saved_paths.append(file_path)

    if not saved_paths:
        raise HTTPException(status_code=409, detail="Не удалось загрузить ни одного видеофайла")

    batch = db_crud.create_batch_job(db, str(INPUT_DIR), status="pending", total_videos=len(saved_paths))
    created = 0
    for file_path in saved_paths:
        try:
            db_crud.create_video(db, str(file_path), status="pending", batch_job_id=batch.id)
            created += 1
        except ValueError:
            logger.warning("Видео уже существует, пропуск: %s", file_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось зарегистрировать %s: %s", file_path, exc)

    await ws_manager.broadcast(f"✅ Загружено {len(saved_paths)} видеофайлов с ПК, задача #{batch.id} создана")
    return {
        "status": "created",
        "batch_id": batch.id,
        "folder_path": str(INPUT_DIR),
        "total_videos": len(saved_paths),
        "registered": created,
        "files": [p.name for p in saved_paths],
    }


@router.post("/download_links")
@limiter.limit("5/minute")
async def api_batch_download_links(
    request: Request,
    links: str = Form(...),
    db: Session = Depends(get_db),
):
    """Скачивает видео по ссылкам (YouTube, VK, RuTube и др.) через yt-dlp."""
    link_list = [link.strip() for link in links.split("\n") if link.strip()]
    if not link_list:
        return {"status": "error", "message": "Список ссылок пуст"}

    await ws_manager.broadcast(f"📥 Получено ссылок для скачивания: {len(link_list)}")
    asyncio.create_task(_download_and_register_task(link_list))
    return {"status": "started", "count": len(link_list)}


async def _get_video_duration(url: str) -> float:
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


async def _download_and_register_task(link_list: List[str]):
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    downloaded: List[Path] = []
    for i, link in enumerate(link_list, 1):
        await ws_manager.broadcast(f"    📥 Скачивание {i}/{len(link_list)}...")
        try:
            duration = await _get_video_duration(link)
            if duration > 0:
                timeout = max(3600, min(int(duration * 3), 14400))
                dur_min = int(duration // 60)
                tout_min = int(timeout // 60)
                await ws_manager.broadcast(f"    ⏱  Видео: ~{dur_min} мин, таймаут: {tout_min} мин")
            else:
                timeout = 7200
                await ws_manager.broadcast(f"    ⏱  Длительность неизвестна, таймаут: 120 мин")

            cmd = [
                "yt-dlp",
                "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
                "--merge-output-format", "mp4",
                "--no-playlist",
                "--restrict-filenames",
                "-o", f"{DOWNLOAD_DIR}/%(title).50s.%(ext)s",
                link,
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            try:
                await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                process.kill()
                await ws_manager.broadcast(f"    ⏰ Видео {i}: таймаут скачивания ({timeout}с)")
                continue
            if process.returncode == 0:
                mp4_files = sorted(DOWNLOAD_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
                if mp4_files:
                    latest = mp4_files[-1]
                    file_size = latest.stat().st_size
                    if file_size == 0:
                        await ws_manager.broadcast(f"    ❌ Видео {i}: файл повреждён (0 байт), пропуск")
                        latest.unlink(missing_ok=True)
                    elif latest not in downloaded:
                        downloaded.append(latest)
                        size_mb = file_size / (1024 * 1024)
                        await ws_manager.broadcast(f"    ✅ Видео {i} скачано ({size_mb:.1f} МБ)")
                    else:
                        await ws_manager.broadcast(f"    ✅ Видео {i} скачано")
                else:
                    await ws_manager.broadcast(f"    ⚠️  Видео {i}: mp4 файл не найден")
            else:
                await ws_manager.broadcast(f"    ⚠️  Видео {i}: ошибка скачивания")
        except Exception as exc:  # noqa: BLE001
            await ws_manager.broadcast(f"    ❌ Ошибка скачивания {i}: {exc}")
            logger.exception("Ошибка скачивания ссылки %s", link)
        await asyncio.sleep(1)

    if not downloaded:
        await ws_manager.broadcast("❌ Не удалось скачать ни одного видео по ссылкам")
        return

    try:
        with session_scope() as db:
            batch = db_crud.create_batch_job(db, str(DOWNLOAD_DIR), status="pending", total_videos=len(downloaded))
            created = 0
            for file_path in downloaded:
                try:
                    db_crud.create_video(db, str(file_path), status="pending", batch_job_id=batch.id)
                    created += 1
                except ValueError:
                    logger.warning("Видео уже существует, пропуск: %s", file_path)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Не удалось зарегистрировать %s: %s", file_path, exc)
        await ws_manager.broadcast(f"🎉 Скачано {created} видео по ссылкам, задача #{batch.id} создана")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Не удалось зарегистрировать скачанные видео")
        await ws_manager.broadcast(f"❌ Ошибка регистрации скачанных видео: {exc}")


@router.get("/status/{folder_id}")
async def api_batch_status(folder_id: int, db: Session = Depends(get_db)):
    batch = db_crud.get_batch_job(db, folder_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Пакетная задача не найдена")
    return _batch_to_dict(batch)


@router.get("/results/{folder_id}")
async def api_batch_results(folder_id: int, db: Session = Depends(get_db)):
    """Возвращает видео и их статусы по пакетной задаче."""
    batch = db_crud.get_batch_job(db, folder_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Пакетная задача не найдена")
    videos = db_crud.list_videos(db, batch_job_id=folder_id)
    return {
        "batch_id": folder_id,
        "status": batch.status,
        "videos": [
            {"id": v.id, "file_path": v.file_path, "status": v.status}
            for v in videos
        ],
    }
