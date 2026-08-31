"""
Общее состояние API-приложения: пути, глобальные объекты (learning_engine,
batch_processor), limiter. Разделяется между роутерами.
"""
from __future__ import annotations

import os
from pathlib import Path

from slowapi import Limiter
from slowapi.util import get_remote_address

from src.utils.logger import ws_manager, batch_ws_manager
from src.modules.mod7_learning.learner import LearningEngine
from src.modules.mod8_analysis.analyzer import MultiLayerAnalyzer
from src.modules.mod9_batch_processing.processor import BatchProcessor

# Максимальный размер загружаемого файла (по умолчанию 2 ГБ).
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(2 * 1024 * 1024 * 1024)))

BASE_DIR = Path(__file__).resolve().parent.parent.parent
WEB_UI_DIR = BASE_DIR / "web_ui"
DATA_DIR = BASE_DIR / "data"
REF_DIR = DATA_DIR / "reference_clips"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
LEARNING_STORE_DIR = DATA_DIR / "learning_store"
BATCH_OUTPUT_DIR = OUTPUT_DIR / "batch"
DOWNLOAD_DIR = DATA_DIR / "downloads"

# Движок самообучения (непрерывное накопление паттернов).
learning_engine = LearningEngine(LEARNING_STORE_DIR)

# Анализатор многослойного контента.
analyzer = MultiLayerAnalyzer()

# Оркестратор пакетной обработки (mod9).
batch_processor = BatchProcessor(
    work_dir=DATA_DIR / "batch_work",
    output_dir=BATCH_OUTPUT_DIR,
)

# Rate limiter (общий для всех роутеров).
limiter = Limiter(key_func=get_remote_address)
