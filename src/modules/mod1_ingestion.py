"""
Модуль 1: Ингестия видео
- Скачивание через yt-dlp (если ссылка)
- Извлечение аудио
- Транскрибация через faster-whisper
- Детекция сцен через PySceneDetect
"""
import asyncio
from pathlib import Path
from typing import Dict, List, Any
from src.utils.logger import ws_manager

class VideoIngestion:
    """Класс для загрузки и предварительной обработки видео"""
    
    # Кэш модели Whisper (загружается один раз)
    _whisper_model = None
    
    def __init__(self, temp_dir: Path, whisper_model: str = "small", 
                 whisper_device: str = "cpu", whisper_compute_type: str = "int8"):
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        # 3.6 FIX: параметры Whisper теперь настраиваемые (device может быть "cuda")
        self.whisper_model_name = whisper_model
        self.whisper_device = whisper_device
        self.whisper_compute_type = whisper_compute_type
    
    async def process_video(self, video_path: Path) -> Dict[str, Any]:
        """
        Обрабатывает видеофайл: извлекает аудио, транскрибирует, детектирует сцены
        
        Args:
            video_path: Путь к видеофайлу
            
        Returns:
            Dict с результатами обработки
        """
        await ws_manager.broadcast(f"📹 Обработка: {video_path.name}")
        
        result = {
            "path": str(video_path),
            "audio_path": None,
            "transcript": [],
            "scenes": [],
            "duration": 0
        }
        
        try:
            # Шаг 1: Извлечение аудио
            await ws_manager.broadcast(f"   🎵 Извлечение аудио...")
            audio_path = await self._extract_audio(video_path)
            result["audio_path"] = str(audio_path)
            
            # Шаг 2: Получение длительности
            result["duration"] = await self._get_duration(video_path)
            
            # Шаг 3: Транскрибация (Whisper)
            await ws_manager.broadcast(f"   ️ Распознавание речи (Whisper)...")
            result["transcript"] = await self._transcribe_audio(audio_path)
            
            # Шаг 4: Детекция сцен
            await ws_manager.broadcast(f"   ✂️ Детекция сцен...")
            result["scenes"] = await self._detect_scenes(video_path)
            
            await ws_manager.broadcast(f"   ✅ Обработка завершена")
            
        except Exception as e:
            await ws_manager.broadcast(f"   ❌ Ошибка: {e}")
            raise
        
        return result
    
    async def _extract_audio(self, video_path: Path) -> Path:
        """Извлекает аудио из видео через FFmpeg"""
        audio_path = self.temp_dir / f"{video_path.stem}.wav"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vn",  # Без видео
            "-acodec", "pcm_s16le",  # PCM 16-bit
            "-ar", "16000",  # 16kHz для Whisper
            "-ac", "1",  # Mono
            str(audio_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr.decode()}")
        
        return audio_path
    
    async def _get_duration(self, video_path: Path) -> float:
        """Получает длительность видео через ffprobe"""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return float(stdout.decode().strip())
        else:
            return 0.0
    
    async def _transcribe_audio(self, audio_path: Path) -> List[Dict]:
        """
        Транскрибирует аудио через faster-whisper с улучшенными настройками
        """
        try:
            from faster_whisper import WhisperModel
            import re
            
            # Загружаем модель один раз и кэшируем (small для баланса скорости/качества)
            if VideoIngestion._whisper_model is None:
                await ws_manager.broadcast("   📦 Загрузка модели Whisper (small)...")
                VideoIngestion._whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
            
            model = VideoIngestion._whisper_model
            
            # УЛУЧШЕННАЯ транскрипция с VAD и лучшими параметрами
            # ВАЖНО: не передаём initial_prompt — он влезает в текст транскрипции!
            segments, info = model.transcribe(
                str(audio_path),
                beam_size=7,
                language="ru",  # Язык явно указываем (не None!)
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                ),
                word_timestamps=True,  # A5: включаем пословные таймкоды
            )
            
            transcript = []
            for segment in segments:
                # Очищаем текст от лишних пробелов и символов
                text = segment.text.strip()
                text = re.sub(r'\s+', ' ', text)
                
                # УДАЛЯЕМ системные подсказки из текста (если Whisper их вставил)
                text = re.sub(r'Продолжай\s+транскрибировать\s+речь\s+на\s+русском\s+языке\.', '', text, flags=re.IGNORECASE).strip()
                text = re.sub(r'Continue\s+transcribing\s+speech\s+in\s+Russian\.', '', text, flags=re.IGNORECASE).strip()
                
                if text:  # Только непустые сегменты
                    transcript.append({
                        "start": segment.start,
                        "end": segment.end,
                        "text": text,
                        "words": [{"start": w.start, "end": w.end, "word": w.word} 
                                 for w in segment.words] if segment.words else []
                    })
            
            # ДОПОЛНИТЕЛЬНАЯ ПОСТ-ОБРАБОТКА: объединяем короткие сегменты
            transcript = self._post_process_transcript(transcript)
            
            return transcript
            
        except ImportError:
            await ws_manager.broadcast("   ⚠️  faster-whisper не установлен, пропускаем транскрибацию")
            return []
        except Exception as e:
            await ws_manager.broadcast(f"   ⚠️  Ошибка транскрибации: {e}")
            return []
    
    def _post_process_transcript(self, transcript: List[Dict]) -> List[Dict]:
        """
        Пост-обработка транскрипции:
        - Объединяем короткие сегменты (< 0.5s) со следующими
        - Убираем дубликаты
        - Очищаем текст от мусора
        """
        import re
        
        if not transcript:
            return []
        
        # Объединяем короткие сегменты
        merged = [transcript[0]]
        for seg in transcript[1:]:
            prev = merged[-1]
            # Если сегмент очень короткий (< 0.5s) и следующий идет сразу
            if (seg["end"] - seg["start"] < 0.5 and 
                abs(seg["start"] - prev["end"]) < 0.2):
                # Объединяем с предыдущим
                prev["text"] = f"{prev['text']} {seg['text']}".strip()
                prev["end"] = seg["end"]
            else:
                merged.append(seg)
        
        # Очищаем текст от мусора
        cleaned = []
        for seg in merged:
            text = seg["text"].strip()
            # Убираем повторяющиеся слова (A4: исправлен regex)
            # Было: r'\b(\w+)(\s+\1)\b' → r'\1\2' (ломалось)
            # Стало: убираем повторы слов типа "а а а"
            text = re.sub(r'(\b\w+\b)(\s+\1)+', r'\1', text, flags=re.IGNORECASE)
            # Убираем слова-паразиты (B3)
            filler_words = r'\b(ээ|эм|м|ну|типа|короче|значит|как бы|в общем|собственно|допустим)\b'
            text = re.sub(filler_words, '', text, flags=re.IGNORECASE).strip()
            # Убираем лишние пробелы
            text = re.sub(r'\s+', ' ', text)
            
            # B2: Фильтр галлюцинаций Whisper
            # Убираем паттерны типа "Продолжай транскрибировать", "Спасибо за просмотр"
            hallucination_patterns = [
                r'продолжай\s+транскрибировать',
                r'спасибо\s+за\s+просмотр',
                r'подписывайтесь\s+на\s+канал',
                r'не\s+забывай\s+ставить\s+лайк',
                r'\b(а\s+){3,}\b',  # "а а а"
                r'\b(ээ)\b',  # "ээ"
            ]
            for pattern in hallucination_patterns:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
            
            if text and len(text) > 2:  # Только осмысленные сегменты
                cleaned.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": text,
                    "words": seg.get("words", [])
                })
        
        return cleaned
    
    async def _detect_scenes(self, video_path: Path) -> List[Dict]:
        """
        Детектирует сцены через PySceneDetect
        
        Returns:
            Список сцен с таймкодами
        """
        try:
            from scenedetect import detect, ContentDetector
            
            scene_list = detect(
                str(video_path),
                ContentDetector(),
                start_in_scene=True
            )
            
            scenes = []
            for i, scene in enumerate(scene_list):
                scenes.append({
                    "index": i,
                    "start_time": scene[0],
                    "end_time": scene[1]
                })
            
            return scenes if scenes else [{"index": 0, "start_time": 0, "end_time": 0}]
            
        except ImportError:
            await ws_manager.broadcast("   ⚠️  PySceneDetect не установлен")
            return []
        except Exception as e:
            await ws_manager.broadcast(f"   ⚠️  Ошибка детекции сцен: {e}")
            return []

async def ingest_video_batch(video_files: List[Path], temp_dir: Path) -> List[Dict]:
    """
    Обрабатывает пакет видеофайлов
    
    Args:
        video_files: Список путей к видео
        temp_dir: Папка для временных файлов
        
    Returns:
        Список результатов обработки
    """
    ingestion = VideoIngestion(temp_dir)
    results = []
    
    for i, video_file in enumerate(video_files, 1):
        await ws_manager.broadcast(f"Обработка видео {i}/{len(video_files)}")
        
        try:
            result = await ingestion.process_video(video_file)
            results.append(result)
        except Exception as e:
            await ws_manager.broadcast(f" Пропущен файл {video_file.name}: {e}")
            continue
        
        # Небольшая пауза между файлами
        await asyncio.sleep(0.5)
    
    return results