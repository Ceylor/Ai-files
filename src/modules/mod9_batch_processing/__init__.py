"""
Модуль 9: МАССОВАЯ ОБРАБОТКА И КОМПОЗИЦИЯ (AI AutoClip Pro 2.0).

Возможности:
    - Загрузка папки с любым количеством видео;
    - Асинхронная очередь обработки (ingest → анализ → паттерны → монтаж → экспорт);
    - Группировка и композиция фрагментов по смыслу (CLIP-кластеризация);
    - Статусы обработки в БД.

Компоненты:
    composer.py  — ClipComposer: кластеризация CLIP + объединение в клипы.
    processor.py — BatchProcessor: асинхронная очередь пакетной обработки.
"""

from src.modules.mod9_batch_processing.composer import ClipComposer
from src.modules.mod9_batch_processing.processor import BatchProcessor

__all__ = [
    "ClipComposer",
    "BatchProcessor",
]