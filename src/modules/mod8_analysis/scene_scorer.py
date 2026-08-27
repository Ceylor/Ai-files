"""
Многослойный скоринг фрагментов видео.

Вычисляет «скор интереса» для каждой сцены на основе 7 слоёв:
1. Аудиоактивность (громкость, диапазон частот)
2. Движение (оптический поток)
3. Эмоции (если детектор доступен)
4. Редкость объектов (если детектор доступен)
5. Смена планов (размер кадра, крупность)
6. Музыкальные биты (BPM, энергия)
7. Визуальная яркость (цвет, контраст)

Итоговый скор = среднее взвешенное. Веса настраиваются через конфиг.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("analysis.scene_scorer")

# Веса слоёв по умолчанию (сумма = 1.0)
DEFAULT_WEIGHTS = {
    "audio_activity": 0.15,
    "motion_energy": 0.20,
    "emotion": 0.10,
    "object_rarity": 0.10,
    "shot_change": 0.15,
    "music_beats": 0.15,
    "visual_brightness": 0.15,
}


class SceneScorer:
    """Вычисляет скор интереса для каждой сцены видео.

    Args:
        weights: словарь весов слоёв (опционально).
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or DEFAULT_WEIGHTS.copy()

    def score_scenes(
        self,
        video_path: Path,
        scenes: List[Dict[str, Any]],
        analysis: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Вычисляет скор для каждой сцены.

        Args:
            video_path: путь к видео.
            scenes: список сцен {start_sec, end_sec, duration_sec}.
            analysis: результат многослойного анализа (опционально).

        Returns:
            список сцен с добавленным полем score (0–1).
        """
        if not scenes:
            return []

        scored = []
        for scene in scenes:
            layers = self._compute_layers(video_path, scene, analysis)
            total = sum(
                layers.get(layer, 0.0) * self.weights.get(layer, 0.0)
                for layer in self.weights
            )
            scored.append({
                **scene,
                "score": round(min(max(total, 0.0), 1.0), 4),
                "layers": layers,
            })

        # Сортировка по убыванию скора.
        scored.sort(key=lambda s: s["score"], reverse=True)
        return scored

    def _compute_layers(
        self,
        video_path: Path,
        scene: Dict[str, Any],
        analysis: Optional[Dict[str, Any]],
    ) -> Dict[str, float]:
        """Вычисляет значения 0–1 для каждого слоя."""
        layers = {}

        # 1. Аудиоактивность.
        layers["audio_activity"] = self._score_audio_activity(video_path, scene)

        # 2. Движение.
        layers["motion_energy"] = self._score_motion(video_path, scene)

        # 3. Эмоции (из анализа).
        layers["emotion"] = self._score_emotion(analysis, scene)

        # 4. Редкость объектов.
        layers["object_rarity"] = self._score_object_rarity(analysis, scene)

        # 5. Смена планов.
        layers["shot_change"] = self._score_shot_change(scene)

        # 6. Музыкальные биты.
        layers["music_beats"] = self._score_music_beats(video_path, scene)

        # 7. Визуальная яркость.
        layers["visual_brightness"] = self._score_visual_brightness(video_path, scene)

        return layers

    def _score_audio_activity(self, video_path: Path, scene: Dict[str, Any]) -> float:
        """Скор аудиоактивности (громкость, диапазон)."""
        try:
            import subprocess
            result = subprocess.run(
                [
                    "ffmpeg", "-i", str(video_path),
                    "-ss", str(scene.get("start_sec", 0)),
                    "-t", str(scene.get("duration_sec", 5)),
                    "-af", "volumedetect",
                    "-f", "null", "-"
                ],
                capture_output=True, text=True, timeout=30
            )
            stderr = result.stderr
            # Извлекаем mean_volume
            for line in stderr.split("\n"):
                if "mean_volume" in line:
                    val = float(line.split(":")[-1].strip().split(" ")[0])
                    # Нормализуем: -40dB = 0, 0dB = 1
                    return max(0.0, min(1.0, (val + 40) / 40))
        except Exception:
            pass
        return 0.5  # fallback

    def _score_motion(self, video_path: Path, scene: Dict[str, Any]) -> float:
        """Скор движения (оптический поток через OpenCV)."""
        try:
            import cv2
            import numpy as np

            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            start_frame = int(scene.get("start_sec", 0) * fps)
            end_frame = int(scene.get("end_sec", start_frame + fps * 5))
            step = max(1, int(fps / 10))  # анализируем 10 кадров/сек

            prev_gray = None
            motion_scores = []
            frame_idx = start_frame

            while frame_idx < end_frame and len(motion_scores) < 50:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, (320, 180))

                if prev_gray is not None:
                    diff = cv2.absdiff(prev_gray, gray)
                    motion_scores.append(np.mean(diff) / 255.0)

                prev_gray = gray
                frame_idx += step

            cap.release()
            if motion_scores:
                return min(1.0, sum(motion_scores) / len(motion_scores) * 5)
        except Exception:
            pass
        return 0.5

    def _score_emotion(self, analysis: Optional[Dict], scene: Dict[str, Any]) -> float:
        """Скор эмоций (из результатов анализа)."""
        if not analysis:
            return 0.5
        emotions = analysis.get("emotions", [])
        if not emotions:
            return 0.5
        # Считаем долю ярких эмоций (не neutral)
        start = scene.get("start_sec", 0)
        end = scene.get("end_sec", start + 5)
        relevant = [
            e for e in emotions
            if start <= e.get("timestamp", 0) <= end
        ]
        if not relevant:
            return 0.5
        bright = sum(1 for e in relevant if e.get("emotion") != "neutral")
        return min(1.0, bright / len(relevant) * 1.5)

    def _score_object_rarity(self, analysis: Optional[Dict], scene: Dict[str, Any]) -> float:
        """Скор редкости объектов."""
        if not analysis:
            return 0.5
        objects = analysis.get("objects", [])
        if not objects:
            return 0.5
        start = scene.get("start_sec", 0)
        end = scene.get("end_sec", start + 5)
        relevant = [
            o for o in objects
            if start <= o.get("timestamp", 0) <= end
        ]
        if not relevant:
            return 0.5
        # Чем меньше объектов, тем выше редкость
        return max(0.0, 1.0 - len(relevant) * 0.1)

    def _score_shot_change(self, scene: Dict[str, Any]) -> float:
        """Скор смены планов (длительность сцены)."""
        dur = scene.get("duration_sec", 5)
        # Короткие сцены (2-5 сек) — высокий скор, длинные (>30 сек) — низкий
        if dur < 2:
            return 0.3
        elif dur < 5:
            return 0.9
        elif dur < 10:
            return 0.7
        elif dur < 30:
            return 0.5
        else:
            return 0.2

    def _score_music_beats(self, video_path: Path, scene: Dict[str, Any]) -> float:
        """Скор музыкальных битов (BPM через librosa)."""
        try:
            import subprocess
            import tempfile
            import os

            # Извлекаем аудио для сцены
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(video_path),
                    "-ss", str(scene.get("start_sec", 0)),
                    "-t", str(min(scene.get("duration_sec", 10), 30)),
                    "-ac", "1", "-ar", "22050",
                    tmp_path
                ],
                capture_output=True, timeout=30
            )

            import librosa
            y, sr = librosa.load(tmp_path, sr=22000, duration=30)
            os.unlink(tmp_path)

            # BPM
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            tempo_val = float(tempo) if hasattr(tempo, '__float__') else float(tempo[0]) if hasattr(tempo, '__getitem__') else 120.0

            # Энергия битов
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            energy = float(onset_env.mean()) if len(onset_env) > 0 else 0.0

            # Нормализуем: BPM 60-180 = 0-1, энергия 0-1
            bpm_score = max(0.0, min(1.0, (tempo_val - 60) / 120))
            energy_score = min(1.0, energy * 10)

            return (bpm_score * 0.5 + energy_score * 0.5)
        except Exception:
            pass
        return 0.5

    def _score_visual_brightness(self, video_path: Path, scene: Dict[str, Any]) -> float:
        """Скор визуальной яркости (яркость, контраст через OpenCV)."""
        try:
            import cv2
            import numpy as np

            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            mid_frame = int((scene.get("start_sec", 0) + scene.get("end_sec", 5)) / 2 * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
            ret, frame = cap.read()
            cap.release()

            if ret:
                # Яркость (средняя интенсивность)
                brightness = np.mean(frame) / 255.0
                # Контраст (стандартное отклонение)
                contrast = np.std(frame) / 128.0
                return min(1.0, (brightness * 0.6 + contrast * 0.4))
        except Exception:
            pass
        return 0.5
