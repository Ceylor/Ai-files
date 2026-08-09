# ==============================================================================
# ПАКЕТНЫЕ ФУНКЦИИ (для вызова из пайплайна)
# ==============================================================================
async def ingest_and_normalize_batch(
    input_files: List[Path],
    temp_dir: Path,
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Обрабатывает пакет видеофайлов с graceful fallback (пропуск битых файлов).

    Args:
        input_files: Список путей к видео.
        temp_dir: Папка для нормализованных файлов и аудио.
        config: Загруженный конфиг (или None — загрузится сам).

    Returns:
        Список результатов process_video по каждому файлу.
    """
    ingest = VideoIngest0(temp_dir, build_ingest_config(config))
    results: List[Dict[str, Any]] = []
    for video in input_files:
        try:
            result = await ingest.process_video(video)
            results.append(result)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Сбой обработки %s (пропускаю): %s", video.name, exc)
            results.append({
                "meta": {"filename": video.name, "success": False},
                "success": False,
            })
    return results


async def run_analyze_only(
    input_dir: Path,
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Dry-run анализ всех видео в папке (без обработки).

    Returns:
        JSON-отчёт по всем найденным видеофайлам.
    """
    video_files: List[Path] = []
    for ext in ("*.mp4", "*.mov", "*.avi", "*.mkv"):
        video_files.extend(input_dir.glob(ext))

    if not video_files:
        logger.warning("В папке %s не найдено видеофайлов.", input_dir)
        return []

    ingest = VideoIngest0(Path(input_dir), build_ingest_config(config))
    return await ingest.analyze_only(video_files)


# ==============================================================================
# CLI-ТОЧКА ВХОДА (для локального запуска и dry-run)
# ==============================================================================
async def _main(argv: Optional[List[str]] = None) -> int:
    """CLI: python -m src.modules.mod0_ingest [--analyze-only] <input_dir>"""
    import argparse

    parser = argparse.ArgumentParser(description="Стадия 0: ингестия и нормализация видео")
    parser.add_argument("input_dir", nargs="?", default="./data/input", help="Папка с исходными видео")
    parser.add_argument("--analyze-only", action="store_true", help="Только JSON-отчёт без обработки")
    parser.add_argument("--temp-dir", default="./data/temp", help="Папка для нормализованных файлов")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [ingest] %(message)s")

    input_path = Path(args.input_dir)
    if not input_path.exists():
        logger.error("Папка %s не существует.", input_path)
        return 1

    config = load_config()

    if args.analyze_only:
        report = await run_analyze_only(input_path, config)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    video_files: List[Path] = []
    for ext in ("*.mp4", "*.mov", "*.avi", "*.mkv"):
        video_files.extend(input_path.glob(ext))
    if not video_files:
        logger.error("Видеофайлы не найдены в %s", input_path)
        return 1

    results = await ingest_and_normalize_batch(video_files, Path(args.temp_dir), config)
    ok = sum(1 for r in results if r.get("success"))
    logger.info("Ингестия завершена: %s/%s файлов обработано успешно", ok, len(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))