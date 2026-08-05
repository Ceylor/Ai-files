"""
Оркестратор полного пайплайна AI-монтажа
Координирует работу всех модулей: кластеризация → ингестия → музыка → монтаж → субтитры → экспорт
"""
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.core.config_loader import load_config
from src.utils.logger import ws_manager


class VideoPipeline:
    """Основной класс пайплайна обработки видео"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.temp_dir = Path(config["general"].get("temp_dir", "./data/temp"))
        self.output_dir = Path(config["general"].get("output_dir", "./data/output"))
        self.music_dir = Path(config["general"].get("music_library_dir", "./data/music_library"))

    async def process_batch(
        self,
        input_files: List[Path],
        style_profile: Optional[Dict] = None,
        category: str = "default"
    ) -> List[Path]:
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        output_files = []

        try:
            # Шаг 1: AI кластеризация
            await ws_manager.broadcast("🧩 Шаг 1/6: AI анализ и группировка клипов...")
            from src.utils.narrative_cluster import cluster_videos
            clusters = await cluster_videos(str(input_files[0].parent))

            if not clusters:
                clusters = [{
                    "title": "Смонтированный клип",
                    "fragment_indices": list(range(1, len(input_files) + 1)),
                    "mood": "energetic",
                    "estimated_duration": 55,
                    "hook_fragment": 1,
                }]
                await ws_manager.broadcast("  ⚠️  Кластеризация вернула пустой результат, создан один клип")

            await ws_manager.broadcast(f"  💡 Запланировано {len(clusters)} клип(ов)")

            # Шаг 2: Обработка каждого кластера
            for idx, cluster in enumerate(clusters, 1):
                await ws_manager.broadcast(f"\n🎬 Обработка клипа {idx}/{len(clusters)}: {cluster.get('title', 'без названия')}")
                try:
                    clip_path = await self._process_cluster(
                        cluster, idx, input_files, style_profile
                    )
                    if clip_path:
                        output_files.append(clip_path)
                except Exception as e:
                    await ws_manager.broadcast(f"  ❌ Ошибка обработки клипа {idx}: {e}")
                    import traceback
                    traceback.print_exc()

            await ws_manager.broadcast(f"\n✅ Пайплайн завершен! Создано клипов: {len(output_files)}")

        except Exception as e:
            await ws_manager.broadcast(f"❌ Критическая ошибка пайплайна: {str(e)}")
            raise

        return output_files

    async def _process_cluster(
        self,
        cluster: Dict,
        cluster_idx: int,
        all_input_files: List[Path],
        style_profile: Optional[Dict]
    ) -> Optional[Path]:
        from src.modules.mod1_ingestion import VideoIngestion
        from src.modules.mod3_music_ai import MusicAI
        from src.modules.mod4_subtitles import SubtitleGenerator
        from src.modules.mod5_editing import SmartEditor
        from src.modules.mod6_export import VideoExporter
        from src.utils.story_builder import build_story, apply_story_structure

        cluster_temp = self.temp_dir / f"cluster_{cluster_idx:02d}"
        cluster_temp.mkdir(parents=True, exist_ok=True)

        # Определяем видео для этого кластера
        fragment_indices = cluster.get("fragment_indices", [])
        cluster_videos = []
        for fi in fragment_indices:
            if 1 <= fi <= len(all_input_files):
                cluster_videos.append(all_input_files[fi - 1])
        if not cluster_videos:
            cluster_videos = list(all_input_files)

        title = cluster.get("title", f"clip_{cluster_idx}")
        safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)[:50]
        output_path = self.output_dir / f"{safe_title}.mp4"

        # ========== ШАГ 1: СБОР ДАННЫХ О ФРАГМЕНТАХ ==========
        await ws_manager.broadcast("  📋 Шаг 1/6: Сбор данных о фрагментах...")
        fragments_data = []
        for i, video_path in enumerate(cluster_videos, 1):
            await ws_manager.broadcast(f"    📹 Анализ фрагмента {i}/{len(cluster_videos)}: {video_path.name}")
            ingestion = VideoIngestion(cluster_temp)
            ingested = await ingestion.process_video(video_path)
            
            fragments_data.append({
                "index": i,
                "path": video_path,
                "filename": video_path.name,
                "duration": ingested.get("duration", 0),
                "transcript": ingested.get("transcript", []),
                "scenes": ingested.get("scenes", []),
                "audio_path": ingested.get("audio_path"),
                "mood": cluster.get("mood", "unknown"),
                "audio_energy": 0.0,  # Будет заполнено позже
            })
        
        # ========== ШАГ 2: ПОСТРОЕНИЕ НАРРАТИВА ==========
        await ws_manager.broadcast("  🧩 Шаг 2/6: Построение нарративной структуры...")
        
        # 1.3 Добавляем seed для вариативности
        import hashlib
        cluster_seed = int(hashlib.md5(str(cluster.get('title', '')).encode()).hexdigest()[:8], 16)
        
        story = await build_story(fragments_data, style_profile, seed=cluster_seed)
        
        if story:
            await ws_manager.broadcast(f"    📖 Тип истории: {story.get('story_type', 'unknown')}")
            await ws_manager.broadcast(f"    🎣 Hook: фрагмент #{story.get('hook_fragment', 1)}")
            await ws_manager.broadcast(f"    📏 Цепочка: {len(story.get('chain', []))} элементов")
            
            # Применяем структуру к фрагментам
            story_result = apply_story_structure(fragments_data, story)
            sorted_fragments = story_result.get("sorted_fragments", [])
            excluded = story_result.get("excluded", [])
            scene_tempo = story_result.get("scene_tempo", {})
            
            if excluded:
                await ws_manager.broadcast(f"    ✂️  Удалено мусора: {len(excluded)} фрагмент(ов)")
            else:
                await ws_manager.broadcast(f"    ✅ Все фрагменты полезны")
        else:
            await ws_manager.broadcast("  ⚠️  Не удалось построить нарратив, используем все фрагменты")
            sorted_fragments = [{"index": i+1, "path": p, "filename": p.name, "duration": 0} 
                               for i, p in enumerate(cluster_videos)]
            scene_tempo = {i+1: "normal" for i in range(len(cluster_videos))}

        # ========== ШАГ 3: КОНКАТЕНАЦИЯ (с учетом нарратива) ==========
        await ws_manager.broadcast("  📎 Шаг 3/6: Объединение фрагментов...")
        
        # Сортируем видео по нарративной цепочке
        sorted_video_paths = []
        for frag in sorted_fragments:
            frag_path = frag.get("path")
            if frag_path and isinstance(frag_path, Path) and frag_path.exists():
                sorted_video_paths.append(frag_path)
        
        if len(sorted_video_paths) == 1:
            concat_video = sorted_video_paths[0]
        elif sorted_video_paths:
            concat_video = cluster_temp / "concat_source.mp4"
            await self._concat_videos(sorted_video_paths, concat_video)
        else:
            # Fallback
            concat_video = cluster_videos[0] if cluster_videos else cluster_temp / "fallback.mp4"
            if len(cluster_videos) > 1:
                await self._concat_videos(cluster_videos, concat_video)

        # ========== ШАГ 4: АНАЛИЗ СЦЕН (без дублирования транскрипции!) ==========
        # A8 FIX: transcript уже есть из Шага 1 (складываем из фрагментов)
        # Здесь делаем ТОЛЬКО scene detection для синхронизации монтажа
        await ws_manager.broadcast("  🎙️ Шаг 4/6: Анализ сцен и синхронизация...")
        
        # Склеиваем транскрипции из Шага 1 (экономим время — не делаем Whisper дважды!)
        merged_transcript = []
        time_offset = 0.0
        for frag_data in fragments_data:
            frag_transcript = frag_data.get("transcript", [])
            if isinstance(frag_transcript, list):
                for seg in frag_transcript:
                    if isinstance(seg, dict):
                        # Сдвигаем таймкоды на offset
                        seg_copy = seg.copy()
                        seg_copy["start"] += time_offset
                        seg_copy["end"] += time_offset
                        if seg_copy.get("words"):
                            for w in seg_copy["words"]:
                                w["start"] += time_offset
                                w["end"] += time_offset
                        merged_transcript.append(seg_copy)
            time_offset += frag_data.get("duration", 0)
        
        # Scene detection только (без транскрипции — экономим время)
        await ws_manager.broadcast("    🔍 Анализ сцен для beat-sync...")
        ingestion = VideoIngestion(cluster_temp)
        ingested = await ingestion.process_video(concat_video)
        # Переиспользуем merged_transcript из Шага 1
        transcript = merged_transcript
        video_duration = ingested.get("duration", 0) or 55

        # ========== ШАГ 5: ПОДБОР МУЗЫКИ ==========
        await ws_manager.broadcast("  🎵 Шаг 5/6: Подбор музыки...")
        music_ai = MusicAI(self.music_dir, self.config, style_profile or {})
        await music_ai.load_music_library()
        target_duration = min(video_duration, cluster.get("estimated_duration", 55))
        music_track = await music_ai.find_perfect_track(target_duration=target_duration)

        music_metadata = music_track or {}
        music_audio_path = self._resolve_music_audio(music_track, cluster_temp)

        # ========== ШАГ 6: МОНТАЖ С УЧЕТОМ НАРРАТИВА ==========
        await ws_manager.broadcast("  ✂️ Шаг 6/6: Монтаж и авто-кадрирование 9:16...")
        
        max_clip_duration = self.config.get("editing", {}).get("max_clip_duration", 55)
        editor = SmartEditor(self.config, cluster_temp)
        edited_video = cluster_temp / "edited.mp4"
        
        # Передаём max_duration и темп для каждого сегмента
        await editor.edit_clip_with_beat_sync(
            video_path=concat_video,
            music_metadata=music_metadata,
            output_path=edited_video,
            style_profile=style_profile,
            max_duration=max_clip_duration,
            scene_tempo=scene_tempo  # Передаем темп для каждой сцены
        )

        # Генерация субтитров (A10: с мэппингом таймкодов)
        subs_path = cluster_temp / "subtitles.ass"
        if transcript:
            await ws_manager.broadcast("  📝 Генерация субтитров...")
            sub_gen = SubtitleGenerator(self.config)
            # Передаём длительность финального видео для мэппинга таймкодов
            final_duration = max_clip_duration or 55
            await sub_gen.generate_ass(transcript, subs_path, duration=final_duration)
        else:
            subs_path = None

        # Шаг 6: Финальный экспорт
        await ws_manager.broadcast("  🎬 Шаг 6/6: Финальный рендер...")
        exporter = VideoExporter(self.config)

        if not music_audio_path or not music_audio_path.exists():
            await ws_manager.broadcast("  ⚠️  Музыка недоступна, рендер с оригинальным аудио")
            music_audio_path = ingested.get("audio_path")

        # Если аудио всё ещё нет — используем само видео как источник аудио
        if not music_audio_path:
            music_audio_path = edited_video

        await exporter.render_final_clip(
            video_path=edited_video,
            audio_path=Path(music_audio_path),
            subs_path=subs_path,
            output_path=output_path
        )

        await ws_manager.broadcast(f"  ✅ Клип сохранён: {output_path.name}")
        return output_path

    def _resolve_music_audio(self, track_metadata: Optional[Dict], temp_dir: Path) -> Optional[Path]:
        """Извлекает путь к аудиофайлу из метаданных трека"""
        if not track_metadata:
            return None

        full_path = track_metadata.get("full_path")
        if full_path and Path(full_path).exists():
            return Path(full_path)

        return None

    async def _concat_videos(self, video_paths: List[Path], output_path: Path):
        """Объединяет несколько видео в один файл через FFmpeg concat"""
        list_file = output_path.parent / "concat_list.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for vp in video_paths:
                f.write(f"file '{vp.absolute()}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_path)
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error = stderr.decode('utf-8', errors='ignore')[:200]
            raise Exception(f"FFmpeg concat failed: {error}")

        if list_file.exists():
            list_file.unlink()


async def run_pipeline(
    input_dir: str,
    style_profile: Optional[Dict] = None,
    category: str = "default"
) -> List[Path]:
    config = load_config()
    pipeline = VideoPipeline(config)

    input_path = Path(input_dir)
    input_files = list(input_path.glob("*.mp4")) + list(input_path.glob("*.mov"))

    if not input_files:
        await ws_manager.broadcast("⚠️  В папке input не найдено видеофайлов")
        return []

    await ws_manager.broadcast(f"📁 Найдено {len(input_files)} видеофайлов")

    return await pipeline.process_batch(input_files, style_profile, category)
