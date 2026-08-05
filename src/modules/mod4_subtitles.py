"""
Модуль 4: Генерация продвинутых субтитров (ASS)
Создает анимированные субтитры с подсветкой, тенями и позиционированием.
"""
import os
from pathlib import Path
from typing import List, Dict, Any
from src.utils.logger import ws_manager

class SubtitleGenerator:
    """Генератор ASS субтитров"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sub_config = config.get("subtitles", {})
        self.font_path = self.sub_config.get("font", {}).get("path", "Arial")
        self.font_size = self.sub_config.get("font", {}).get("size", 52)
        self.font_color = self._hex_to_ass(self.sub_config.get("font", {}).get("color", "#FFFFFF"))
        self.highlight_color = self._hex_to_ass(self.sub_config.get("highlight", {}).get("color", "#FFD700"))
        self.pos_x = self.sub_config.get("position", {}).get("x", 540)
        self.pos_y = self.sub_config.get("position", {}).get("y", 1500)
        
        # Загружаем ключевые слова для подсветки
        self.keywords = []
        kw_file = self.sub_config.get("highlight", {}).get("keywords_file", "")
        if kw_file and os.path.exists(kw_file):
            with open(kw_file, "r", encoding="utf-8") as f:
                self.keywords = [line.strip().lower() for line in f if line.strip()]

    async def generate_ass(self, transcript: List[Dict], output_path: Path, 
                           duration: float = 60) -> Path:
        """
        Генерирует .ass файл из транскрипции
        A10 FIX: добавлен параметр duration для корректного мэппинга таймкодов
        
        Args:
            transcript: Список сегментов от Whisper
            output_path: Путь для сохранения .ass файла
            duration: Длительность финального видео (для мэппинга)
            
        Returns:
            Путь к созданному файлу
        """
        await ws_manager.broadcast("📝 Генерация субтитров...")
        
        # A10 FIX: Мэппинг таймкодов на финальную длительность
        # После beat-sync монтажа таймкоды меняются — нормализуем их
        mapped_transcript = self._remap_timelines(transcript, duration)
        
        header = self._get_ass_header()
        events = []
        
        for segment in mapped_transcript:
            start_time = self._format_time(segment["start"])
            end_time = self._format_time(segment["end"])
            text = segment["text"].strip()
            
            # Разбиваем на слова для анимации (если включено)
            words = text.split()
            formatted_text = self._format_words(words, start_time, end_time)
            
            # Позиционирование (raw string для escape-последовательностей ASS)
            position_tag = r"{\an2\pos(" + str(self.pos_x) + "," + str(self.pos_y) + r")}"
            
            events.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{position_tag}{formatted_text}")
        
        # Собираем файл
        ass_content = header + "\n".join(events)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)
            
        await ws_manager.broadcast(f"  ✅ Субтитры созданы: {output_path.name}")
        return output_path

    def _remap_timelines(self, transcript: List[Dict], target_duration: float) -> List[Dict]:
        """
        A10 FIX: Мэппинг таймкодов на финальную длительность.
        После beat-sync монтажа таймкоды меняются — нормализуем их.
        
        Если transcript пустой или duration == 0 — возвращаем как есть.
        Иначе масштабируем все таймкоды пропорционально.
        """
        if not transcript or target_duration <= 0:
            return transcript
        
        # Находим максимальный таймкод
        max_time = max(seg.get("end", 0) for seg in transcript)
        
        if max_time <= 0:
            return transcript
        
        # Масштабируем таймкоды на target_duration
        scale_factor = target_duration / max_time
        mapped = []
        for seg in transcript:
            seg_copy = seg.copy()
            seg_copy["start"] = seg["start"] * scale_factor
            seg_copy["end"] = seg["end"] * scale_factor
            
            # Масштабируем слова тоже
            if seg_copy.get("words"):
                for w in seg_copy["words"]:
                    w["start"] = w["start"] * scale_factor
                    w["end"] = w["end"] * scale_factor
            
            # Убираем сегменты за пределами target_duration
            if seg_copy["end"] > 0 and seg_copy["end"] <= target_duration + 1:
                mapped.append(seg_copy)
        
        return mapped

    def _format_words(self, words: List[str], start: str, end: str) -> str:
        """Форматирует слова с анимацией и подсветкой"""
        # Для простоты и стабильности рендера используем поочередное выделение
        # В реальном ASS это делается через \t, но для надежности сделаем базовое выделение
        
        formatted = []
        for word in words:
            clean_word = word.strip(".,!?-:;")
            if clean_word.lower() in self.keywords:
                # Подсветка ключевых слов
                formatted.append(f"{{\\c&H{self.highlight_color}&\\b1}}{word}{{\\c&H{self.font_color}&\\b0}}")
            else:
                formatted.append(word)
                
        return " ".join(formatted)

    def _get_ass_header(self) -> str:
        """Возвращает стандартный заголовок ASS файла"""
        shadow_color = self._hex_to_ass(self.sub_config.get("effects", {}).get("shadow_color", "#000000"))
        outline_width = self.sub_config.get("effects", {}).get("outline_width", 3)
        
        return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.font_path},{self.font_size},&H00{self.font_color[2:]}&,&H000000FF&,&H00{shadow_color[2:]}&,&H80000000&,-1,0,0,0,100,100,0,0,1,{outline_width},2,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def _format_time(self, seconds: float) -> str:
        """Конвертирует секунды в формат ASS (H:MM:SS.CC)"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def _hex_to_ass(self, hex_color: str) -> str:
        """Конвертирует HEX (#RRGGBB) в формат ASS (AABBGGRR)"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
            return f"00{b}{g}{r}"
        return "00FFFFFF" # Белый по умолчанию