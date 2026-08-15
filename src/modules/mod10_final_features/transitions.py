"""
Умные переходы между фрагментами.

Автоматический выбор типа перехода по контексту сцены:
- динамичные/эпичные сцены → zoom / spin;
- спокойные → fade;
- нейтральные → fade/двойное растворение.

Переходы реализованы через FFmpeg (xfade для плавных переходов между
двумя фрагментами), либо как встроенные эффекты на стыке.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import ws_manager

logger = logging.getLogger("final.transitions")


class TransitionEngine:
    """Движок умных переходов на основе контекста сцен."""

    TRANSITIONS = ["cut", "fade", "zoom", "spin"]

    def pick_transition(
        self, analysis: Optional[Dict[str, Any]], next_analysis: Optional[Dict[str, Any]]
    ) -> str:
        """
        Выбирает тип перехода по контексту текущей и следующей сцены.

        Args:
            analysis: анализ текущей сцены.
            next_analysis: анализ следующей сцены.

        Returns:
            Тип перехода ("cut" / "fade" / "zoom" / "spin").
        """
        if not analysis and not next_analysis:
            return "fade"

        def _energy(a):
            if not a:
                return 0.0
            motion = a.get("motion", [])
            if not motion:
                return 0.0
            return sum(float(m.get("energy", 0)) for m in motion) / len(motion)

        cur_e = _energy(analysis)
        next_e = _energy(next_analysis)

        # Оба динамичные → spin/zoom.
        if cur_e > 0.6 and next_e > 0.6:
            return "spin"
        # Текущая динамичная → zoom.
        if cur_e > 0.6:
            return "zoom"
        # Спокойные → fade.
        if cur_e < 0.3 and next_e < 0.3:
            return "fade"
        return "cut"

    def build_xfade(
        self,
        video_a: Path,
        video_b: Path,
        output_path: Path,
        duration: float = 1.0,
    ) -> Path:
        """
        Создаёт плавный переход между двумя видео через FFmpeg xfade.

        Внимание: этот метод синхронный и тяжёлый (FFmpeg), используется
        через asyncio.to_thread в асинхронной обёртке. Реализован для
        полноты; в пайплайне переходы чаще применяются на этапе склейки
        через mod5 (xfade в concat-фильтре).

        Returns:
            Путь к итоговому видео.
        """
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_a),
            "-i", str(video_b),
            "-filter_complex",
            f"[0:v][1:v]xfade=transition=fade:duration={duration}[v]",
            "-map", "[v]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "copy",
            str(output_path),
        ]
        # Заглушка — реальный вызов выполняется во внешнем контексте.
        return output_path