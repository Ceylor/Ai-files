"""
Модуль 6: Финальный экспорт и рендеринг
Использует аппаратное ускорение NVIDIA (NVENC)
"""
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from src.utils.logger import ws_manager

class VideoExporter:
    """Класс для финального рендеринга видео"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.export_config = config.get("export", {})
        self.general_config = config.get("general", {})

    async def render_final_clip(
        self, 
        video_path: Path, 
        audio_path: Path, 
        subs_path: Optional[Path], 
        output_path: Path
    ) -> Path:
        """
        Собирает финальное видео (Видео + Музыка + Субтитры)
        
        Args:
            video_path: Обработанное видео (9:16)
            audio_path: Подготовленная музыка
            subs_path: Файл субтитров .ass (или None для рендера без субтитров)
            output_path: Итоговый файл
            
        Returns:
            Путь к готовому видео
        """
        await ws_manager.broadcast("🎬 Финальный рендер...")
        
        # Настройки кодека из конфига
        codec = self.export_config.get("codec", "h264_nvenc")
        preset = self.export_config.get("preset", "p4")
        cq = self.export_config.get("cq", "19")
        video_bitrate = self.general_config.get("video_bitrate", "8M")
        audio_bitrate = self.general_config.get("audio_bitrate", "192k")
        
        # Громкость музыки (ducking)
        music_volume = self.config.get("music", {}).get("volume", {}).get("music_volume_db", -20)
        
        # Формируем видеофильтр
        vf_parts = []
        if subs_path and Path(subs_path).exists():
            # Вшиваем ASS субтитры прямо в кадр (надежно для VK/YouTube)
            # FFmpeg на Windows: используем форвард-слеши (бэкслеши — escape-символы)
            # и экранируем двоеточия (спецсимвол в ass= фильтре)
            subs_posix = Path(subs_path).as_posix()
            subs_escaped = subs_posix.replace(":", r"\:")
            vf_parts.append(f"ass={subs_escaped}")
            await ws_manager.broadcast("  📝 Субтитры вшиваются в кадр...")
        else:
            await ws_manager.broadcast("  ⚠️  Субтитры отсутствуют, рендер без них")
        
        vf = ",".join(vf_parts) if vf_parts else None
        
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
        ]
        
        if vf:
            cmd += ["-vf", vf]
        
        cmd += [
            "-c:a", "aac",
            "-b:a", audio_bitrate,
            "-filter:a", f"volume={music_volume}dB",
            
            "-shortest",
            str(output_path)
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            
            # Если NVENC не сработал — пробуем libx264 (software encoding)
            if codec == "h264_nvenc" and ("nvenc" in error_msg.lower() or "encoder" in error_msg.lower()):
                await ws_manager.broadcast("  ⚠️  NVENC недоступен, переключаюсь на libx264 (software)...")
                cmd[cmd.index(codec)] = "libx264"
                cmd[cmd.index(preset)] = "fast"
                # Убираем -cq (только для NVENC), добавляем -crf
                if "-cq" in cmd:
                    idx = cmd.index("-cq")
                    cmd[idx] = "-crf"
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
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