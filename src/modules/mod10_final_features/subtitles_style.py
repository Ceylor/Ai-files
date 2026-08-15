"""
Стилизованные субтитры с эмодзи и эффектами (ASS).

Добавляет эмодзи к субтитрам по контексту (😂 для смешных/весёлых,
🔥 для эпичных, 💪 для мотивирующих) и применяет стилизацию
(цвет, фон, тень, анимация появления) через ASS-формат.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("final.subtitles_style")

# Эмодзи по эмоциям/контексту.
EMOJI_MAP: Dict[str, str] = {
    "happy": "😂",
    "surprise": "😮",
    "sad": "😢",
    "angry": "😠",
    "fear": "😱",
    "neutral": "✨",
    "energetic": "🔥",
    "motivational": "💪",
}


class EmojiSubtitleStyler:
    """Стилизатор субтитров: эмодзи + ASS-стили."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.sub_config = self.config.get("subtitles", {})
        self.font_size = self.sub_config.get("font", {}).get("size", 52)
        self.font_color = self.sub_config.get("font", {}).get("color", "#FFFFFF")
        self.outline_color = self.sub_config.get("effects", {}).get(
            "shadow_color", "#000000"
        )
        self.outline_width = self.sub_config.get("effects", {}).get("outline_width", 3)

    def pick_emoji(self, analysis: Optional[Dict[str, Any]]) -> str:
        """Выбирает эмодзи по анализу сцены."""
        if not analysis:
            return EMOJI_MAP["neutral"]

        emotions = analysis.get("emotions", [])
        if emotions:
            emotion = emotions[0].get("emotion", "neutral")
            return EMOJI_MAP.get(emotion, EMOJI_MAP["neutral"])

        motion = analysis.get("motion", [])
        if motion:
            energy = sum(float(m.get("energy", 0)) for m in motion) / len(motion)
            if energy > 0.6:
                return EMOJI_MAP["energetic"]
        return EMOJI_MAP["neutral"]

    def _ass_style(self) -> str:
        """Стиль ASS для субтитров (заголовок секции Styles)."""
        # Цвета в ASS: &HAABBGGRR (alpha, blue, green, red).
        def _to_ass_color(hex_color: str) -> str:
            hex_color = hex_color.lstrip("#")
            if len(hex_color) != 6:
                return "FFFFFF"
            r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
            return f"&H00{b}{g}{r}"

        primary = _to_ass_color(self.font_color)
        outline = _to_ass_color(self.outline_color)

        return (
            "Style: Default,{font},1,{size},{primary},{outline},{outline},"
            "{outline},0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1".format(
                font="Montserrat", size=self.font_size,
                primary=primary, outline=outline,
            )
        )

    def build_ass(
        self,
        segments: List[Dict[str, Any]],
        output_path: Path,
        analyses: Optional[Dict[str, Any]] = None,
        duration: Optional[float] = None,
    ) -> Path:
        """
        Генерирует ASS-файл субтитров с эмодзи и стилями.

        Args:
            segments: список [{start, end, text}, ...].
            output_path: путь для .ass файла.
            analyses: анализ сцен (опционально, для эмодзи).
            duration: длительность видео (для мэппинга, необязательно).

        Returns:
            Путь к .ass файлу.
        """
        style = self._ass_style()
        lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "",
            "[V4+ Styles]",
            style,
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]

        for i, seg in enumerate(segments):
            start = float(seg.get("start", 0))
            end = float(seg.get("end", start + 2))
            text = str(seg.get("text", ""))

            # Эмодзи по анализу (если есть).
            emoji = self.pick_emoji(analyses) if analyses else EMOJI_MAP["neutral"]

            # Формат времени ASS: H:MM:SS.cc
            def _fmt(t):
                h = int(t // 3600)
                m = int((t % 3600) // 60)
                s = int(t % 60)
                cs = int((t - int(t)) * 100)
                return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

            text_clean = text.replace("\n", "\\N")
            # Стилизация: цвет текста + эмодзи в начале.
            styled = f"{emoji} {text_clean}"

            lines.append(
                f"Dialogue: 0,{_fmt(start)},{_fmt(end)},Default,,0,0,0,,{styled}"
            )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("ASS-субтитры сохранены: %s (%d строк)", output_path, len(segments))
        return output_path