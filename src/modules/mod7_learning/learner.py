"""
Оркестратор самообучения (LearningEngine).

Связывает экстрактор паттернов и векторное хранилище в единый движок:

    learn_from_references(category, reference_dir) -> List[EditPattern]
        Анализирует все референсные клипы категории, извлекает паттерны,
        сохраняет их в векторное хранилище (непрерывное обучение)
        и в базу данных (learning_patterns).

    find_similar(pattern, category=None, k=5) -> List[SearchHit]
        Ищет похожие паттерны для применения к новому видео.

    get_category_profile(category) -> EditPattern
        Агрегированный "средний" профиль категории (стиль).

Движок персистентен: паттерны сохраняются в data/learning_store (NumPy/FAISS)
и в SQLAlchemy-БД (learning_patterns), переживают перезапуск.
"""
from __future__ import annotations

import logging
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import ws_manager
from src.modules.mod7_learning.pattern_models import EditPattern
from src.modules.mod7_learning.pattern_extractor import (
    build_pattern_vector,
    extract_pattern,
    extract_pattern_async,
)
from src.modules.mod7_learning.vector_store import SearchHit, VectorStore, get_vector_store
from src.database.session import session_scope
from src.database.models import Category, LearningPattern, Video

logger = logging.getLogger("learning.engine")

DEFAULT_STORE_DIR = Path("data") / "learning_store"


