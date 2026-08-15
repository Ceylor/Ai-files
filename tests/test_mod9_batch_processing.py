"""
Тесты модуля 9: МАССОВАЯ ОБРАБОТКА И КОМПОЗИЦИЯ.

Проверяют:
    - ClipComposer: кластеризацию фрагментов по CLIP-эмбеддингам;
    - ClipComposer: compose_clips создаёт несколько планов клипов;
    - ClipComposer.group_by_time — fallback-группировку без CLIP;
    - BatchProcessor.process_folder — очередь с моками шагов;
    - graceful shutdown через stop_event;
    - _run_editing с реальным монтажом и fallback-копией;
    - _compose_and_save — сохранение композиций в БД.

Запуск:
    python -m pytest tests/test_mod9_batch_processing.py -v

Требования: pytest, pytest-asyncio.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.modules.mod9_batch_processing.composer import ClipComposer


# ==============================================================================
# ТЕСТЫ: CLIP COMPOSER (кластеризация)
# ==============================================================================
def _frag(video_id: int, path: str, embedding: List[float]) -> Dict[str, Any]:
    return {"video_id": video_id, "path": path, "embedding": embedding}


def test_cluster_empty():
    """Пустой список фрагментов → пустой список кластеров."""
    composer = ClipComposer()
    assert composer.cluster_fragments([]) == []


def test_cluster_similar_fragments():
    """Похожие по смыслу фрагменты объединяются в один кластер."""
    composer = ClipComposer(similarity_threshold=0.8)
    fragments = [
        _frag(1, "/v1.mp4", [1.0, 0.0, 0.0]),
        _frag(1, "/v2.mp4", [0.98, 0.02, 0.0]),
        _frag(2, "/v3.mp4", [0.0, 1.0, 0.0]),
    ]
    clusters = composer.cluster_fragments(fragments)
    # Два кластера: [v1,v2] и [v3].
    assert len(clusters) == 2
    assert len(clusters[0]) >= 1
    # В первом кластере — похожие фрагменты v1 и v2.
    paths = [f["path"] for f in clusters[0]]
    assert "/v1.mp4" in paths and "/v2.mp4" in paths


def test_cluster_max_size():
    """max_cluster_size ограничивает число фрагментов в кластере."""
    composer = ClipComposer(similarity_threshold=0.5, max_cluster_size=2)
    fragments = [
        _frag(1, f"/v{i}.mp4", [1.0, 0.0]) for i in range(4)
    ]
    clusters = composer.cluster_fragments(fragments)
    for cluster in clusters:
        assert len(cluster) <= 2


def test_compose_clips_creates_multiple(tmp_path: Path):
    """compose_clips создаёт несколько планов клипов и выходные пути."""
    composer = ClipComposer(similarity_threshold=0.8)
    fragments = [
        _frag(1, "/a.mp4", [1.0, 0.0]),
        _frag(1, "/b.mp4", [0.99, 0.01]),
        _frag(2, "/c.mp4", [0.0, 1.0]),
    ]
    plans = composer.compose_clips(fragments, tmp_path, prefix="clip")
    assert len(plans) >= 1
    assert plans[0]["name"].startswith("clip_")
    assert Path(plans[0]["output_path"]).parent == tmp_path


def test_group_by_time_fallback():
    """group_by_time группирует по порядку по group_size штук."""
    fragments = [_frag(i, f"/v{i}.mp4", []) for i in range(7)]
    groups = ClipComposer.group_by_time(fragments, group_size=3)
    assert [len(g) for g in groups] == [3, 3, 1]


# ==============================================================================
# ТЕСТЫ: BATCH PROCESSOR
# ==============================================================================
@pytest.mark.asyncio
async def test_process_folder_success(tmp_path: Path, monkeypatch):
    """
    process_folder корректно обрабатывает pending-видео и завершает задачу.
    Мокаем _process_one и _compose_and_save, чтобы не выполнять реальный монтаж.
    """
    from src.modules.mod9_batch_processing.processor import BatchProcessor

    processor = BatchProcessor(
        work_dir=tmp_path / "work",
        output_dir=tmp_path / "out",
        category="test",
    )

    pending = [
        {"id": 1, "file_path": "/tmp/a.mp4", "status": "pending"},
        {"id": 2, "file_path": "/tmp/b.mp4", "status": "pending"},
    ]

    processed_ids = []

    async def fake_process_one(video, folder_id):
        processed_ids.append(video["id"])

    async def noop(*args, **kwargs):
        await asyncio.sleep(0)

    # Мокаем шаги.
    monkeypatch.setattr(processor, "_get_pending_videos", lambda fid: pending)
    monkeypatch.setattr(processor, "_process_one", fake_process_one)
    monkeypatch.setattr(processor, "_compose_and_save", noop)
    monkeypatch.setattr(processor, "_set_batch_status", noop)
    monkeypatch.setattr(processor, "_update_batch_progress", noop)
    monkeypatch.setattr(processor, "_finish_batch", noop)

    result = await processor.process_folder(42)

    assert result == {"folder_id": 42, "processed": 2, "total": 2}
    assert processed_ids == [1, 2]


@pytest.mark.asyncio
async def test_process_folder_graceful_shutdown(tmp_path: Path, monkeypatch):
    """
    При установленном stop_event обработка останавливается досрочно
    и композиция не запускается.
    """
    from src.modules.mod9_batch_processing.processor import BatchProcessor

    processor = BatchProcessor(
        work_dir=tmp_path / "work",
        output_dir=tmp_path / "out",
        category="test",
    )

    pending = [
        {"id": 1, "file_path": "/tmp/a.mp4", "status": "pending"},
        {"id": 2, "file_path": "/tmp/b.mp4", "status": "pending"},
        {"id": 3, "file_path": "/tmp/c.mp4", "status": "pending"},
    ]

    composed_called = []

    async def fake_process_one(video, folder_id):
        # Останавливаемся после первого видео.
        processor._stop_event.set()
        await asyncio.sleep(0)

    async def fake_compose(folder_id):
        composed_called.append(folder_id)

    async def noop(*args, **kwargs):
        await asyncio.sleep(0)

    monkeypatch.setattr(processor, "_get_pending_videos", lambda fid: pending)
    monkeypatch.setattr(processor, "_process_one", fake_process_one)
    monkeypatch.setattr(processor, "_compose_and_save", fake_compose)
    monkeypatch.setattr(processor, "_set_batch_status", noop)
    monkeypatch.setattr(processor, "_update_batch_progress", noop)
    monkeypatch.setattr(processor, "_finish_batch", noop)

    result = await processor.process_folder(99)

    # Обработан только один (остальные пропущены из-за stop_event).
    assert result["processed"] == 1
    assert result["total"] == 3
    # Композиция не запускается при graceful shutdown.
    assert composed_called == []


@pytest.mark.asyncio
async def test_process_one_marks_completed(tmp_path: Path, monkeypatch):
    """
    _process_one для существующего файла проходит шаги и ставит статус completed.
    """
    from src.modules.mod9_batch_processing.processor import BatchProcessor

    processor = BatchProcessor(
        work_dir=tmp_path / "work",
        output_dir=tmp_path / "out",
        category="test",
    )

    video_file = tmp_path / "input.mp4"
    video_file.write_bytes(b"fake-video")

    video = {"id": 7, "file_path": str(video_file), "status": "pending"}

    async def fake_step(*args, **kwargs):
        return {}

    statuses = []

    async def fake_set_status(video_id, status):
        statuses.append((video_id, status))

    async def fake_editing(video_path, story):
        return str(tmp_path / "out.mp4")

    monkeypatch.setattr(processor, "_run_ingest", fake_step)
    monkeypatch.setattr(processor, "_run_analysis", fake_step)
    monkeypatch.setattr(processor, "_find_pattern", fake_step)
    monkeypatch.setattr(processor, "_build_story", fake_step)
    monkeypatch.setattr(processor, "_run_editing", fake_editing)
    monkeypatch.setattr(processor, "_set_video_status", fake_set_status)

    await processor._process_one(video, folder_id=5)

    assert (7, "processing") in statuses
    assert (7, "completed") in statuses


@pytest.mark.asyncio
async def test_run_editing_uses_pipeline(tmp_path: Path, monkeypatch):
    """
    _run_editing использует VideoPipeline.process_batch для реального монтажа.
    """
    from src.modules.mod9_batch_processing.processor import BatchProcessor

    processor = BatchProcessor(
        work_dir=tmp_path / "work",
        output_dir=tmp_path / "out",
        category="test",
    )

    src = tmp_path / "input.mp4"
    src.write_bytes(b"data")

    async def noop(*args, **kwargs):
        await asyncio.sleep(0)

    monkeypatch.setattr(processor, "_broadcast", noop)

    # Мокаем VideoPipeline внутри метода.
    fake_output = tmp_path / "out" / "edited.mp4"
    fake_output.parent.mkdir(parents=True, exist_ok=True)
    fake_output.write_bytes(b"edited")

    class FakePipeline:
        async def process_batch(self, input_files, style_profile=None, category=None):
            return [fake_output]

    import src.core.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "VideoPipeline", lambda config: FakePipeline())

    out = await processor._run_editing(src, story=None)
    assert out == str(fake_output)


@pytest.mark.asyncio
async def test_run_editing_fallback_copy(tmp_path: Path, monkeypatch):
    """
    При сбое реального монтажа _run_editing делает fallback-копию исходника.
    """
    from src.modules.mod9_batch_processing.processor import BatchProcessor

    processor = BatchProcessor(
        work_dir=tmp_path / "work",
        output_dir=tmp_path / "out",
        category="test",
    )

    async def noop(*args, **kwargs):
        await asyncio.sleep(0)

    monkeypatch.setattr(processor, "_broadcast", noop)

    src = tmp_path / "input.mp4"
    src.write_bytes(b"data")

    # Мокаем VideoPipeline, который бросает исключение.
    class FakeBrokenPipeline:
        async def process_batch(self, input_files, style_profile=None, category=None):
            raise RuntimeError("pipeline failed")

    import src.core.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "VideoPipeline", lambda config: FakeBrokenPipeline())

    out = await processor._run_editing(src, story=None)
    assert Path(out).exists()
    assert Path(out).suffix == ".mp4"


@pytest.mark.asyncio
async def test_compose_and_save(tmp_path: Path, monkeypatch):
    """
    _compose_and_save сохраняет композиции в БД как новые записи videos.
    """
    from src.modules.mod9_batch_processing.processor import BatchProcessor
    from src.modules.mod9_batch_processing import processor as processor_mod

    processor = BatchProcessor(
        work_dir=tmp_path / "work",
        output_dir=tmp_path / "out",
        category="test",
    )
    processor.output_dir.mkdir(parents=True, exist_ok=True)

    async def noop(*args, **kwargs):
        await asyncio.sleep(0)

    monkeypatch.setattr(processor, "_broadcast", noop)

    # Класс видео-заглушки (с атрибутом file_path, который нужен _compose_and_save).
    class FakeVideo:
        def __init__(self, vid, status, file_path):
            self.id = vid
            self.status = status
            self.file_path = file_path

    completed_video = FakeVideo(1, "completed", "/dummy/path/video.mp4")
    not_completed = FakeVideo(2, "error", "/dummy/path/other.mp4")

    # Мокаем session_scope и CRUD.
    saved = []

    class FakeDB:
        pass

    fake_db = FakeDB()

    class FakeSessionScope:
        def __enter__(self):
            return fake_db

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(processor_mod, "session_scope", lambda: FakeSessionScope())
    monkeypatch.setattr(
        processor_mod.db_crud, "list_videos",
        lambda db, batch_job_id=None: [completed_video, not_completed],
    )
    monkeypatch.setattr(
        processor_mod.db_crud, "get_frame_embeddings",
        lambda db, video_id: [{"embedding": [1.0, 0.0]}],
    )

    def fake_create_video(db, path, **kwargs):
        saved.append({"path": path, "kwargs": kwargs})
        return FakeVideo(len(saved) + 10, "composed", str(path))

    monkeypatch.setattr(processor_mod.db_crud, "create_video", fake_create_video)

    await processor._compose_and_save(folder_id=7)

    # Хотя бы одна композиция должна быть создана.
    assert len(saved) >= 1
    assert saved[0]["kwargs"]["status"] == "composed"
    assert saved[0]["kwargs"]["batch_job_id"] == 7