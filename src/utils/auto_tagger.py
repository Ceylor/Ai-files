"""
Автоматический анализ музыки и создание JSON-метаданных
Использует librosa для анализа BPM, энергии, тональности
"""
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import librosa
import numpy as np
from src.utils.logger import ws_manager

async def analyze_music_file(audio_path: Path) -> Optional[Dict[str, Any]]:
    """
    Анализирует аудиофайл и извлекает метаданные
    
    Args:
        audio_path: Путь к аудиофайлу
        
    Returns:
        Dict с метаданными или None если ошибка
    """
    try:
        await ws_manager.broadcast(f"🎵 Анализ трека: {audio_path.name}")
        
        # Загружаем аудио (только первые 30 сек для скорости)
        y, sr = librosa.load(str(audio_path), duration=30, sr=None)
        
# Анализ BPM
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        # В новых версиях librosa tempo может быть numpy array — конвертируем
        bpm = float(tempo.item() if hasattr(tempo, 'item') else tempo)
        
# Анализ энергии (RMS)
        rms = librosa.feature.rms(y=y)[0]
        energy_normalized = float(np.mean(rms) / np.max(rms)) if np.max(rms) > 0 else 0
        
        # Спектральный центроид (яркость/тональность)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        avg_centroid = float(np.mean(spectral_centroid))
        
        # Определение настроения на основе метрик
        mood = detect_mood(bpm, energy_normalized, avg_centroid)
        
        # Поиск дропов (резких изменений энергии)
        drops = find_drops(rms, sr=sr)
        
        metadata = {
            "file": audio_path.name,
            "bpm": round(bpm, 1),
            "energy": round(energy_normalized, 3),
            "spectral_centroid": round(avg_centroid, 1),
            "mood": mood,
            "drops": drops,
            "beat_times_sec": [round(float(t), 2) for t in librosa.frames_to_time(beat_frames, sr=sr)],
            "drop_times_sec": drops,
            "duration": round(librosa.get_duration(y=y, sr=sr), 2)
        }
        
        # Сохраняем JSON рядом с файлом
        json_path = audio_path.with_suffix(audio_path.suffix + ".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        await ws_manager.broadcast(f"   ✅ BPM: {bpm:.1f}, Настроение: {', '.join(mood)}")
        
        return metadata
        
    except Exception as e:
        await ws_manager.broadcast(f"   ❌ Ошибка анализа {audio_path.name}: {e}")
        return None

def detect_mood(bpm: float, energy: float, centroid: float) -> list:
    """
    Определяет настроение трека на основе метрик
    
    Returns:
        Список тегов настроения
    """
    mood = []
    
    # По BPM
    if bpm < 80:
        mood.append("slow")
        mood.append("calm")
    elif bpm < 120:
        mood.append("medium")
    else:
        mood.append("fast")
        mood.append("energetic")
    
    # По энергии
    if energy > 0.6:
        mood.append("high_energy")
        mood.append("dynamic")
    elif energy < 0.3:
        mood.append("low_energy")
        mood.append("relaxed")
    
    # По тональности
    if centroid > 3000:
        mood.append("bright")
    elif centroid < 1500:
        mood.append("dark")
    
    return mood if mood else ["neutral"]

def find_drops(rms: np.ndarray, sr: int = 22050, threshold: float = 0.8) -> list:
    """
    Находит моменты резкого изменения энергии (дропы)
    
    Args:
        rms: RMS energy array
        sr: Sample rate (для корректного преобразования фреймов в секунды)
        threshold: Порог для определения пиков
    
    Returns:
        Список временных меток дропов (в секундах)
    """
    drops = []
    
    # Нормализуем
    rms_normalized = rms / np.max(rms) if np.max(rms) > 0 else rms
    
    # Ищем резкие спады после пиков
    peak_indices = []
    for i in range(1, len(rms_normalized) - 1):
        if (rms_normalized[i] > rms_normalized[i-1] and 
            rms_normalized[i] > rms_normalized[i+1] and
            rms_normalized[i] > threshold):
            peak_indices.append(i)
    
    # Корректное преобразование фреймов в секунды через librosa
    if peak_indices:
        drop_times = librosa.frames_to_time(peak_indices, sr=sr, hop_length=512)
        drops = [round(float(t), 2) for t in drop_times]
    
    return drops[:3]  # Возвращаем первые 3 дропа

async def analyze_music_library(music_dir: str):
    """
    Анализирует всю музыкальную библиотеку
    
    Args:
        music_dir: Путь к папке с музыкой
    """
    music_path = Path(music_dir)
    
    # Находим все аудиофайлы
    audio_extensions = ["*.mp3", "*.wav", "*.ogg", "*.flac", "*.m4a"]
    audio_files = []
    
    for ext in audio_extensions:
        audio_files.extend(music_path.glob(ext))
    
    if not audio_files:
        await ws_manager.broadcast(" Музыкальная библиотека пуста")
        return
    
    await ws_manager.broadcast(f" Анализ музыкальной библиотеки ({len(audio_files)} треков)")
    
    # Анализируем каждый файл
    for i, audio_file in enumerate(audio_files, 1):
        # Проверяем, есть ли уже JSON
        json_path = audio_file.with_suffix(audio_file.suffix + ".json")
        
        if json_path.exists():
            await ws_manager.broadcast(f"   ️  Пропущен (уже есть метаданные): {audio_file.name}")
            continue
        
        await analyze_music_file(audio_file)
        await asyncio.sleep(0.1)  # Небольшая пауза
    
    await ws_manager.broadcast("✅ Анализ музыкальной библиотеки завершен")