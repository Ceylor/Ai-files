"""
Модуль 10: Финальные фичи (пункт 7 ТЗ)
- Авто-цветокоррекция на основе анализа сцен (mod8_analysis);
- Умные переходы (morphing/fade/zoom/spin) по контексту;
- Субтитры с эмодзи и стилизацией;
- Экспорт в разных качествах (HD/FHD/4K) и пресетах (TikTok/Shorts/Reels).
"""
from src.modules.mod10_final_features.color_grade import ColorGrader
from src.modules.mod10_final_features.transitions import TransitionEngine
from src.modules.mod10_final_features.subtitles_style import EmojiSubtitleStyler
from src.modules.mod10_final_features.export_profiles import ExportProfiles

__all__ = [
    "ColorGrader",
    "TransitionEngine",
    "EmojiSubtitleStyler",
    "ExportProfiles",
]