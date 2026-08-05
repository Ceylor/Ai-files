"""
Модуль 3: AI-подбор музыки на основе выученного профиля стиля
Ищет треки, совпадающие по BPM, Энергии и тональности Camelot
"""
import json
import os
import random
from pathlib import Path
from typing import Dict, List, Optional
import httpx
from src.utils.logger import ws_manager

class MusicAI:
    """AI-подбор и обработка музыки"""
    
    def __init__(self, music_dir: Path, config: Dict, style_profile: Dict):
        self.music_dir = music_dir
        self.config = config
        self.profile = style_profile
        self.music_cache = []
        self.used_tracks = set()  # Отслеживаем использованные треки
    
    async def load_music_library(self):
        """Загружает метаданные всей локальной музыкальной библиотеки"""
        await ws_manager.broadcast("📚 Загрузка и анализ музыкальной библиотеки...")
        self.music_cache = []
        
        # Ищем все аудиофайлы
        mp3_files = list(self.music_dir.glob("*.mp3"))
        wav_files = list(self.music_dir.glob("*.wav"))
        all_audio = mp3_files + wav_files
        
        # Ищем все JSON с метаданными (созданные auto_tagger.py)
        json_files = list(self.music_dir.glob("*.mp3.json")) + \
                    list(self.music_dir.glob("*.wav.json"))
        
        # Если метаданных меньше чем аудиофайлов — запускаем авто-теггер
        if len(json_files) < len(all_audio):
            missing = len(all_audio) - len(json_files)
            await ws_manager.broadcast(f"  ⚠️  Метаданные отсутствуют для {missing} треков, запускаю авто-теггер...")
            from src.utils.auto_tagger import analyze_music_library
            await analyze_music_library(str(self.music_dir))
            # Перезагружаем список JSON
            json_files = list(self.music_dir.glob("*.mp3.json")) + \
                        list(self.music_dir.glob("*.wav.json"))
        
        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    metadata["full_path"] = str(json_file.with_suffix(""))
                    self.music_cache.append(metadata)
            except Exception:
                pass # Пропускаем битые файлы
        
        await ws_manager.broadcast(f"  ✅ Загружено {len(self.music_cache)} треков с метаданными")
    
    async def find_perfect_track(self, target_duration: float = 45) -> Optional[Dict]:
        """
        Находит трек, идеально подходящий под выученный профиль стиля
        Важно: выбирает РАЗНЫЕ треки для разных клипов (не повторяется)
        
        Returns:
            Metadata лучшего трека или None
        """
        target_bpm = self.profile.get("target_bpm", 120)
        bpm_range = self.profile.get("bpm_range", [100, 140])
        target_energy = self.profile.get("target_energy_percent", 70)
        preferred_camelot = self.profile.get("preferred_camelot", "Any")
        editing_rule = self.profile.get("editing_rule", "balanced")
        
        await ws_manager.broadcast(f"🎵 Поиск идеального трека для правила: '{editing_rule}'")
        await ws_manager.broadcast(f"   Цели: BPM {bpm_range[0]}-{bpm_range[1]}, Энергия ~{target_energy}%, Camelot: {preferred_camelot}")
        
        # 1. Ищем в локальной библиотеке (исключая уже использованные)
        matches = self._score_local_tracks(bpm_range, target_energy, preferred_camelot, target_duration)
        
        # Фильтруем уже использованные треки
        available_matches = [m for m in matches if m.get('full_path') not in self.used_tracks]
        
        if available_matches:
            best_match = available_matches[0]
            track_name = Path(best_match['full_path']).name
            self.used_tracks.add(best_match['full_path'])
            await ws_manager.broadcast(f"  ✅ НАЙДЕН ТРЕК: {track_name} (Совпадение: {best_match['score']}%)")
            return best_match
        
        # Если все треки использованы — сбрасываем и начинаем сначала
        if matches:
            await ws_manager.broadcast("  ⚠️  Все треки использованы, начинаем цикл заново")
            self.used_tracks.clear()
            best_match = matches[0]
            track_name = Path(best_match['full_path']).name
            self.used_tracks.add(best_match['full_path'])
            await ws_manager.broadcast(f"  ✅ НАЙДЕН ТРЕК (цикл): {track_name} (Совпадение: {best_match['score']}%)")
            return best_match
        
        # 2. Fallback: если локально ничего не подошло, ищем в Pixabay
        if self.config["music"].get("source") in ["pixabay", "hybrid"]:
            await ws_manager.broadcast("  🔍 Локальная библиотека не подошла, ищу в Pixabay...")
            pixabay_match = await self._search_pixabay(target_bpm, target_duration)
            if pixabay_match:
                return pixabay_match
        
        # 3. Абсолютный fallback: случайный трек
        if self.music_cache:
            fallback = random.choice(self.music_cache)
            await ws_manager.broadcast(f"  ⚠️  Использую запасной вариант: {Path(fallback['full_path']).name}")
            return fallback
        
        await ws_manager.broadcast("  ❌ Музыка не найдена")
        return None
    
    def _score_local_tracks(self, bpm_range: List[float], target_energy: int, 
                            preferred_camelot: str, target_duration: float) -> List[Dict]:
        """Оценивает каждый трек по шкале от 0 до 100 на основе профиля стиля"""
        scored_tracks = []
        
        for track in self.music_cache:
            score = 0
            
            # 1. Оценка BPM (макс 40 баллов)
            track_bpm = track.get("bpm", 120)
            if bpm_range[0] <= track_bpm <= bpm_range[1]:
                score += 40
            elif abs(track_bpm - sum(bpm_range)/2) < 20:
                score += 20
                
            # 2. Оценка Энергии (макс 30 баллов)
            track_energy = track.get("energy_percent", 50)
            energy_diff = abs(track_energy - target_energy)
            if energy_diff < 15:
                score += 30
            elif energy_diff < 30:
                score += 15
                
            # 3. Оценка Тональности Camelot (макс 20 баллов) - для гармоничного сведения
            track_camelot = track.get("camelot", "Unknown")
            if preferred_camelot != "Any" and track_camelot == preferred_camelot:
                score += 20
            elif self._is_camelot_compatible(track_camelot, preferred_camelot):
                score += 10
                
            # 4. Оценка длительности (макс 10 баллов)
            track_duration = track.get("duration", 0)
            if track_duration >= target_duration:
                score += 10
                
            if score > 0:
                # 3.9 FIX: Создаём глубокую копию, чтобы не мутировать оригинал
                track_copy = dict(track)
                track_copy["score"] = score
                scored_tracks.append(track_copy)
        
        # Сортируем по убыванию очков
        scored_tracks.sort(key=lambda x: x["score"], reverse=True)
        return scored_tracks

    def _is_camelot_compatible(self, camelot1: str, camelot2: str) -> bool:
        """Проверяет гармоническую совместимость по колесу Camelot (упрощенно)"""
        if camelot1 == "Unknown" or camelot2 == "Unknown" or camelot2 == "Any":
            return False
        
        # Извлекаем число и букву (например, "8A" -> 8, "A")
        num1, let1 = int(camelot1[:-1]), camelot1[-1]
        num2, let2 = int(camelot2[:-1]), camelot2[-1]
        
        # Совместимы, если: одинаковые, соседние числа с той же буквой, или то же число с другой буквой (мажор/минор)
        return (num1 == num2) or (abs(num1 - num2) == 1 and let1 == let2) or (num1 == num2 and let1 != let2)

    async def _search_pixabay(self, target_bpm: float, duration: float) -> Optional[Dict]:
        """Поиск в Pixabay API с учетом целевого BPM"""
        try:
            api_key_env = self.config["music"]["pixabay"].get("api_key_env")
            if not api_key_env:
                return None
            api_key = os.environ.get(api_key_env)
            if not api_key:
                await ws_manager.broadcast(f"  ⚠️  Переменная окружения {api_key_env} не установлена")
                return None
            
            # Определяем тег на основе энергии из профиля
            energy = self.profile.get("target_energy_percent", 50)
            mood_tag = "energetic" if energy > 60 else "calm"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://pixabay.com/api/music/",
                    params={
                        "key": api_key,
                        "q": mood_tag,
                        "duration_min": int(duration // 60),
                        "duration_max": int(duration // 60) + 1
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("hits"):
                        return {
                            "title": data["hits"][0].get("title", "Pixabay Track"),
                            "audio_url": data["hits"][0].get("preview_url"),
                            "source": "pixabay",
                            "score": 50 # Условно средний балл
                        }
        except Exception:
            pass
        return None