"""
Стадия 0: Ингестия и нормализация видеофайлов.

Модуль собирает ffprobe-метаданные, авто-поворачивает кадры по EXIF/rotate,
нормализует fps/разрешение к целевым (30 fps, 1080x1920 через pad),
извлекает аудио (PCM mono) для последующих стадий (whisper, beat-анализ).

Graceful fallback: битый/нечитаемый файл не роняет обработку, логируется
и пропускается. Поддерживается dry-run режим (--analyze-only).
"""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.config_loader import load_config
from src.utils.logger import ws_manager

logger = logging.getLogger("mod0_ingest")


# ==============================================================================
# Конфигурация
# ==============================================================================
class IngestConfig(BaseModel):
    """Конфигурация ингестии/нормализации."""

    target_fps: int = Field(30, description="Целевой FPS")
    interpolate: bool = Field(True, description="minterpolate для 24/25 fps")
    target_resolution: List[int] = Field([1080, 1920], description="Целевое разрешение WxH")
    pad: bool = Field(True, description="pad вместо crop (не теряем контент)")
    auto_rotate: bool = Field(True, description="авто-поворот по rotate/EXIF")
    extract_audio: bool = Field(True, description="извлекать аудио")
    audio_sample_rate: int = Field(16000, description="частота дискретизации аудио")
    fast_mode: bool = Field(False, description="быстрый режим: анализ в 640x360")
    analysis_resolution: List[int] = Field([640, 360], description="разрешение для анализа в быстром режиме")
    ffmpeg_preset: str = Field("fast", description="пресет кодирования FFmpeg (ultrafast/fast/medium)")


def build_ingest_config(config: Optional[Dict[str, Any]] = None,
                        performance: Optional[Dict[str, Any]] = None) -> IngestConfig:
    """Строит IngestConfig из dict (или fallback-конфигурацию по умолчанию).

    Args:
        config: основной YAML-конфиг.
        performance: профиль производительности (fast/normal/quality) из
            load_performance_config(). Его значения имеют приоритет.
    """
    if not config:
        base = {}
    else:
        base = config.get("ingest", {}) if isinstance(config, dict) else {}

    # Применяем профиль производительности поверх.
    preset = base.get("ffmpeg_preset", "fast")
    analysis_res = list(base.get("analysis_resolution", [640, 360]))
    if performance:
        if performance.get("ffmpeg_preset"):
            preset = performance["ffmpeg_preset"]
        if performance.get("analysis_resolution"):
            try:
                w, h = performance["analysis_resolution"].lower().split("x")
                analysis_res = [int(w), int(h)]
            except Exception:  # noqa: BLE001
                pass

    fast_mode = bool(base.get("fast_mode", False)) or preset in ("ultrafast",)

    return IngestConfig(
        target_fps=base.get("target_fps", 30),
        interpolate=base.get("interpolate", True),
        target_resolution=list(base.get("target_resolution", [1080, 1920])),
        pad=base.get("pad", True),
        auto_rotate=base.get("auto_rotate", True),
        extract_audio=base.get("extract_audio", True),
        audio_sample_rate=base.get("audio_sample_rate", 16000),
        analysis_resolution=analysis_res,
        ffmpeg_preset=preset,
        fast_mode=fast_mode,
    )


