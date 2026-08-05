"""
AI-модуль для анализа и группировки видео в логические клипы
Использует локальную LLM (Qwen 2.5 3B через Ollama) или облачный GigaChat
"""
import asyncio
import json
import re
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.core.config_loader import load_config
from src.utils.logger import ws_manager
from src.utils.gigachat_client import GigaChatClient

async def get_video_metadata(video_path: Path) -> Dict[str, Any]:
    """
    Извлекает метаданные видео через ffprobe
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video_path)
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()

        if process.returncode == 0:
            data = json.loads(stdout.decode().strip())
            streams = data.get("streams", [])
            fmt = data.get("format", {})
            stream = streams[0] if streams else {}
            
            # Проверяем наличие аудиопотока
            audio_cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=codec_type",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path)
            ]
            audio_proc = await asyncio.create_subprocess_exec(
                *audio_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            audio_stdout, _ = await audio_proc.communicate()
            has_audio = audio_proc.returncode == 0 and audio_stdout.decode().strip() == "audio"
            
            return {
                "filename": video_path.name,
                "duration": float(fmt.get("duration", 0)),
                "has_audio": has_audio,
                "resolution": [int(stream.get("width", 0)), int(stream.get("height", 0))]
            }
    except Exception:
        pass

    return {
        "filename": video_path.name,
        "duration": 0,
        "has_audio": False,
        "resolution": [0, 0]
    }

async def _quick_scene_count(video_path: Path) -> int:
    """Быстрый подсчёт количества сцен через FFmpeg scene detection"""
    try:
        cmd = [
            "ffmpeg", "-i", str(video_path),
            "-filter:v", "select='gt(scene,0.3)',showinfo",
            "-f", "null", "-"
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
)
        _, stderr = await process.communicate()
        # Считаем количество строк showinfo = количество смен сцены
        matches = re.findall(r"pts_time:", stderr.decode(errors="ignore"))
        return len(matches) + 1  # +1 потому что первая сцена не детектируется как смена
    except Exception:
        return 1


async def cluster_videos(input_dir: str) -> List[Dict[str, Any]]:
    """
    Анализирует все видео в папке и группирует их в логические клипы
    Собирает полные метаданные для построения нарратива
    """
    config = load_config()
    input_path = Path(input_dir)
    
    video_files = list(input_path.glob("*.mp4")) + \
                  list(input_path.glob("*.mov")) + \
                  list(input_path.glob("*.avi"))
    
    if not video_files:
        await ws_manager.broadcast("⚠️  Видеофайлы не найдены")
        return []
    
    await ws_manager.broadcast(f" Найдено {len(video_files)} видеофайлов для анализа")
    
    videos_info = []
    for i, video_file in enumerate(video_files, 1):
        await ws_manager.broadcast(f"   📹 Анализ файла {i}/{len(video_files)}: {video_file.name}")
        
        metadata = await get_video_metadata(video_file)
        metadata["path"] = str(video_file)
        metadata["index"] = i
        
        # Быстрая оценка количества сцен через FFmpeg scene detection
        scene_count = await _quick_scene_count(video_file)
        metadata["scenes"] = scene_count
        
        # Извлекаем аудио для анализа энергии
        audio_path = None
        try:
            audio_path = input_path / f"{video_file.stem}_audio.wav"
            audio_cmd = [
                "ffmpeg", "-y",
                "-i", str(video_file),
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                str(audio_path)
            ]
            audio_proc = await asyncio.create_subprocess_exec(
                *audio_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await audio_proc.communicate()
        except Exception:
            pass
        
        # Анализ аудиоэнергии
        if audio_path and audio_path.exists():
            try:
                energy_cmd = [
                    "ffmpeg", "-i", str(audio_path),
                    "-af", "volumedetect",
                    "-f", "null", "-"
                ]
                energy_proc = await asyncio.create_subprocess_exec(
                    *energy_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await energy_proc.communicate()
                # Парсим максимальную громкость
                match = re.search(r'max_volume:\s+([+-]?\d+\.?\d*)\s*dB', stderr.decode(errors="ignore"))
                if match:
                    metadata["audio_energy"] = float(match.group(1))
                else:
                    metadata["audio_energy"] = 0.0
            except Exception:
                metadata["audio_energy"] = 0.0
            finally:
                if audio_path.exists():
                    audio_path.unlink()
        else:
            metadata["audio_energy"] = 0.0
        
        # A6 FIX: Quick транскрипция для LLM (tiny модель — быстро, достаточно для кластеризации)
        try:
            from faster_whisper import WhisperModel
            if not hasattr(cluster_videos, '_tiny_model'):
                cluster_videos._tiny_model = WhisperModel("tiny", device="cpu", compute_type="int8")
            model = cluster_videos._tiny_model
            segments, _ = model.transcribe(str(audio_path) if audio_path and audio_path.exists() else str(video_file),
                                          beam_size=3, language="ru", vad_filter=True)
            transcript_text = " ".join(seg.text.strip() for seg in segments if seg.text.strip())
            metadata["transcript"] = transcript_text[:500]  # Ограничиваем длину
        except Exception:
            metadata["transcript"] = ""
        
        metadata["mood"] = "unknown"
        metadata["content_value"] = "normal"  # normal, highlight, filler
        metadata["visual_quality"] = 80  # Заглушка, будет улучшено
        
        videos_info.append(metadata)
    
    prompt = create_clustering_prompt(videos_info)
    provider = config["ai_brain"].get("primary_provider", "ollama")
    clusters: Optional[List[Dict[str, Any]]] = None
    
    if provider == "ollama":
        try:
            await ws_manager.broadcast("🧠 Отправка в локальную LLM (Ollama)...")
            clusters = await send_to_ollama(prompt, config)
            if clusters:
                await ws_manager.broadcast(f"✅ Ollama сгруппировала видео в {len(clusters)} клипа(ов)")
                return clusters
        except Exception as e:
            await ws_manager.broadcast(f"⚠️  Ollama не ответила: {e}")
    
    if config["ai_brain"].get("cloud_fallback", {}).get("enabled", False):
        await ws_manager.broadcast("🔄 Переключаюсь на GigaChat API...")
        gigachat = GigaChatClient(config["ai_brain"])
        clusters = await gigachat.analyze_video_cluster(videos_info)
        
        if clusters:
            await ws_manager.broadcast(f"✅ GigaChat сгруппировала видео в {len(clusters)} клипа(ов)")
            return clusters
    
    await ws_manager.broadcast("⚠️  Использую fallback-кластеризацию")
    return await fallback_clustering(videos_info)

def create_clustering_prompt(videos_info: List[Dict]) -> str:
    """Создает промпт для LLM на основе метаданных видео"""
    prompt = """Ты - профессиональный AI-режиссер монтажа. 
