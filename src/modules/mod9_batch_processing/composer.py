"""
Композитор клипов: кластеризация фрагментов по смыслу (CLIP) и объединение.

Возможности:
    - Кластеризация видеофрагментов по CLIP-эмбеддингам (косинусное сходство);
    - Автоматическое объединение фрагментов в логические клипы;
    - Создание нескольких клипов из одного набора файлов.

Алгоритм кластеризации — простая агломерация по порогу косинусного сходства
средних эмбеддингов (без внешних зависимостей, чистая математика).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import ws_manager

logger = logging.getLogger("batch.composer")


def _cosine(a: List[float], b: List[float]) -> float:
    """Косинусное сходство двух векторов (0..1)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    import math

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _mean_embedding(embeddings: List[List[float]]) -> List[float]:
    """Усредняет список эмбеддингов."""
    if not embeddings:
        return []
    dim = len(embeddings[0])
    mean = [0.0] * dim
    for emb in embeddings:
        for i, v in enumerate(emb[:dim]):
            mean[i] += v
    return [v / len(embeddings) for v in mean]


class ClipComposer:
    """
    Композитор клипов на основе CLIP-эмбеддингов.

    Args:
        similarity_threshold: порог косинусного сходства для объединения в кластер.
        max_cluster_size: максимальное число фрагментов в одном клипе.
    """

    def __init__(self, similarity_threshold: float = 0.75, max_cluster_size: int = 5) -> None:
        self.similarity_threshold = similarity_threshold
        self.max_cluster_size = max_cluster_size

    # ------------------------------------------------------------------ кластеризация
    def cluster_fragments(self, fragments: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Кластеризует фрагменты по средним CLIP-эмбеддингам.

        Args:
            fragments: список dict [{"video_id": int, "path": str, "embedding": [..]}, ...]

        Returns:
            Список кластеров (каждый кластер — список фрагментов).
        """
        if not fragments:
            return []

        # Жадная агломерация: последовательно сравниваем со средним кластера.
        clusters: List[List[Dict[str, Any]]] = []
        cluster_means: List[List[float]] = []

        for frag in fragments:
            emb = frag.get("embedding") or []
            best_idx = -1
            best_sim = -1.0
            for ci, mean in enumerate(cluster_means):
                sim = _cosine(emb, mean)
                if sim > best_sim:
                    best_sim = sim
                    best_idx = ci

            # Если похож и кластер не переполнен — добавляем.
            if best_idx >= 0 and best_sim >= self.similarity_threshold and \
                    len(clusters[best_idx]) < self.max_cluster_size:
                clusters[best_idx].append(frag)
                # Пересчитываем среднее.
                cluster_means[best_idx] = _mean_embedding(
                    [f.get("embedding") or [] for f in clusters[best_idx]]
                )
            else:
                # Новый кластер.
                clusters.append([frag])
                cluster_means.append(emb)

        logger.info("Композитор: %d фрагментов -> %d кластеров", len(fragments), len(clusters))
        return clusters

    # ------------------------------------------------------------------ композиция
    def compose_clips(
        self,
        fragments: List[Dict[str, Any]],
        output_dir: Path,
        prefix: str = "clip",
    ) -> List[Dict[str, Any]]:
        """
        Создаёт композиции клипов из набора фрагментов.

        Возвращает список планов клипов (метаданные для монтажа), где каждый
        клип — список фрагментов одного кластера.

        Returns:
            Список dict [{"index": int, "name": str, "fragments": [...], "output_path": str}]
        """
        clusters = self.cluster_fragments(fragments)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        plans: List[Dict[str, Any]] = []
        for i, cluster in enumerate(clusters, 1):
            if not cluster:
                continue
            name = f"{prefix}_{i:02d}"
            plans.append({
                "index": i,
                "name": name,
                "fragments": cluster,
                "output_path": str(output_dir / f"{name}.mp4"),
            })
        await_warn = None  # для совместимости
        logger.info("Композиция: создано %d планов клипов", len(plans))
        return plans

    # ------------------------------------------------------------------ эвристика без CLIP
    @staticmethod
    def group_by_time(fragments: List[Dict[str, Any]], group_size: int = 3) -> List[List[Dict[str, Any]]]:
        """
        Fallback-группировка фрагментов (если CLIP-эмбеддинги недоступны).
        Группирует по порядку, по group_size штук в клипе.

        Returns:
            Список кластеров.
        """
        groups: List[List[Dict[str, Any]]] = []
        for i in range(0, len(fragments), group_size):
            groups.append(fragments[i:i + group_size])
        return groups