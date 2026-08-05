"""
Аудио-анализатор уровня Timbrica
Извлекает точную сетку битов (Beat Grid), пики энергии (Drops), BPM и тональность (Camelot)
Оптимизирован для CPU, не нагружает GPU.
"""
import librosa
import numpy as np
from pathlib import Path
from typing import Dict, Any

def analyze_audio_track(audio_path: Path, duration_limit: float = 60.0) -> Dict[str, Any]:
    """
    Глубокий анализ аудиофайла
    
    Args:
        audio_path: Путь к аудио или видеофайлу (librosa извлечет аудио)
        duration_limit: Анализируем первые N секунд (60 сек достаточно для выявления паттерна)
        
    Returns:
        Словарь с продвинутыми метриками
    """
    try:
        # 1. Загрузка аудио (22050 Гц - золотой стандарт для анализа темпа, быстро и точно)
        y, sr = librosa.load(str(audio_path), sr=22050, duration=duration_limit)
        
# 2. BPM и СЕТКА БИТОВ (Самое важное для монтажа!)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        # В новых версиях librosa tempo может быть numpy array — конвертируем
        bpm = float(tempo.item() if hasattr(tempo, 'item') else tempo)
        
        # Конвертируем фреймы битов в секунды
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
        
# 3. Анализ энергии и поиск "Дропов" (Piks)
        # Вычисляем силу начала звука (onset strength) по времени
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        
        # Находим локальные максимумы (пики энергии)
        # Сравниваем с медианным значением + стандартное отклонение
        threshold = np.median(onset_env) + 0.5 * np.std(onset_env)
        peak_indices = np.where(onset_env > threshold)[0]
        drop_times = librosa.frames_to_time(peak_indices, sr=sr).tolist()
        
        # Общая энергия трека (RMS)
        rms = librosa.feature.rms(y=y)[0]
        energy_percent = int((np.mean(rms) / np.max(rms)) * 100) if np.max(rms) > 0 else 0
        
        # 4. Танцевальность (регулярность ритма)
        pulse = librosa.beat.plp(onset_envelope=onset_env, sr=sr)
        danceability = float(np.mean(pulse)) * 100
        
        # 5. Тональность и Camelot (Эвристика на основе хромаграммы)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        dominant_note_idx = int(np.argmax(np.mean(chroma, axis=1)))
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        key_name = notes[dominant_note_idx]
        
        # Простое определение мажор/минор
        is_minor = np.mean(chroma[3]) > np.mean(chroma[4])
        full_key = f"{key_name} {'Minor' if is_minor else 'Major'}"
        
        camelot_map = {
            # Мажор (B)
            "C Major": "8B", "C# Major": "3B", "Db Major": "3B",
            "D Major": "10B", "D# Major": "5B", "Eb Major": "5B",
            "E Major": "12B", "F Major": "7B", "F# Major": "2B", "Gb Major": "2B",
            "G Major": "9B", "G# Major": "4B", "Ab Major": "4B",
            "A Major": "11B", "A# Major": "6B", "Bb Major": "6B",
            "B Major": "1B",
            # Минор (A)
            "A Minor": "8A", "A# Minor": "3A", "Bb Minor": "3A",
            "B Minor": "10A", "C Minor": "5A", "C# Minor": "12A",
            "Db Minor": "12A", "D Minor": "6A", "D# Minor": "2A", "Eb Minor": "2A",
            "E Minor": "9A", "F Minor": "4A", "F# Minor": "11A",
            "Gb Minor": "11A", "G Minor": "6A", "G# Minor": "1A", "Ab Minor": "1A",
        }
        camelot = camelot_map.get(full_key, "Unknown")

        return {
            "success": True,
            "bpm": round(bpm, 1),
            "key": full_key,
            "camelot": camelot,
            "energy_percent": energy_percent,
            "danceability": round(danceability, 1),
            "beat_times_sec": beat_times[:200],  # Сохраняем биты для монтажа
            "drop_times_sec": drop_times[:20],  # Сохраняем первые 20 пиков энергии
            "duration_analyzed": round(duration_limit, 1)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "bpm": 120.0,
            "energy_percent": 50,
            "camelot": "Unknown",
            "beat_times_sec": [],
            "drop_times_sec": []
        }