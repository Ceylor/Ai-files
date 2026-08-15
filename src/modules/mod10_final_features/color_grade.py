"""
Авто-цветокоррекция фрагментов на основе анализа сцен (mod8_analysis).

Для каждого фрагмента подбирает цветовой профиль на основе эмоций/движения:
- динамичные/энергичные сцены → контраст + насыщенность (поп);
- спокойные сцены → мягкая гамма, лёгкий баланс белого;
- тёмные сцены → подъём теней.
Применяет через FFmpeg (eq/curves/colorbalance).
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import ws_manager

logger = logging.getLogger("final.color_grade")


class ColorGrader:
    """Автоматическая цветокоррекция по контексту сцены."""

    # Профили цветокоррекции (параметры FFmpeg eq/curves).
    PROFILES: Dict[str, Dict[str, Any]] = {
        "energetic": {  # динамичные/эпичные сцены
            "contrast": 1.15,
            "saturation": 1.25,
            "brightness": 0.02,
            "gamma": 1.0,
            "label": "Энергичный",
        },
        "calm": {  # спокойные сцены
            "contrast": 1.0,
            "saturation": 1.05,
            "brightness": 0.0,
            "gamma": 1.05,
            "label": "Спокойный",
        },
        "dark": {  # тёмные сцены (подъём теней)
            "contrast": 1.08,
            "saturation": 1.1,
            "brightness": 0.03,
            "gamma": 1.1,
            "label": "Тёмный",
        },
        "natural": {  # естественный
            "contrast": 1.0,
            "saturation": 1.0,
            "brightness": 0.0,
            "gamma": 1.0,
            "label": "Естественный",
        },
    }

    def __init__(self) -> None:
        self.profiles = self.PROFILES

    def pick_profile(self, analysis: Optional[Dict[str, Any]]) -> str:
        """
        Выбирает цветовой профиль по результатам анализа сцены.

        Args:
            analysis: dict из mod8 (emotions, motion, objects) или None.

        Returns:
            Имя профиля ("energetic" / "calm" / "dark" / "natural").
        """
        if not analysis:
            return "natural"

        motion = analysis.get("motion", [])
        emotions = analysis.get("emotions", [])

        # Средняя энергия движения.
        energy = 0.0
        if motion:
            energy = sum(float(m.get("energy", 0)) for m in motion) / len(motion)

        # Доминирующая эмоция.
        dominant_emotion = "neutral"
        if emotions:
            dominant_emotion = emotions[0].get("emotion", "neutral")

        # Логика выбора профиля.
        if energy > 0.7:
            return "energetic"
        if dominant_emotion in ("happy", "surprise", "angry"):
            return "energetic"
        if energy < 0.2 and dominant_emotion in ("sad", "neutral", "fear"):
            return "calm"
        if energy < 0.1:
            return "dark"
        return "natural"

    def build_filter(self, profile_name: str) -> str:
        """
        Строит FFmpeg-фильтр eq для цветокоррекции по профилю.

        Returns:
            Строка фильтра FFmpeg (например "eq=contrast=1.15:saturation=1.25").
        """
        prof = self.profiles.get(profile_name, self.profiles["natural"])
        contrast = prof.get("contrast", 1.0)
        saturation = prof.get("saturation", 1.0)
        brightness = prof.get("brightness", 0.0)
        gamma = prof.get("gamma", 1.0)

        parts = [f"eq=contrast={contrast}:saturation={saturation}"]
        if brightness:
            parts.append(f"brightness={brightness}")
        if gamma != 1.0:
            parts.append(f"gamma={gamma}")
        return ",".join(parts)

    async def grade_fragment(
        self,
        video_path: Path,
        output_path: Path,
        analysis: Optional[Dict[str, Any]],
    ) -> Path:
        """
        Применяет цветокоррекцию к фрагменту через FFmpeg.

        Args:
            video_path: исходное видео.
            output_path: путь для результата.
            analysis: результаты анализа сцены (для выбора профиля).

        Returns:
            Путь к откорректированному видео.
        """
        profile_name = self.pick_profile(analysis)
        vf = self.build_filter(profile_name)
        await ws_manager.broadcast(
            f"  🎨 Цветокоррекция ({self.profiles[profile_name]['label']})..."
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "copy",
            str(output_path),
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0 or not output_path.exists():
            error = stderr.decode("utf-8", errors="ignore")[:200]
            logger.warning("Цветокоррекция не удалась (%s), fallback на исходник", error)
            return video_path

        return output_path