"""
Анализ референсных видео для создания профиля стиля
ТЕПЕРЬ ВКЛЮЧАЕТ ГЛУБОКИЙ АУДИО-АНАЛИЗ (BPM, Camelot, Энергия, Сетка битов)
И РЕАЛЬНЫЙ ВИДЕО-АНАЛИЗ (детекция сцен, частота склеек)
"""
import asyncio
import re
import statistics
from pathlib import Path
from typing import Dict, Any, List
from src.core.config_loader import load_config
from src.utils.logger import ws_manager
from src.utils.audio_analyzer import analyze_audio_track


async def _detect_scenes_simple(video_path: Path, duration_limit: float = 60.0) -> List[float]:
    """
    Детектирует сцены в видео через PySceneDetect или контентный анализ FFmpeg
    
    Returns:
        Список длительностей найденных сцен (в секундах)
    """
    cut_durations = []
    
    try:
        # Пытаемся использовать PySceneDetect
        from scenedetect import detect, ContentDetector
        
        scene_list = detect(
            str(video_path),
            ContentDetector(threshold=27.0),
            start_in_scene=True
        )
        
        if scene_list:
            for scene in scene_list:
                start = scene[0].get_seconds()
                end = scene[1].get_seconds()
                scene_dur = end - start
                if 0.3 <= scene_dur <= duration_limit:
                    cut_durations.append(scene_dur)
    except ImportError:
        pass
    except Exception:
        pass
    
    # Если PySceneDetect не сработал — используем FFmpeg scene detection
    if not cut_durations:
        try:
            cmd = [
                "ffmpeg", "-i", str(video_path),
                "-filter:v", f"select='gt(scene,0.3)',showinfo",
                "-f", "null", "-"
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await process.communicate()
            
            # Парсим showinfo для извлечения pts_time
            times = re.findall(r"pts_time:([\d.]+)", stderr.decode(errors="ignore"))
            prev = 0.0
            for t_str in times:
                t = float(t_str)
                if t - prev > 0.5:
                    cut_durations.append(t - prev)
                prev = t
            if prev > 0:
                cut_durations.append(duration_limit - prev)
        except Exception:
            pass
    
    return cut_durations if cut_durations else [2.5]  # fallback


async def analyze_reference_clips(reference_dir: str) -> Dict[str, Any]:
    """Анализирует референсные видео и создает умный профиль стиля"""
    config = load_config()
    ref_path = Path(reference_dir)
    
    video_files = list(ref_path.glob("*.mp4")) + list(ref_path.glob("*.mov"))
    
    if not video_files:
        raise ValueError("В папке reference_clips нет видеофайлов")
    
    await ws_manager.broadcast(f"🔍 Найдено {len(video_files)} референсов. Запускаю аудио-видео анализ...")
    
    style_metrics = {
        "cut_durations": [],
        "audio_bpm": [],
        "audio_energy": [],
        "audio_camelot": [],
        "zoom_frequency": []
    }
    
    for i, video_file in enumerate(video_files, 1):
        await ws_manager.broadcast(f"   📊 Анализ {i}/{len(video_files)}: {video_file.name}")
        
        # 1. Глубокий аудио-анализ (аналог Timbrica)
        audio_data = analyze_audio_track(video_file, duration_limit=60.0)
        
        if audio_data["success"]:
            style_metrics["audio_bpm"].append(audio_data["bpm"])
            style_metrics["audio_energy"].append(audio_data["energy_percent"])
            if audio_data["camelot"] != "Unknown":
                style_metrics["audio_camelot"].append(audio_data["camelot"])
            
            await ws_manager.broadcast(f"      🎵 Музыка: {audio_data['bpm']} BPM, Энергия: {audio_data['energy_percent']}%, Тональность: {audio_data['camelot']}")
        else:
            await ws_manager.broadcast(f"      ⚠️  Ошибка аудио: {audio_data.get('error')}")
        
        # 2. Реальная детекция сцен
        scene_durations = await _detect_scenes_simple(video_file)
        if scene_durations:
            style_metrics["cut_durations"].extend(scene_durations)
            avg_cut = statistics.median(scene_durations)
            await ws_manager.broadcast(f"      ✂️ Сцен: {len(scene_durations)}, Средняя длина склейки: {avg_cut:.1f}с")
        
        # 3. Оценка zoom_frequency на основе сцен (эвристика)
        if scene_durations:
            # Чем короче сцены, тем выше zoom_frequency (больше динамики)
            avg_scene = statistics.median(scene_durations)
            zoom_freq = min(1.3, max(1.05, 1.0 + (3.0 - avg_scene) / 20.0))
            style_metrics["zoom_frequency"].append(zoom_freq)
        else:
            style_metrics["zoom_frequency"].append(1.15)
        
        await asyncio.sleep(0.3)  # Небольшая пауза между видео
    
    # Рассчитываем итоговый профиль на основе собранных данных
    profile = calculate_style_profile(style_metrics)
    
    return profile

def calculate_style_profile(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Рассчитывает итоговый профиль стиля и правила монтажа"""
    profile = {}
    
    # 1. Видео метрики
    if metrics["cut_durations"]:
        profile["avg_cut_duration"] = round(statistics.median(metrics["cut_durations"]), 2)
    else:
        profile["avg_cut_duration"] = 3.0
        
    if metrics["zoom_frequency"]:
        profile["avg_zoom_factor"] = round(statistics.median(metrics["zoom_frequency"]), 2)
    else:
        profile["avg_zoom_factor"] = 1.15

    # 2. АУДИО МЕТРИКИ (Сердце системы)
    if metrics["audio_bpm"]:
        profile["target_bpm"] = round(statistics.median(metrics["audio_bpm"]), 1)
        # Допускаем отклонение +/- 10% для поиска музыки
        profile["bpm_range"] = [
            round(profile["target_bpm"] * 0.9, 1),
            round(profile["target_bpm"] * 1.1, 1)
        ]
    else:
        profile["target_bpm"] = 120.0
        profile["bpm_range"] = [100.0, 140.0]
        
    if metrics["audio_energy"]:
        profile["target_energy_percent"] = int(statistics.median(metrics["audio_energy"]))
    else:
        profile["target_energy_percent"] = 70
        
    if metrics["audio_camelot"]:
        # Находим самую частую тональность для гармоничного сведения
        profile["preferred_camelot"] = max(set(metrics["audio_camelot"]), key=metrics["audio_camelot"].count)
    else:
        profile["preferred_camelot"] = "Any"
        
    # 3. ВЫВОД ПРАВИЛА МОНТАЖА (AI-логика)
    # Если энергия высокая (>60%) и склейки короткие (<3 сек) -> Динамичный монтаж под бит
    if profile.get("target_energy_percent", 0) > 60 and profile.get("avg_cut_duration", 99) < 3.5:
        profile["editing_rule"] = "dynamic_beat_sync" # Резать видео ровно в моменты beat_times_sec
        profile["description"] = "Динамичный клип с частыми склейками под ритм музыки"
    # Если энергия низкая и склейки длинные -> Плавный повествовательный монтаж
    elif profile.get("target_energy_percent", 0) < 50 and profile.get("avg_cut_duration", 99) > 4.0:
        profile["editing_rule"] = "narrative_flow" # Плавный монтаж по смыслу текста, медленные зумы
        profile["description"] = "Атмосферный клип с плавными переходами и акцентом на смысл"
    else:
        profile["editing_rule"] = "balanced"
        profile["description"] = "Сбалансированный монтаж"

    profile["version"] = "3.0 (Audio-Enhanced Timbrica Logic)"
    return profile