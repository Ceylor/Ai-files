"""
Модуль 6: Финальный экспорт и рендеринг
Поддержка профилей экспорта (HD/FHD/4K, TikTok/Shorts/Reels),
цветокоррекции и стилизованных субтитров.
"""
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from src.utils.logger import ws_manager

from src.modules.mod10_final_features.export_profiles import ExportProfiles


class VideoExporter:
    """Класс для финального рендеринга видео"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.export_config = config.get("export", {})
        self.general_config = config.get("general", {})
        self.export_profiles = ExportProfiles()

    async def render_final_clip(
        self,
        video_path: Path,
        audio_path: Path,
        subs_path: Optional[Path],
        output_path: Path,
        platform: str = "tiktok",
        quality: Optional[str] = None,
        max_duration: Optional[float] = None,
    ) -> Path:
        """
        Собирает финальное видео (Видео + Музыка + Субтитры) с учётом
        профиля экспорта и качества.

        Args:
            video_path: Обработанное видео (9:16).
            audio_path: Подготовленная музыка.
            subs_path: Файл субтитров .ass (или None).
            output_path: Итоговый файл.
            platform: пресет платформы (tiktok/yt_shorts/instagram_reels/youtube).
            quality: желаемое качество (hd/fhd/4k).
            max_duration: переопределение максимальной длительности.
        """
        await ws_manager.broadcast("🎬 Финальный рендер...")

        # Разрешаем профиль экспорта.
        profile = self.export_profiles.resolve(
            platform=platform, quality=quality, max_duration=max_duration
        )
        await ws_manager.broadcast(f"  📦 Профиль: {profile['label']}")

        # Настройки кодека из конфига.
        codec = self.export_config.get("codec", "h264_nvenc")
        preset = self.export_config.get("preset", "p4")
        cq = self.export_config.get("cq", "19")
        video_bitrate = profile.get("bitrate", self.general_config.get("video_bitrate", "8M"))
        audio_bitrate = self.general_config.get("audio_bitrate", "192k")

        # Громкость музыки (ducking).
        music_volume = self.config.get("music", {}).get("volume", {}).get("music_volume_db", -20)

        # Формируем видеофильтр.
        vf_parts = [profile["vf"]]  # scale/crop/pad под профиль

        if subs_path and Path(subs_path).exists():
            # Вшиваем ASS субтитры прямо в кадр.
            subs_posix = Path(subs_path).as_posix()
            subs_escaped = subs_posix.replace(":", r"\:")
            vf_parts.append(f"ass={subs_escaped}")
            await ws_manager.broadcast("  📝 Субтитры вшиваются в кадр...")

        vf = ",".join(vf_parts)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-map", "0:v",
            "-map", "1:a",

            "-c:v", codec,
            "-preset", preset,
            "-cq", str(cq),
            "-b:v", video_bitrate,
            "-vf", vf,
        ]

        cmd += [
            "-c:a", "aac",
            "-b:a", audio_bitrate,
            "-filter:a", f"volume={music_volume}dB",
            "-shortest",
            str(output_path),
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            # Если NVENC не сработал — пробуем libx264 (software).
            if codec == "h264_nvenc" and ("nvenc" in error_msg.lower() or "encoder" in error_msg.lower()):
                await ws_manager.broadcast("  ⚠️  NVENC недоступен, переключаюсь на libx264 (software)...")
                cmd[cmd.index(codec)] = "libx264"
                cmd[cmd.index(preset)] = "fast"
                if "-cq" in cmd:
                    idx = cmd.index("-cq")
                    cmd[idx] = "-crf"

                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    error_msg = stderr.decode('utf-8', errors='ignore')
                    await ws_manager.broadcast(f"  ❌ Ошибка рендера FFmpeg: {error_msg[:200]}")
                    raise Exception(f"FFmpeg render failed: {error_msg}")
            else:
                await ws_manager.broadcast(f"  ❌ Ошибка рендера FFmpeg: {error_msg[:200]}")
                raise Exception(f"FFmpeg render failed: {error_msg}")

        await ws_manager.broadcast(f"  ✅ Рендер завершен! Сохранено в: {output_path.name}")
        return output_path