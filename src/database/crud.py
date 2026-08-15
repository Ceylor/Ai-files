def update_video_status(
    db: Session, video_id: int, status: str,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Video]:
    """Обновляет статус (и, опционально, extra_metadata) видео."""
    video = get_video(db, video_id)
    if video is None:
        return None
    video.status = status
    if extra_metadata is not None:
        video.extra_metadata = extra_metadata
    db.commit()
    db.refresh(video)
    logger.info("Статус видео обновлён: id=%s -> %s", video_id, status)
    return video