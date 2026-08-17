@app.get("/api/batch/list")
async def api_batch_list(status: Optional[str] = None, db: Session = Depends(get_db)):
    """Возвращает список пакетных задач (опционально по статусу)."""
    batches = db_crud.list_batch_jobs(db, status=status)
    return {"tasks": [_batch_to_dict(b) for b in batches]}


async def run_batch_task(folder_id: int):
    """
    Фоновая задача пакетной обработки папки.

    Использует глобальный BatchProcessor (batch_processor), чтобы не создавать
    новый экземпляр на каждый запуск. Выполняется после ответа HTTP 200
    через BackgroundTasks.
    """
    try:
        logger.info("Старт пакетной обработки задачи #%s", folder_id)
        await batch_processor.process_folder(folder_id)
        logger.info("Пакетная обработка задачи #%s завершена", folder_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Сбой пакетной обработки задачи #%s", folder_id)
        await ws_manager.broadcast(f"❌ Сбой пакетной обработки #{folder_id}: {exc}")


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