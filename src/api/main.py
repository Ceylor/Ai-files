@app.post("/api/batch/process/{folder_id}")
async def api_batch_process(
    folder_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Запускает пакетную обработку папки в фоне.

    Задача добавляется в BackgroundTasks (внедряется через DI FastAPI),
    поэтому гарантированно выполняется после ответа HTTP 200.
    """
    logger.info("Запрос на запуск пакетной обработки задачи #%s", folder_id)
    batch = db_crud.get_batch_job(db, folder_id)
    if batch is None:
        logger.warning("Пакетная задача #%s не найдена", folder_id)
        raise HTTPException(status_code=404, detail="Пакетная задача не найдена")
    if batch.status in ("processing", "completed"):
        logger.warning(
            "Пакетная задача #%s уже в статусе '%s'", folder_id, batch.status
        )
        raise HTTPException(
            status_code=409, detail=f"Задача уже в статусе '{batch.status}'"
        )

    # Важно: используем background_tasks, внедрённый FastAPI, чтобы задача
    # выполнилась после ответа. Ранее создавался локальный объект, из-за чего
    # обработка фактически не стартовала.
    background_tasks.add_task(run_batch_task, folder_id)
    logger.info("Пакетная обработка задачи #%s поставлена в очередь", folder_id)
    return {
        "status": "started",
        "batch_id": folder_id,
        "message": "Пакетная обработка запущена в фоне",
    }


@app.post("/api/batch/upload_files")
async def api_batch_upload_files(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Загружает видеофайлы с ПК и регистрирует их как новую пакетную задачу.

    Файлы сохраняются в data/input, затем создаётся BatchJob со статусом
    'pending' и записи Video для каждого загруженного файла.
    """
    if not files:
        raise HTTPException(status_code=400, detail="Файлы не переданы")

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

    # Создаём пакетную задачу и регистрируем видео.
    batch = db_crud.create_batch_job(
        db, str(INPUT_DIR), status="pending", total_videos=len(saved_paths)
    )
    created = 0
    for file_path in saved_paths:
        try:
            db_crud.create_video(
                db,
                str(file_path),
                status="pending",
                batch_job_id=batch.id,
            )
            created += 1
        except ValueError:
            logger.warning("Видео уже существует, пропуск: %s", file_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось зарегистрировать %s: %s", file_path, exc)

    await ws_manager.broadcast(
        f"✅ Загружено {len(saved_paths)} видеофайлов с ПК, задача #{batch.id} создана"
    )
    return {
        "status": "created",
        "batch_id": batch.id,
        "folder_path": str(INPUT_DIR),
        "total_videos": len(saved_paths),
        "registered": created,
        "files": [p.name for p in saved_paths],
    }


@app.post("/api/batch/download_links")
async def api_batch_download_links(
    links: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Скачивает видео по ссылкам (YouTube, VK, RuTube и др.) через yt-dlp.

    Скачанные файлы сохраняются в data/downloads, затем регистрируются как
    новая пакетная задача (статус pending). Поддерживается массовая вставка
    ссылок — каждая с новой строки.
    """
    link_list = [link.strip() for link in links.split("\n") if link.strip()]
    if not link_list:
        return {"status": "error", "message": "Список ссылок пуст"}

    await ws_manager.broadcast(
        f"📥 Получено ссылок для скачивания: {len(link_list)}"
    )
    asyncio.create_task(_download_and_register_task(link_list))
    return {"status": "started", "count": len(link_list)}


async def _download_and_register_task(link_list: List[str]):
    """Скачивает видео по ссылкам и регистрирует их в новой пакетной задаче."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    downloaded: List[Path] = []
    for i, link in enumerate(link_list, 1):
        await ws_manager.broadcast(f"    📥 Скачивание {i}/{len(link_list)}...")
        try:
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
            await process.communicate()
            if process.returncode == 0:
                # Ищем последний скачанный mp4.
                mp4_files = sorted(DOWNLOAD_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
                if mp4_files:
                    latest = mp4_files[-1]
                    if latest not in downloaded:
                        downloaded.append(latest)
                await ws_manager.broadcast(f"    ✅ Видео {i} скачано")
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
            batch = db_crud.create_batch_job(
                db, str(DOWNLOAD_DIR), status="pending", total_videos=len(downloaded)
            )
            created = 0
            for file_path in downloaded:
                try:
                    db_crud.create_video(
                        db, str(file_path), status="pending", batch_job_id=batch.id
                    )
                    created += 1
                except ValueError:
                    logger.warning("Видео уже существует, пропуск: %s", file_path)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Не удалось зарегистрировать %s: %s", file_path, exc)
        await ws_manager.broadcast(
            f"🎉 Скачано {created} видео по ссылкам, задача #{batch.id} создана"
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Не удалось зарегистрировать скачанные видео")
        await ws_manager.broadcast(f"❌ Ошибка регистрации скачанных видео: {exc}")