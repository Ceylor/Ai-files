"""
Профили экспорта для разных платформ и качеств.

Преобразует выбор пользователя (HD/FHD/4K, TikTok/Shorts/Reels) в
параметры FFmpeg (разрешение, битрейт, aspect ratio, максимальная длина).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class ExportProfiles:
    """Профили экспорта видео."""

    # Пресеты качества (по названию).
    QUALITY_PRESETS: Dict[str, Dict[str, Any]] = {
        "hd": {"height": 720, "bitrate": "4M", "label": "HD (720p)"},
        "fhd": {"height": 1080, "bitrate": "8M", "label": "Full HD (1080p)"},
        "4k": {"height": 2160, "bitrate": "20M", "label": "4K"},
    }

    # Платформенные пресеты.
    PLATFORM_PRESETS: Dict[str, Dict[str, Any]] = {
        "tiktok": {
            "aspect": "9:16",
            "max_duration": 60,
            "label": "TikTok",
            "quality": "fhd",
        },
        "yt_shorts": {
            "aspect": "9:16",
            "max_duration": 60,
            "label": "YouTube Shorts",
            "quality": "fhd",
        },
        "instagram_reels": {
            "aspect": "9:16",
            "max_duration": 90,
            "label": "Instagram Reels",
            "quality": "fhd",
        },
        "youtube": {
            "aspect": "16:9",
            "max_duration": 0,  # без ограничения
            "label": "YouTube",
            "quality": "fhd",
        },
    }

    def list_platforms(self) -> List[str]:
        """Список доступных платформенных пресетов."""
        return list(self.PLATFORM_PRESETS.keys())

    def list_qualities(self) -> List[str]:
        """Список доступных качеств."""
        return list(self.QUALITY_PRESETS.keys())

    def get_platform(self, name: str) -> Optional[Dict[str, Any]]:
        """Возвращает пресет платформы по имени."""
        return self.PLATFORM_PRESETS.get(name)

    def get_quality(self, name: str) -> Optional[Dict[str, Any]]:
        """Возвращает пресет качества по имени."""
        return self.QUALITY_PRESETS.get(name)

    def resolve(
        self,
        platform: str = "tiktok",
        quality: Optional[str] = None,
        max_duration: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Собирает итоговые параметры экспорта для FFmpeg.

        Args:
            platform: имя платформы (tiktok/yt_shorts/instagram_reels/youtube).
            quality: желаемое качество (hd/fhd/4k). Если None — из пресета платформы.
            max_duration: переопределение максимальной длительности.

        Returns:
            dict {height, bitrate, aspect, max_duration, platform, label, vf}.
        """
        pl = self.PLATFORM_PRESETS.get(platform, self.PLATFORM_PRESETS["tiktok"])
        q_name = quality or pl.get("quality", "fhd")
        q = self.QUALITY_PRESETS.get(q_name, self.QUALITY_PRESETS["fhd"])

        height = q["height"]
        bitrate = q["bitrate"]
        aspect = pl["aspect"]
        duration = max_duration if max_duration is not None else pl.get("max_duration", 60)

        # Видеофильтр для приведения к нужному aspect.
        # 9:16 → вертикальное; 16:9 → горизонтальное.
        # Ключевой момент: scale с force_original_aspect_ratio=decrease
        # уменьшает видео, чтобы оно влезло в целевые размеры, а pad
        # добавляет чёрные полосы до точного разрешения.
        if aspect == "9:16":
            width = int(height * 9 / 16) // 2 * 2  # чётное
            vf = (
                f"scale={width}:-2:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
            )
        else:
            width = int(height * 16 / 9) // 2 * 2
            vf = (
                f"scale=-2:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
            )

        return {
            "platform": platform,
            "label": f"{pl['label']} • {q['label']}",
            "width": width,
            "height": height,
            "bitrate": bitrate,
            "aspect": aspect,
            "max_duration": duration,
            "vf": vf,
            "quality": q_name,
        }