"""
Модуль 8: МНОГОСЛОЙНЫЙ АНАЛИЗ КОНТЕНТА (AI AutoClip Pro 2.0).

Слой-анализаторы:
    emotion_detector.py — эмоции лиц (DeepFace/fer);
    object_detector.py  — объекты (YOLO/ultralytics);
    motion_analyzer.py  — движение (optical flow, Farneback);
    golden_moments.py   — "золотые моменты" (интегральный скор);
    clip_embedder.py    — CLIP-эмбеддинги кадров;
    analyzer.py         — оркестратор MultiLayerAnalyzer.

Каждый анализатор имеет graceful fallback: если модель недоступна,
слой пропускается и не роняет общий анализ.

Публичный API:
    MultiLayerAnalyzer           — оркестратор полного анализа.
    analyze_video                — высокоуровневая функция анализа одного видео.
    EmotionalFrame, DetectedObject, MotionSample, GoldenMoment, ClipEmbedding — модели данных.
"""

from src.modules.mod8_analysis.analyzer import MultiLayerAnalyzer, analyze_video

__all__ = [
    "MultiLayerAnalyzer",
    "analyze_video",
]