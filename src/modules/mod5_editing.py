"""
Модуль 5: Интеллектуальный монтаж с синхронизацией под бит
Использует beat_times_sec и drop_times_sec из аудио-анализа
"""
import asyncio
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import cv2
from src.utils.logger import ws_manager


class SmartEditor:
    """Интеллектуальный редактор с синхронизацией под бит"""
    
    def __init__(self, config: Dict, temp_dir: Path):
        self.config = config
        self.temp_dir = temp_dir
        self.target_resolution = config["general"].get("resolution", [1080, 1920])
        self.editing_config = config.get("editing", {})
        # Максимальная длительность клипа (из конфига или 55 сек)
        self.max_clip_duration = self.editing_config.get("max_clip_duration", 55)

    async def edit_clip_with_beat_sync(
        self,
        video_path: Path,
        music_metadata: Dict,
        output_path: Path,
        style_profile: Optional[Dict] = None,
        max_duration: Optional[float] = None,
        scene_tempo: Optional[Dict] = None
    ) -> Path:
        """
        Монтирует клип, синхронизируя склейки с битами музыки
        scene_tempo: {fragment_index: "fast"/"normal"/"slow"} - темп для каждого фрагмента
        """
        await ws_manager.broadcast("🎬 Монтаж с синхронизацией под бит...")
        
        # Определяем максимальную длительность
        if max_duration is None:
            max_duration = self.max_clip_duration
        await ws_manager.broadcast(f"   ⏱️  Максимальная длительность клипа: {max_duration}с")
        
        # Получаем сетку битов из метаданных музыки
        beat_times = music_metadata.get("beat_times_sec", [])
        drop_times = music_metadata.get("drop_times_sec", [])
        bpm = music_metadata.get("bpm", 120)
        
        # Получаем длительность исходного видео
        duration = await self._get_video_duration(video_path)
        
        # Определяем целевую длительность ДО ветвления (A2 FIX)
        target_duration = min(duration, max_duration or self.max_clip_duration)
        await ws_manager.broadcast(f"   📏 Длительность видео: {duration:.1f}с → лимит: {target_duration:.1f}с")
        
        # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ A2: НЕ масштабируем биты под видео!
        # Музыка играет в реальном темпе — обрезаем видео ПОД музыку
        if beat_times:
            music_duration = beat_times[-1] if beat_times else 30
            # Определяем реальную длительность музыки
            await ws_manager.broadcast(f"   🎵 BPM: {bpm}, Битов в треке: {len(beat_times)}, Дропов: {len(drop_times)}")
            await ws_manager.broadcast(f"   🎵 Реальная длительность музыки: {music_duration:.1f}с")
            
            # Обрезаем видео ПОД музыку (не наоборот!)
            target_duration = min(duration, music_duration, max_duration or self.max_clip_duration)
            await ws_manager.broadcast(f"   📏 Видео: {duration:.1f}с → обрезаем до {target_duration:.1f}с (под музыку)")
            
            if duration > target_duration:
                trimmed_path = self.temp_dir / "trimmed_source.mp4"
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", "0.0",
                    "-i", str(video_path),
                    "-t", str(target_duration),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-c:a", "aac", "-b:a", "128k",
                    str(trimmed_path)
                ]
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                if trimmed_path.exists():
                    video_path = trimmed_path
                    duration = target_duration
            
            # НЕ масштабируем биты — используем реальные!
            # Фильтруем биты по обрезанной длительности
            beat_times = [t for t in beat_times if t < duration]
            drop_times = [t for t in drop_times if t < duration]
            await ws_manager.broadcast(f"   🎵 Битов после обрезки: {len(beat_times)}, Дропов: {len(drop_times)}")
        else:
            await ws_manager.broadcast("  ⚠️  Сетка битов пуста, использую стандартную нарезку")
            return await self._standard_cut(video_path, output_path, max_duration=target_duration)
        
        # Получаем правило монтажа из профиля
        editing_rule = "balanced"
        if style_profile:
            editing_rule = style_profile.get("editing_rule", "balanced")
        
        await ws_manager.broadcast(f"    Правило монтажа: {editing_rule}")
        
        # Формируем список точек склейки с учетом темпа сцен
        cut_points = self._calculate_cut_points(beat_times, drop_times, duration, editing_rule, scene_tempo)
        
        await ws_manager.broadcast(f"   ️  Точек склейки: {len(cut_points)}")
        
        # Нарезаем видео по точкам склейки через FFmpeg (быстро и качественно)
        await self._cut_video_by_points(video_path, cut_points, output_path)
        
        # Применяем auto-reframe 9:16 если нужно
        if self.editing_config.get("auto_reframe", {}).get("enabled", False):
            reframed_path = output_path.with_suffix(".reframed.mp4")
            await self.auto_reframe_916(output_path, reframed_path)
            output_path.unlink()  # Удаляем промежуточный файл
            reframed_path.rename(output_path)
        
        await ws_manager.broadcast("  ✅ Монтаж завершен")
        return output_path

    def _calculate_cut_points(
        self, 
        beats: List[float], 
        drops: List[float], 
        duration: float,
        editing_rule: str,
        scene_tempo: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Рассчитывает точки склейки на основе битов и правила монтажа
        scene_tempo: {fragment_index: "fast"/"normal"/"slow"} - темп для каждого фрагмента
        """
        cut_points = []
        
        if editing_rule == "dynamic_beat_sync":
            # Динамичный монтаж: режем на каждом бите, на дропах — зум
            for i, beat in enumerate(beats):
                is_drop = any(abs(beat - drop) < 0.3 for drop in drops)
                cut_points.append({
                    "time": beat,
                    "effect": "zoom" if is_drop else "cut",
                    "intensity": 1.3 if is_drop else 1.0
                })
        
        elif editing_rule == "narrative_flow":
            # Плавный монтаж: режем реже, только на сильных битах (каждый 2-й или 4-й)
            step = max(1, len(beats) // 10)  # ~10 склеек на клип
            for i in range(0, len(beats), step):
                beat = beats[i]
                is_drop = any(abs(beat - drop) < 0.5 for drop in drops)
                cut_points.append({
                    "time": beat,
                    "effect": "fade" if is_drop else "cut",
                    "intensity": 1.15 if is_drop else 1.0
                })
        
        else:
            # Сбалансированный: каждый 2-й бит
            for i in range(0, len(beats), 2):
                beat = beats[i]
                is_drop = any(abs(beat - drop) < 0.4 for drop in drops)
                cut_points.append({
                    "time": beat,
                    "effect": "zoom" if is_drop else "cut",
                    "intensity": 1.2 if is_drop else 1.0
                })
        
        # Добавляем начало и конец
        if cut_points and cut_points[0]["time"] > 0.5:
            cut_points.insert(0, {"time": 0.0, "effect": "cut", "intensity": 1.0})
        if cut_points and cut_points[-1]["time"] < duration - 0.5:
            cut_points.append({"time": duration, "effect": "cut", "intensity": 1.0})
        
        return cut_points

    async def _cut_video_by_points(self, video_path: Path, cut_points: List[Dict], output_path: Path):
        """Нарезает видео по точкам склейки через FFmpeg с применением эффектов.
        Если точек мало — всё равно режет видео на сегменты по таймкодам."""
        
        # Если нет точек склейки — генерируем автоматические каждые 3-5 секунд
        if len(cut_points) < 2:
            duration = await self._get_video_duration(video_path)
            cut_points = []
            interval = 3.0  # Раз в 3 секунды
            t = 0.0
            while t < duration:
                cut_points.append({"time": t, "effect": "cut", "intensity": 1.0})
                t += interval
            if cut_points and cut_points[-1]["time"] < duration - 0.5:
                cut_points.append({"time": duration, "effect": "cut", "intensity": 1.0})
            await ws_manager.broadcast(f"   ️  Точек нет, генерируем {len(cut_points)} автоматических (каждые 3с)")
        
        if len(cut_points) < 2:
            # Всё ещё мало точек — обрезаем видео до макс. длительности
            await self._standard_cut(video_path, output_path, max_duration=self.max_clip_duration)
            return
        
        # Создаем файл со списком сегментов для FFmpeg concat
        segments_file = self.temp_dir / "segments.txt"
        segment_files = []
        
        for i in range(len(cut_points) - 1):
            start = cut_points[i]["time"]
            end = cut_points[i + 1]["time"]
            seg_duration = end - start
            
            if seg_duration < 0.5:  # Пропускаем слишком короткие сегменты
                continue
            
            segment_file = self.temp_dir / f"segment_{i:03d}.mp4"
            effect = cut_points[i].get("effect", "cut")
            intensity = cut_points[i].get("intensity", 1.0)
            
            # 1.3 Вариативность: случайный выбор типа эффекта
            import random
            effects_pool = ["cut", "zoom", "fade"]
            if random.random() < 0.3:  # 30% chance для альтернативного эффекта
                alternate = random.choice(["zoom", "fade"])
                if alternate != effect:
                    effect = alternate
                    intensity = 1.15 + random.random() * 0.15
            
            # Формируем фильтры для эффектов
            vf_parts = []
            
            if effect == "zoom" and intensity > 1.0:
                # Zoom-эффект: масштабируем и кропаем центр
                # 1.3 Вариативность: разные позиции зума
                zoom_type = random.choice(["center", "top", "bottom", "left", "right"])
                if zoom_type == "center":
                    vf_parts.append(
                        f"scale=iw*{intensity}:ih*{intensity}:flags=lanczos,"
                        f"crop=iw/{intensity}:ih/{intensity}"
                    )
                elif zoom_type == "top":
                    vf_parts.append(
                        f"scale=iw*{intensity}:ih*{intensity}:flags=lanczos,"
                        f"crop=iw/{intensity}:ih/{intensity}:x=0:y=0"
                    )
                elif zoom_type == "bottom":
                    vf_parts.append(
                        f"scale=iw*{intensity}:ih*{intensity}:flags=lanczos,"
                        f"crop=iw/{intensity}:ih/{intensity}:x=0:y=(ih-ih/{intensity})/2"
                    )
                elif zoom_type == "left":
                    vf_parts.append(
                        f"scale=iw*{intensity}:ih*{intensity}:flags=lanczos,"
                        f"crop=iw/{intensity}:ih/{intensity}:x=0:y=0"
                    )
                else:  # right
                    vf_parts.append(
                        f"scale=iw*{intensity}:ih*{intensity}:flags=lanczos,"
                        f"crop=iw/{intensity}:ih/{intensity}:x=(iw-iw/{intensity}):y=0"
                    )
            elif effect == "fade":
                # Fade-эффект: плавное появление из чёрного
                fade_dur = 0.2 + random.random() * 0.3  # Случайная длительность
                vf_parts.append("fade=t=in:st=0:d={d:.2f},fade=t=out:st={st}:d={d:.2f}".format(
                    d=fade_dur, st=max(0, seg_duration - fade_dur)
                ))
            
            # Собираем команду FFmpeg
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-i", str(video_path),
                "-t", str(seg_duration),
            ]
            
            if vf_parts:
                cmd += ["-vf", ",".join(vf_parts)]
            
            # Всегда ре-энкодим, чтобы фильтры применились
            cmd += [
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                str(segment_file)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if segment_file.exists() and segment_file.stat().st_size > 0:
                segment_files.append(segment_file)
        
        # Склеиваем сегменты
        with open(segments_file, "w") as f:
            for sf in segment_files:
                f.write(f"file '{sf}'\n")
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(segments_file),
            "-c", "copy",
            str(output_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        # Очищаем временные файлы
        for sf in segment_files:
            if sf.exists():
                sf.unlink()
        if segments_file.exists():
            segments_file.unlink()

    async def _standard_cut(self, video_path: Path, output_path: Path,
                             max_duration: Optional[float] = None) -> Path:
        """Стандартная нарезка без синхронизации (fallback).
        Если задано max_duration — обрезает видео до указанной длительности,
        начиная с самого начала (timestamp 0.0)."""
        if max_duration is not None:
            duration = await self._get_video_duration(video_path)
            if duration > max_duration:
                await ws_manager.broadcast(
                    f"   ✂️  Обрезка с 0.0с до {max_duration}с (было {duration:.1f}с)"
                )
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", "0.0",
                    "-i", str(video_path),
                    "-t", str(max_duration),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-c:a", "aac", "-b:a", "128k",
                    str(output_path)
                ]
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                if output_path.exists() and output_path.stat().st_size > 0:
                    return output_path
                # Если не вышло — копируем целиком
        shutil.copy(video_path, output_path)
        return output_path

    async def _get_video_duration(self, video_path: Path) -> float:
        """Получает длительность видео через ffprobe"""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        if process.returncode == 0:
            return float(stdout.decode().strip())
        return 0.0

    async def auto_reframe_916(self, video_path: Path, output_path: Path) -> Path:
        """
        Адаптивный кроп в 9:16 с отслеживанием лица или центра
        1.3 Вариативность: случайный Ken Burns эффект
        """
        await ws_manager.broadcast("  Auto-Reframe 9:16...")
        import random
        
        # 1.3 Вариативность: случайный Ken Burns эффект
        kb_enabled = random.random() < 0.5  # 50% шанс
        kb_direction = random.choice(["zoom_in", "zoom_out", "pan_left", "pan_right", "none"])
        
        if kb_enabled and kb_direction != "none":
            # Ken Burns эффект через FFmpeg
            kb_filter = ""
            if kb_direction == "zoom_in":
                kb_filter = "zoomin=z=1.2:d=3:x='iw/2-(iw/zoom/2)':y=0"
            elif kb_direction == "zoom_out":
                kb_filter = "zoomout=z=0.8:d=3:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            elif kb_direction == "pan_left":
                kb_filter = "zoomin=z=1.1:d=3:x='-iw/10':y=0"
            elif kb_direction == "pan_right":
                kb_filter = "zoomin=z=1.1:d=3:x='iw':y=0"
            
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-vf", f"{kb_filter},scale=1080:1920:force_original_aspect_ratio=decrease,"
                       f"crop=1080:1920,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                str(output_path)
            ]
        else:
            # Простой кроп без Ken Burns
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,"
                       "crop=1080:1920,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                str(output_path)
            ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        if output_path.exists():
            kb_info = f" (Ken Burns: {kb_direction})" if kb_enabled else ""
            await ws_manager.broadcast(f"  ✅ Auto-Reframe завершен{kb_info}")
            return output_path
        
        # Если не получилось, возвращаем оригинал
        shutil.copy(video_path, output_path)
        return output_path
