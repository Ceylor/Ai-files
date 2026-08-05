"""
Модуль улучшения качества видео: стабилизация, поворот, улучшение резкости
"""
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import json
from src.utils.logger import ws_manager


class VideoEnhancer:
    """Улучшение качества: стабилизация, поворот, резкость"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    async def analyze_video_quality(self, video_path: Path) -> Dict[str, Any]:
        """Анализирует качество видео: стабильность, резкость, ориентацию"""
        await ws_manager.broadcast(f"  🔍 Анализ качества: {video_path.name}")
        
        result = {
            "width": 0,
            "height": 0,
            "rotation": 0,
            "avg_brightness": 0,
            "avg_sharpness": 0,
            "needs_stabilization": False,
            "needs_rotation": False,
        }
        
        # Получаем метаданные
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(video_path)
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        
        if process.returncode == 0:
            data = json.loads(stdout)
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    result["width"] = int(stream.get("width", 0))
                    result["height"] = int(stream.get("height", 0))
                    
                    # Проверяем поворот
                    rotation = int(stream.get("tags", {}).get("rotate", 0))
                    result["rotation"] = rotation
                    result["needs_rotation"] = rotation > 0
                    
                    break
        
        return result
    
    async def stabilize_and_fix(
        self, 
        input_path: Path, 
        output_path: Path,
        quality_info: Dict[str, Any]
    ) -> Path:
        """Стабилизирует, поворачивает и улучшает видео"""
        await ws_manager.broadcast(f"  🎬 Улучшение качества...")
        
        filters = []
        
        # 1. Поворот
        rotation = quality_info.get("rotation", 0)
        if rotation:
            if rotation == 90:
                filters.append("transpose=1")
            elif rotation == 180:
                filters.append("transpose=1,transpose=1")
            elif rotation == 270:
                filters.append("transpose=2")
            await ws_manager.broadcast(f"  🔄 Поворот на {rotation}°")
        
        # 2. Улучшение резкости
        filters.append("unsharp=5:5:1.0:5:5:0.0")
        
        if filters:
            vf = ",".join(filters)
            cmd = [
                "ffmpeg", "-y",
                "-i", str(input_path),
                "-vf", vf,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "copy",
                str(output_path)
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
        
        if output_path.exists() and output_path.stat().st_size > 0:
            await ws_manager.broadcast(f"  ✅ Улучшение завершено")
            return output_path
        
        # Если не получилось, возвращаем оригинал
        return input_path