class LearningEngine:
    """
    Движок самообучения на примерах.

    Args:
        store_dir: Папка персистентного векторного хранилища.
        vector_size: Размерность вектора признаков (должна совпадать с экстрактором).
    """

    def __init__(self, store_dir: Path = DEFAULT_STORE_DIR, vector_size: int = 10) -> None:
        self.store_dir = Path(store_dir)
        self.store: VectorStore = get_vector_store(
            self.store_dir, vector_size=vector_size, prefer_backend="faiss"
        )
        logger.info("LearningEngine инициализирован (store=%s)", self.store_dir)

    # ------------------------------------------------------------------ обучение
    async def learn_from_references(
        self,
        reference_dir: Path,
        category: str = "default",
    ) -> List[EditPattern]:
        """
        Анализирует референсные клипы категории и сохраняет паттерны в хранилище.

        Это ключевой метод непрерывного обучения: чем больше примеров вы даёте,
        тем точнее движок понимает ваш стиль.

        Returns:
            Список извлечённых паттернов.
        """
        reference_dir = Path(reference_dir)
        video_files: List[Path] = []
        for ext in ("*.mp4", "*.mov", "*.avi", "*.mkv", "*.webm"):
            video_files.extend(reference_dir.glob(ext))

        if not video_files:
            raise ValueError(
                f"В папке '{reference_dir}' не найдено видеофайлов для обучения"
            )

        await ws_manager.broadcast(
            f"🧠 Самообучение [{category}]: анализирую {len(video_files)} референсов..."
        )

        patterns: List[EditPattern] = []
        for i, video in enumerate(video_files, 1):
            try:
                await ws_manager.broadcast(f"   📊 {i}/{len(video_files)}: {video.name}")
                pattern = await extract_pattern_async(video, category=category)
                patterns.append(pattern)
                # Сохраняем в векторное хранилище (метаданные содержат весь паттерн).
                self.store.add(
                    pattern.vector,
                    metadata={
                        "category": category,
                        "source_path": pattern.source_path,
                        "pattern": pattern.serialize(),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Не удалось извлечь паттерн из %s: %s", video.name, exc)
                await ws_manager.broadcast(f"   ⚠️  Ошибка анализа {video.name}: {exc}")

        # Персистим накопленные паттерны (векторное хранилище).
        self.store.persist()

        # Сохраняем паттерны в базу данных (learning_patterns).
        try:
            saved_db = self.save_patterns_to_db(patterns, category=category)
            await ws_manager.broadcast(f"   🗄️  В БД сохранено паттернов: {saved_db}")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось сохранить паттерны в БД: %s", exc)
            await ws_manager.broadcast(f"   ⚠️  Ошибка сохранения в БД: {exc}")

        # Вычисляем оптимальные веса слоёв скоринга для этой категории.
        try:
            weights = self._compute_scoring_weights(video_files, category)
            if weights:
                self._save_scoring_weights(category, weights)
                await ws_manager.broadcast(
                    f"   ⚖️  Веса скоринга обновлены: {weights}"
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось вычислить веса скоринга: %s", exc)

        await ws_manager.broadcast(
            f"✅ Самообучение [{category}] завершено: извлечено {len(patterns)} паттернов. "
            f"Всего в хранилище: {self.store.count()}"
        )
        return patterns

    # --------------------------------------------------------------- БД-интеграция
    def save_patterns_to_db(self, patterns: List[EditPattern], category: str) -> int:
        """
        Сохраняет извлечённые паттерны в таблицу learning_patterns.

        Каждый паттерн привязывается к категории (создаётся, если её нет)
        и к записи видео (создаётся, если ещё не существует).

        Returns:
            Число сохранённых паттернов.
        """
        saved = 0
        try:
            with session_scope() as db:
                # Гарантируем существование категории.
                db_category = db.query(Category).filter(Category.name == category).first()
                if db_category is None:
                    db_category = Category(name=category)
                    db.add(db_category)
                    db.flush()  # получить id

                for pattern in patterns:
                    # Привязка к видео по пути исходного референса.
                    video = None
                    if pattern.source_path:
                        video = (
                            db.query(Video)
                            .filter(Video.file_path == pattern.source_path)
                            .first()
                        )
                        if video is None:
                            video = Video(
                                file_path=pattern.source_path,
                                duration=pattern.duration_sec or None,
                                category_id=db_category.id,
                                status="reference",
                            )
                            db.add(video)
                            db.flush()

                    db_pattern = LearningPattern(
                        video_id=video.id if video else None,
                        category_id=db_category.id,
                        vector=pattern.vector or None,
                        structure=pattern.structure.model_dump() if pattern.structure else None,
                        tempo=pattern.tempo.avg_cut_duration if pattern.tempo else None,
                        transitions=pattern.transitions.model_dump() if pattern.transitions else None,
                        color_profile=pattern.color.model_dump() if pattern.color else None,
                        music_profile=pattern.music.model_dump() if pattern.music else None,
                    )
                    db.add(db_pattern)
                    saved += 1

            logger.info("Сохранено паттернов в БД: %d (категория %s)", saved, category)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка сохранения паттернов в БД")
            raise
        return saved

    def get_patterns_from_db(self, category: str) -> List[Dict[str, Any]]:
        """
        Возвращает паттерны категории из БД (learning_patterns).

        Returns:
            Список словарей с данными паттернов.
        """
        result: List[Dict[str, Any]] = []
        try:
            with session_scope() as db:
                db_category = db.query(Category).filter(Category.name == category).first()
                if db_category is None:
                    return []
                rows = (
                    db.query(LearningPattern)
                    .filter(LearningPattern.category_id == db_category.id)
                    .all()
                )
                for row in rows:
                    result.append({
                        "id": row.id,
                        "video_id": row.video_id,
                        "vector": row.vector,
                        "structure": row.structure,
                        "tempo": row.tempo,
                        "transitions": row.transitions,
                        "color_profile": row.color_profile,
                        "music_profile": row.music_profile,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                    })
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ошибка чтения паттернов из БД: %s", exc)
        return result

    # ------------------------------------------------------------------ веса скоринга
    def _compute_scoring_weights(
        self,
        video_files: List[Path],
        category: str,
    ) -> Dict[str, float]:
        """Вычисляет оптимальные веса слоёв скоринга на основе референсов.

        Анализирует характерные слои референсных клипов и вычисляет веса,
        при которых эти слои дают наибольший вклад.
        """
        try:
            from src.modules.mod8_analysis.scene_scorer import SceneScorer

            scorer = SceneScorer()
            layer_importance: Dict[str, float] = {k: 0.0 for k in scorer.weights}

            for vf in video_files[:10]:  # ограничиваем для производительности
                scenes = [{"start_sec": 0, "end_sec": 30, "duration_sec": 30}]
                scored = scorer.score_scenes(vf, scenes)
                if scored:
                    layers = scored[0].get("layers", {})
                    for layer, val in layers.items():
                        if layer in layer_importance:
                            layer_importance[layer] += val

            # Нормализуем веса.
            total = sum(layer_importance.values()) or 1.0
            weights = {k: round(v / total, 3) for k, v in layer_importance.items()}
            return weights
        except Exception:
            return {}

    def _save_scoring_weights(self, category: str, weights: Dict[str, float]) -> None:
        """Сохраняет веса скоринга в конфиг-файл категории."""
        import json
        config_dir = self.store_dir / "scoring_weights"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / f"{category}.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(weights, f, indent=2)

    def get_scoring_weights(self, category: str) -> Optional[Dict[str, float]]:
        """Загружает веса скоринга для категории."""
        import json
        config_path = self.store_dir / "scoring_weights" / f"{category}.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    # ------------------------------------------------------------------ поиск
    def find_similar(
        self,
        pattern: EditPattern,
        category: Optional[str] = None,
        k: int = 5,
    ) -> List[SearchHit]:
        """
        Ищет похожие паттерны для данного паттерна/видео.

        Args:
            pattern: Паттерн (или любой объект с .vector) для поиска.
            category: Опциональный фильтр по категории.
            k: Число ближайших результатов.

        Returns:
            Список SearchHit с баллом сходства (0..1).
        """
        query = list(pattern.vector)
        hits = self.store.search(query, k=k)
        if category:
            hits = [h for h in hits if h.metadata.get("category") == category]
        return hits

    # ------------------------------------------------------------------ профиль
    def get_category_profile(self, category: str) -> Optional[EditPattern]:
        """
        Возвращает агрегированный "средний" профиль стиля категории.

        Усредняет все паттерны категории по ключевым метрикам. Возвращает
        EditPattern с заполненными усреднёнными слоями, либо None, если
        в категории нет обученных паттернов.
        """
        patterns = self._patterns_by_category(category)
        if not patterns:
            return None
        return _average_patterns(patterns, category=category)

    def list_categories(self) -> List[str]:
        """Возвращает список категорий, по которым есть обученные паттерны."""
        cats: set[str] = set()
        if self.store._chroma is not None:
            try:
                res = self.store._chroma["collection"].get(include=["metadatas"])
                for meta in (res.get("metadatas") or []):
                    if meta and meta.get("category"):
                        cats.add(str(meta["category"]))
                return sorted(cats)
            except Exception:  # noqa: BLE001
                pass
        for meta in self.store._metadata:
            if meta.get("category"):
                cats.add(str(meta["category"]))
        return sorted(cats)

    def _patterns_by_category(self, category: str) -> List[EditPattern]:
        """Извлекает все паттерны категории из хранилища."""
        patterns: List[EditPattern] = []
        if self.store._chroma is not None:
            try:
                res = self.store._chroma["collection"].get(include=["metadatas"])
                for meta in (res.get("metadatas") or []):
                    if meta and meta.get("category") == category and meta.get("pattern"):
                        try:
                            patterns.append(EditPattern.deserialize(meta["pattern"]))
                        except Exception:  # noqa: BLE001
                            continue
                return patterns
            except Exception:  # noqa: BLE001
                pass
        for meta in self.store._metadata:
            if meta.get("category") == category and meta.get("pattern"):
                try:
                    patterns.append(EditPattern.deserialize(meta["pattern"]))
                except Exception:  # noqa: BLE001
                    continue
        return patterns

    def stats(self) -> Dict[str, Any]:
        """Статистика движка обучения."""
        return {
            "store_backend": self.store.backend_name,
            "total_patterns": self.store.count(),
            "categories": self.list_categories(),
        }


# ==============================================================================
# Утилиты агрегации
# ==============================================================================
def _average_patterns(patterns: List[EditPattern], category: str) -> EditPattern:
    """Усредняет список паттернов в единый профиль стиля категории."""
    if not patterns:
        raise ValueError("Нет паттернов для усреднения")

    def _med(key: str) -> float:
        vals = [p.to_feature_dict()[key] for p in patterns]
        return float(statistics.median(vals))

    bpm_vals = [p.music.bpm for p in patterns if p.music.bpm]
    energy_vals = [p.music.energy_percent for p in patterns if p.music.energy_percent is not None]
    camelots = [p.music.camelot for p in patterns if p.music.camelot]

    avg = EditPattern(
        category=category,
        duration_sec=_med("phase_count") * _med("avg_cut_duration"),
        structure=patterns[0].structure.model_copy(deep=True),
        tempo=patterns[0].tempo.model_copy(deep=True),
        transitions=patterns[0].transitions.model_copy(deep=True),
        color=patterns[0].color.model_copy(deep=True),
        music=patterns[0].music.model_copy(deep=True),
        extracted_by=f"learning_engine:aggregate:{len(patterns)}",
    )
    avg.tempo.avg_cut_duration = round(_med("avg_cut_duration"), 2)
    avg.tempo.cuts_per_minute = round(_med("cuts_per_minute"), 1)
    avg.tempo.tempo_label = _tempo_label(avg.tempo.avg_cut_duration)
    avg.structure.hook_at_start = _med("hook_at_start") > 0.5
    avg.structure.phase_count = int(round(_med("phase_count")))
    avg.color.brightness = round(_med("brightness"), 3)
    avg.color.saturation = round(_med("saturation"), 3)
    avg.color.contrast = round(_med("contrast"), 3)
    avg.color.color_temp = round(_med("color_temp"), 3)
    avg.music.bpm = round(statistics.median(bpm_vals), 1) if bpm_vals else None
    avg.music.energy_percent = int(round(statistics.median(energy_vals))) if energy_vals else None
    avg.music.camelot = statistics.mode(camelots) if camelots else None
    avg.vector = build_pattern_vector(avg)
    return avg


def _tempo_label(avg_cut: float) -> str:
    if avg_cut < 2.0:
        return "fast"
    if avg_cut > 5.0:
        return "slow"
    return "balanced"