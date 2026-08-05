"""
Загрузка и валидация конфигурации из YAML
"""
import yaml
import os
from pathlib import Path
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """
    Загружает конфигурацию из config.yaml
    
    Returns:
        Dict с конфигурацией
        
    Raises:
        FileNotFoundError: Если config.yaml не найден
        yaml.YAMLError: Если YAML некорректен
    """
    # Ищем config.yaml
    config_paths = [
        Path(__file__).parent.parent.parent / "configs" / "config.yaml",
        Path(__file__).parent / "config.yaml",
        Path("configs") / "config.yaml",
    ]
    
    config_file = None
    for path in config_paths:
        if path.exists():
            config_file = path
            break
    
    if not config_file:
        raise FileNotFoundError(
            "config.yaml не найден! Создайте файл в папке configs/"
        )
    
    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # Валидация обязательных полей
    required_sections = ["general", "ai_brain", "subtitles", "music", "editing"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"В config.yaml отсутствует секция: {section}")
    
    return config

def get_config_value(config: Dict, key_path: str, default=None):
    """
    Получает значение из config по пути (например, "ai_brain.ollama.model")
    """
    keys = key_path.split(".")
    value = config
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value