"""
Загрузчик конфигурации AI AutoEditor.

Читает конфигурацию из YAML (configs/config.yaml) с graceful fallback
на значения по умолчанию, если файл отсутствует или повреждён.

Также загружает конфигурацию производительности (configs/performance.json)
с профилями fast/normal/quality.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("core.config_loader")

# Путь к конфигу по умолчанию (относительно корня проекта).
DEFAULT_CONFIG_PATH = Path("configs/config.yaml")
PERFORMANCE_CONFIG_PATH = Path("configs/performance.json")

# Значения по умолчанию, если YAML отсутствует/повреждён.
DEFAULT_CONFIG: Dict[str, Any] = {
    "general": {
        "input_dir": "./data/input",
        "output_dir": "./data/output",
        "temp_dir": "./data/temp",
        "music_library_dir": "./data/music_library",
        "resolution": [1080, 1920],
        "fps": 30,
        "video_bitrate": "8M",
        "audio_bitrate": "192k",
        "log_level": "INFO",
    },
    "ingest": {
        "target_fps": 30,
        "interpolate": True,
        "target_resolution": [1080, 1920],
        "pad": True,
        "auto_rotate": True,
        "extract_audio": True,
        "audio_sample_rate": 16000,
    },
    "ai_brain": {
        "primary_provider": "ollama",
        "ollama": {
            "model": "qwen2.5-coder:3b",
            "base_url": "http://localhost:11434",
            "timeout": 120,
            "num_gpu": 15,
        },
        "cloud_fallback": {
            "enabled": False,
            "provider": "gigachat",
            "client_id_env": "GIGACHAT_CLIENT_ID",
            "scope": "GIGACHAT_API_PERS",
            "authorization_key_env": "GIGACHAT_AUTH_KEY",
            "model": "GigaChat-2-Max",
            "token_cache_file": "./data/temp/gigachat_token.json",
            "token_refresh_threshold": 300,
        },
    },
    "subtitles": {
        "enabled": True,
        "font": {"path": "./assets/fonts/Montserrat-Bold.ttf", "size": 52, "color": "#FFFFFF"},
        "highlight": {"enabled": True, "color": "#FFD700", "keywords_file": "./assets/keywords.txt"},
        "position": {"x": 540, "y": 1500, "alignment": "center"},
        "effects": {"shadow": True, "shadow_color": "#000000", "outline": True, "outline_width": 3},
        "animation": {"type": "word_by_word", "word_delay_ms": 60},
    },
    "music": {
        "source": "hybrid",
        "pixabay": {"api_key_env": "PIXABAY_API_KEY"},
        "mood_matching": True,
        "bpm_sync": True,
        "volume": {
            "voice_ducking_db": -14,
            "music_volume_db": -20,
            "fade_in_sec": 1.5,
            "fade_out_sec": 2.5,
        },
    },
    "editing": {
        "max_clip_duration": 60,
        "min_clip_duration": 15,
        "target_clips_count": "auto",
        "transition_type": "dynamic_cut",
        "auto_reframe": {"enabled": True, "tracking": "face", "padding": 1.25, "smoothing": 0.8},
        "ken_burns": {"enabled": True, "zoom_factor": 1.15},
    },
    "export": {
        "codec": "h264_nvenc",
        "preset": "p4",
        "tune": "hq",
        "rc": "vbr",
        "cq": 19,
        "platforms": [
            {"name": "vk_clips", "tags": ["#shorts", "#vk"]},
            {"name": "yt_shorts", "tags": ["#shorts", "#youtube"]},
        ],
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Рекурсивно сливает override-словарь в base (base имеет приоритет для вложенных)."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Загружает конфигурацию из YAML-файла.

    Args:
        config_path: путь к YAML-конфигу. Если None — используется
            DEFAULT_CONFIG_PATH.

    Returns:
        Словарь конфигурации. При ошибке загрузки возвращает DEFAULT_CONFIG.
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    if not path.exists():
        logger.warning("Конфиг %s не найден, использую значения по умолчанию.", path)
        return dict(DEFAULT_CONFIG)

    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        # Сливаем поверх дефолтов, чтобы гарантировать наличие всех секций.
        config = _deep_merge(DEFAULT_CONFIG, loaded)
        return config
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ошибка загрузки конфига %s (%s), использую дефолт.", path, exc)
        return dict(DEFAULT_CONFIG)


# Профили производительности по умолчанию (fallback при отсутствии performance.json).
_DEFAULT_PERFORMANCE: Dict[str, Any] = {
    "profiles": {
        "fast": {
            "analysis_resolution": "320x180",
            "whisper_model": "tiny",
            "whisper_compute_type": "int8",
            "yolo_model": "yolov8n",
            "clip_batch_size": 1,
            "scene_detection_threshold": 30,
            "max_concurrent_videos": 1,
            "ffmpeg_preset": "ultrafast",
            "chunk_duration_seconds": 180,
        },
        "normal": {
            "analysis_resolution": "640x360",
            "whisper_model": "small",
            "whisper_compute_type": "int8",
            "yolo_model": "yolov8n",
            "clip_batch_size": 4,
            "scene_detection_threshold": 27,
            "max_concurrent_videos": 1,
            "ffmpeg_preset": "fast",
            "chunk_duration_seconds": 300,
        },
        "quality": {
            "analysis_resolution": "1280x720",
            "whisper_model": "medium",
            "whisper_compute_type": "float16",
            "yolo_model": "yolov8m",
            "clip_batch_size": 8,
            "scene_detection_threshold": 25,
            "max_concurrent_videos": 2,
            "ffmpeg_preset": "medium",
            "chunk_duration_seconds": 420,
        },
    },
    "default": "normal",
    "chunk_duration_seconds": 300,
}


def load_performance_config(performance_mode: Optional[str] = None) -> Dict[str, Any]:
    """
    Загружает конфигурацию производительности (configs/performance.json)
    и возвращает параметры для выбранного профиля (fast/normal/quality).

    Args:
        performance_mode: имя профиля ('fast', 'normal', 'quality').
            Если None — используется профиль по умолчанию из конфига.

    Returns:
        Словарь параметров производительности для профиля.
    """
    data: Dict[str, Any] = {}
    try:
        if PERFORMANCE_CONFIG_PATH.exists():
            with open(PERFORMANCE_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ошибка загрузки performance.json (%s), использую дефолт", exc)
        data = {}

    # Сливаем с дефолтами, чтобы гарантировать наличие всех ключей.
    merged = _deep_merge(_DEFAULT_PERFORMANCE, data)

    profiles = merged.get("profiles", {})
    default_profile = merged.get("default", "normal")

    mode = performance_mode or default_profile
    if mode not in profiles:
        logger.warning("Профиль '%s' не найден, используем '%s'", mode, default_profile)
        mode = default_profile

    profile = profiles[mode]
    # Добавляем имя профиля и значения chunk_duration по умолчанию.
    result = dict(profile)
    result["mode"] = mode
    result.setdefault("chunk_duration_seconds", merged.get("chunk_duration_seconds", 300))
    return result