Твоя задача - сгруппировать видеофрагменты в логически завершенные короткие видео (Shorts 9:16).

У тебя есть следующие видеофрагменты:
"""
    for i, video in enumerate(videos_info, 1):
        prompt += f"""
Фрагмент {i}:
- Файл: {video['filename']}
- Настроение: {video.get('mood', 'unknown')}
- Сцен: {video.get('scenes', 0)}
- Транскрипция: {video.get('transcript', 'нет текста')[:200]}
"""
    
    prompt += """
ИНСТРУКЦИЯ:
1. Проанализируй все фрагменты
2. Сгруппируй их в 1-5 логически завершенных клипов
3. Для каждого клипа укажи:
   - Название (краткое, привлекательное)
   - Список номеров фрагментов (indices)
   - Общее настроение (mood): energetic, calm, epic, funny
   - Примерную длительность
   - Hook (цепляющее начало) - какой фрагмент поставить первым

ВЕРНИ СТРОГО JSON в формате:
{
  "clusters": [
    {
      "title": "Название клипа",
      "fragment_indices": [1, 3, 5],
      "mood": "energetic",
      "estimated_duration": 45,
      "hook_fragment": 1,
      "description": "Краткое описание"
    }
  ]
}

Отвечай ТОЛЬКО JSON, без дополнительных комментариев."""
    return prompt

async def send_to_ollama(prompt: str, config: Dict) -> List[Dict]:
    """Отправляет промпт в Ollama и получает ответ"""
    model = config["ai_brain"]["ollama"]["model"]
    base_url = config["ai_brain"]["ollama"]["base_url"]
    timeout = config["ai_brain"]["ollama"].get("timeout", 120)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.7, "top_p": 0.9}
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                try:
                    start_idx = response_text.find("{")
                    end_idx = response_text.rfind("}") + 1
                    json_str = response_text[start_idx:end_idx]
                    data = json.loads(json_str)
                    return data.get("clusters", [])
                except json.JSONDecodeError as e:
                    await ws_manager.broadcast(f"️  Ошибка парсинга JSON: {e}")
                    return []
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
        except httpx.TimeoutException:
            raise Exception("Превышено время ожидания ответа от Ollama")
        except httpx.ConnectError:
            raise Exception("Не удалось подключиться к Ollama. Убедитесь, что она запущена.")

async def fallback_clustering(videos_info: List[Dict]) -> List[Dict]:
    """Fallback кластеризация, если AI не ответил"""
    await ws_manager.broadcast("🔄 Использую простую эвристическую группировку")
    
    return [{
        "title": "Смонтированный клип",
        "fragment_indices": list(range(1, len(videos_info) + 1)),
        "mood": "energetic",
        "estimated_duration": 60,
        "hook_fragment": 1,
        "description": "Все загруженные видео"
    }]