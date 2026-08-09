"""
Тесты для модуля 0 (ингестия и нормализация видео).

Используют синтетические мини-видео, генерируемые через FFmpeg (testsrc + sine),
чтобы не зависеть от реальных файлов.

Запуск:
    python -m pytest tests/test_mod0_ingest.py -v

Требования: ffmpeg/ffprobe в PATH, pytest.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List

import pytest

from src.modules.mod0_ingest import (
    IngestConfig,
    VideoIngest0,
    build_ingest_config,
    run_analyze_only,
)

# ==============================================================================
# HELPERS: генерация синтетических видео
# ==============================================================================
def _ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _make_video(
    path: Path,
    duration: float = 2.0,
    width: int = 640,
    height: int = 360,
    fps: int = 30,
    rotation: int = 0,
    with_audio: bool = True,
) -> Path:
    """Генерирует синтетическое видео через FFmpeg testsrc + sine."""
    vf = "testsrc=duration={dur}:size={w}x{h}:rate={fps}".format(
        dur=duration, w=width, h=height, fps=fps
    )
    if rotation:
        vf += f",transpose={rotation}"

    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", vf]
    if with_audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}"]
        cmd += ["-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "ultrafast"]
    if with_audio:
        cmd += ["-c:a", "aac"]
    cmd.append(str(path))
    subprocess.run(cmd, capture_output=True, timeout=60)
    return path


# ==============================================================================
# FIXTURES
# ==============================================================================
@pytest.fixture()
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path / "work"


@pytest.fixture()
def sample_videos(tmp_path: Path) -> List[Path]:
    """Создаёт 2 синтетических видео (разные разрешения/фпс)."""
    v1 = _make_video(tmp_path / "clip1.mp4", duration=1.5, width=640, height=360, fps=30)
    v2 = _make_video(tmp_path / "clip2.mp4", duration=1.0, width=1280, height=720, fps=25)
    return [v1, v2]


# ==============================================================================
# ТЕСТЫ
# ==============================================================================
@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe не найдены в PATH")
@pytest.mark.asyncio
async def test_analyze_video_metadata(temp_dir: Path, sample_videos: List[Path]):
    """Проверяет сбор ffprobe-метаданных."""
    ingest = VideoIngest0(temp_dir)

    meta = await ingest.analyze_video(sample_videos[0])

    assert meta["success"] is True
    assert meta["filename"] == "clip1.mp4"
    assert meta["width"] > 0
    assert meta["height"] > 0
    assert meta["fps"] > 0
    assert meta["has_audio"] is True
    assert meta["duration"] > 0


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe не найдены в PATH")
@pytest.mark.asyncio
async def test_normalize_video_resolution(temp_dir: Path, sample_videos: List[Path]):
    """Проверяет приведение к целевым 1080x1920 через pad."""
    cfg = IngestConfig(target_fps=30, target_resolution=[1080, 1920])
    ingest = VideoIngest0(temp_dir, cfg)

    out = temp_dir / "normalized.mp4"
    ok = await ingest.normalize_video(sample_videos[0], out)

    assert ok is True
    assert out.exists() and out.stat().st_size > 0

    # Проверяем итоговое разрешение через ffprobe
    meta = await ingest.analyze_video(out)
    assert meta["width"] == 1080
    assert meta["height"] == 1920


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe не найдены в PATH")
@pytest.mark.asyncio
async def test_extract_audio(temp_dir: Path, sample_videos: List[Path]):
    """Проверяет извлечение аудио."""
    ingest = VideoIngest0(temp_dir)
    audio = await ingest.extract_audio(sample_videos[0])
    assert audio is not None
    assert audio.exists() and audio.stat().st_size > 0


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe не найдены в PATH")
@pytest.mark.asyncio
async def test_process_video_graceful_missing_file(temp_dir: Path):
    """Битый/отсутствующий файл не должен ронять обработку."""
    ingest = VideoIngest0(temp_dir)
    result = await ingest.process_video(temp_dir / "nonexistent.mp4")
    assert result["success"] is False
    assert result["normalized_path"] is None


@pytest.mark.asyncio
async def test_build_ingest_config_defaults():
    """Проверяет fallback-конфигурацию."""
    cfg = build_ingest_config({})
    assert cfg.target_fps == 30
    assert cfg.target_resolution == [1080, 1920]
    assert cfg.pad is True


@pytest.mark.asyncio
async def test_analyze_only_dry_run(tmp_path: Path, sample_videos: List[Path]):
    """Dry-run режим возвращает отчёт без создания файлов."""
    report = await run_analyze_only(tmp_path, {})
    assert len(report) >= 2
    for item in report:
        assert "filename" in item
        assert item["analyzed_at"] == "dry-run"