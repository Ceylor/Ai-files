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
from src.utils.gpu_detector import gpu

class VideoIngestion:
    """Класс для загрузки и предварительной обработки видео"""
    
    # Кэш модели Whisper (загружается один раз)
    _whisper_model = None
    _whisper_device_used: str | None = None
    
    def __init__(self, temp_dir: Path, whisper_model: str = "small", 
                 whisper_device: str | None = None, whisper_compute_type: str | None = None):
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.whisper_model_name = whisper_model
        # Auto-detect GPU/CPU if not explicitly specified
        self.whisper_device = whisper_device or gpu.get_whisper_device()
        self.whisper_compute_type = whisper_compute_type or gpu.get_whisper_compute_type()
    
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
            
            # Шаг 3: VAD-trimming тишины перед транскрибацией (экономит время/память).
            await ws_manager.broadcast(f"   🗣️ VAD-фильтр тишины...")
            trimmed_audio, time_offset = await self._trim_silence(audio_path)
            result["audio_path"] = str(trimmed_audio) if trimmed_audio else str(audio_path)
            
            # Шаг 3: Транскрибация (Whisper)
            await ws_manager.broadcast(f"   ️ Распознавание речи (Whisper)...")
            effective_audio = trimmed_audio if trimmed_audio else audio_path
            result["transcript"] = await self._transcribe_audio(effective_audio, time_offset=time_offset)
            
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
    
    async def _trim_silence(self, audio_path: Path) -> tuple:
        """
        Обнаруживает речевые сегменты и обрезает длинную тишину,
        чтобы уменьшить объём данных, передаваемых в Whisper.

        Returns:
            (trimmed_audio_path_or_None, time_offset_sec)
            Если тишины не найдено или обработка не удалась — (None, 0.0).
        """
        try:
            import librosa
            import numpy as np
            import soundfile as sf

            # Загружаем моно-аудио (уже 16kHz, mono после FFmpeg).
            y, sr = librosa.load(str(audio_path), sr=None)
            if len(y) == 0:
                return None, 0.0

            # Обнаружение речи по энергии (split возвращает интервалы [start, end] в сэмплах).
            intervals = librosa.effects.split(
                y,
                top_db=30,          # порог тишины, дБ
                frame_length=2048,  # Берём достаточно длинное окно,
                hop_length=512,     # чтобы не резать по коротким паузам в речи.
            )

            if len(intervals) == 0:
                return None, 0.0

            # Определяем начальный сэмпл (начало первой речи).
            start_sample = int(intervals[0, 0])
            # Оставляем небольшой отступ перед речью (примерно 50 мс), чтобы не срезать начало слова.
            start_sample = max(0, start_sample - int(0.05 * sr))

            # Если тишина в начале незначительна (< 0.3с) — не обрезаем.
            if start_sample < 0.3 * sr:
                return None, 0.0

            trimmed = y[start_sample:]
            out_path = audio_path.with_name(f"{audio_path.stem}_vad.wav")
            sf.write(str(out_path), trimmed, sr)

            time_offset = start_sample / sr
            saved_sec = start_sample / sr
            await ws_manager.broadcast(
                f"   ✂️ VAD: обрезано тишины в начале {saved_sec:.1f}с"
            )
            return out_path, time_offset
        except Exception as exc:  # noqa: BLE001
            await ws_manager.broadcast(f"   ⚠️  VAD-trimming пропущен: {exc}")
            return None, 0.0

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
    
    async def _transcribe_audio(self, audio_path: Path, time_offset: float = 0.0) -> List[Dict]:
        """
        Транскрибирует аудио через faster-whisper с улучшенными настройками.

        Args:
            audio_path: путь к WAV-файлу (возможно, уже обрезанному VAD).
            time_offset: смещение в сек, добавленное при VAD-trimming; прибавляется
                к таймкодам сегментов, чтобы вернуть их в исходную шкалу времени.
        """
        try:
            from faster_whisper import WhisperModel
            import re
            
            # Загружаем модель один раз и кэшируем.
            # If device changed (e.g. first run had no GPU, now has one), reload.
            if (VideoIngestion._whisper_model is None 
                    or VideoIngestion._whisper_device_used != self.whisper_device):
                device_label = "GPU" if self.whisper_device == "cuda" else "CPU"
                await ws_manager.broadcast(
                    f"   📦 Загрузка модели Whisper ({self.whisper_model_name}, {device_label}, {self.whisper_compute_type})..."
                )
                # Free old model if device changed
                if VideoIngestion._whisper_model is not None:
                    del VideoIngestion._whisper_model
                    VideoIngestion._whisper_model = None
                VideoIngestion._whisper_model = WhisperModel(
                    self.whisper_model_name,
                    device=self.whisper_device,
                    compute_type=self.whisper_compute_type,
                )
                VideoIngestion._whisper_device_used = self.whisper_device
            
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
                        "start": round(segment.start + time_offset, 3),
                        "end": round(segment.end + time_offset, 3),
                        "text": text,
                        "words": [{"start": round(w.start + time_offset, 3),
                                  "end": round(w.end + time_offset, 3),
                                  "word": w.word}
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