# ==============================================================================
# Основной класс ингестии
# ==============================================================================
class VideoIngest0:
    """Сбор метаданных и нормализация одного видеофайла."""

    def __init__(self, temp_dir: Path, config: Optional[IngestConfig] = None):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or IngestConfig()

    async def _run(self, cmd: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
        """Запускает subprocess и возвращает результат (без блокировки loop).

        Args:
            cmd: команда для выполнения.
            timeout: таймаут в секундах (по умолчанию 120).
        """
        return await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, timeout=timeout
        )

    def _get_dynamic_timeout(self, video_path: Path) -> int:
        """Вычисляет динамический таймаут на основе длительности видео.

        Формула: max(120, duration * 2), максимум 7200 сек (2 часа).
        """
        try:
            import subprocess as sp
            result = sp.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(video_path)],
                capture_output=True, text=True, timeout=10
            )
            duration = float(result.stdout.strip() or "0")
            return max(120, min(int(duration * 2), 7200))
        except Exception:
            return 120

    # ------------------------------------------------------------------ метаданные
    async def analyze_video(self, video_path: Path) -> Dict[str, Any]:
        """Собирает ffprobe-метаданные о видео."""
        video_path = Path(video_path)
        cmd = [
            "ffprobe", "-v", "error", "-print_format", "json",
            "-show_streams", "-show_format", str(video_path),
        ]
        try:
            proc = await self._run(cmd)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.decode(errors="ignore")[:300])
            data = json.loads(proc.stdout.decode(errors="ignore"))

            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"), {}
            )
            audio_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {}
            )

            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            rotation = 0
            side_data = video_stream.get("side_data_list", [])
            for sd in side_data:
                if "rotation" in sd:
                    rotation = int(float(sd["rotation"]))
                    break

            fps_num = video_stream.get("avg_frame_rate", "30/1")
            try:
                num, den = fps_num.split("/")
                fps = int(num) / int(den) if int(den) else 0.0
            except Exception:  # noqa: BLE001
                fps = 0.0

            duration = float(data.get("format", {}).get("duration", 0) or 0)

            return {
                "success": True,
                "filename": video_path.name,
                "path": str(video_path),
                "width": width,
                "height": height,
                "rotation": rotation,
                "fps": round(fps, 2),
                "duration": duration,
                "has_audio": bool(audio_stream),
                "codec": video_stream.get("codec_name", ""),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось проанализировать %s: %s", video_path.name, exc)
            return {
                "success": False,
                "filename": video_path.name,
                "path": str(video_path),
                "error": str(exc),
            }

    # ------------------------------------------------------------------ нормализация
    async def normalize_video(self, video_path: Path, output_path: Path) -> bool:
        """Нормализует видео к целевым fps/разрешению (pad). Возвращает True при успехе."""
        meta = await self.analyze_video(video_path)
        if not meta.get("success"):
            return False

        tw, th = self.config.target_resolution
        vf_parts: List[str] = []

        # Авто-поворот по EXIF/rotate.
        if self.config.auto_rotate and meta.get("rotation"):
            rotation = meta["rotation"]
            if rotation == 90:
                vf_parts.append("transpose=1")
            elif rotation == 180:
                vf_parts.append("transpose=1,transpose=1")
            elif rotation == 270:
                vf_parts.append("transpose=2")

        # Приведение к целевому размеру с pad (не теряем контент).
        vf_parts.append(f"scale={tw}:{th}:force_original_aspect_ratio=decrease")
        if self.config.pad:
            vf_parts.append(f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:color=black")

        # Нормализация fps.
        fps_filter = ""
        if meta.get("fps") and abs(float(meta["fps"]) - self.config.target_fps) > 1:
            if self.config.interpolate:
                fps_filter = f",minterpolate=fps={self.config.target_fps}"
            else:
                fps_filter = f",fps={self.config.target_fps}"

        vf = ",".join(vf_parts) + fps_filter

        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", vf,
            "-c:v", "libx264", "-preset", self.config.ffmpeg_preset, "-crf", "23",
            "-an",  # без аудио на этом шаге
            str(output_path),
        ]
        timeout = self._get_dynamic_timeout(video_path)
        try:
            proc = await self._run(cmd, timeout=timeout)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.decode(errors="ignore")[:300])
            return output_path.exists() and output_path.stat().st_size > 0
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ошибка нормализации %s: %s", video_path.name, exc)
            return False

    # ------------------------------------------------------------------ аудио
    async def extract_audio(self, video_path: Path) -> Optional[Path]:
        """Извлекает аудио (PCM mono) в temp_dir. Возвращает путь или None."""
        output_path = self.temp_dir / f"{Path(video_path).stem}.wav"
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-ac", "1",
            "-ar", str(self.config.audio_sample_rate),
            str(output_path),
        ]
        timeout = self._get_dynamic_timeout(video_path)
        try:
            proc = await self._run(cmd, timeout=timeout)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.decode(errors="ignore")[:300])
            if output_path.exists() and output_path.stat().st_size > 0:
                return output_path
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ошибка извлечения аудио %s: %s", video_path.name, exc)
            return None

    # ------------------------------------------------------------------ детекция сцен
    async def detect_scenes(self, video_path: Path) -> List[Dict[str, Any]]:
        """Детектирует сцены в видео длиннее 5 минут через PySceneDetect.

        Returns:
            список словарей {start_sec, end_sec, duration_sec}.
        """
        try:
            from scenedetect import open_video, SceneManager
            from scenedetect.detectors import ContentDetector

            video = open_video(str(video_path))
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector(threshold=27.0))
            scene_manager.detect_scenes(video)
            scene_list = scene_manager.get_scene_list()

            scenes = []
            for start, end in scene_list:
                scenes.append({
                    "start_sec": start.get_seconds(),
                    "end_sec": end.get_seconds(),
                    "duration_sec": end.get_seconds() - start.get_seconds(),
                })
            await ws_manager.broadcast(
                f"  🎬 Детектировано {len(scenes)} сцен в {video_path.name}"
            )
            return scenes
        except Exception as exc:  # noqa: BLE001
            logger.warning("Детекция сцен не удалась (%s): %s", video_path.name, exc)
            return []

    # ------------------------------------------------------------------ полный процесс
    async def process_video(self, video_path: Path) -> Dict[str, Any]:
        """Полный цикл: метаданные -> нормализация -> аудио."""
        video_path = Path(video_path)
        if not video_path.exists():
            logger.warning("Файл не найден: %s", video_path)
            return {"success": False, "filename": video_path.name, "error": "file not found",
                    "normalized_path": None, "meta": {"filename": video_path.name, "success": False}}

        meta = await self.analyze_video(video_path)
        if not meta.get("success"):
            return {**meta, "normalized_path": None}

        normalized_path = self.temp_dir / f"norm_{video_path.stem}.mp4"
        ok = await self.normalize_video(video_path, normalized_path)
        normalized = str(normalized_path) if ok and normalized_path.exists() else None

        audio_path = None
        if self.config.extract_audio and normalized:
            audio_path = await self.extract_audio(Path(normalized))
            audio_path = str(audio_path) if audio_path else None

        # Детекция сцен для видео длиннее 5 минут.
        scenes = []
        duration = meta.get("duration", 0)
        if duration > 300:
            scenes = await self.detect_scenes(video_path)

        return {
            "success": True,
            "meta": meta,
            "normalized_path": normalized,
            "audio_path": audio_path,
            "duration": duration,
            "scenes": scenes,
            "transcript": [],
        }

    # ------------------------------------------------------------------ dry-run
    async def analyze_only(self, video_files: List[Path]) -> List[Dict[str, Any]]:
        """Dry-run: собирает метаданные по всем файлам без обработки."""
        report = []
        for video in video_files:
            meta = await self.analyze_video(video)
            meta["analyzed_at"] = "dry-run"
            report.append(meta)
        return report


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