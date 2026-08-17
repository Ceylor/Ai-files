"""
Векторное хранилище паттернов с graceful-fallback.

Приоритет бэкендов (по убыванию):
    1. FAISS    — быстрый поиск по косинусному сходству, GPU-опция.
    2. ChromaDB — простое персистентное хранилище с метаданными.
    3. NumPy    — in-memory косинусное сходство (всегда доступен).

Любой недоступный бэкенд не роняет систему: при импорте/инициализации
ошибка логируется и выбирается следующий. Это важно, т.к. тяжёлые
ML-зависимости (faiss-cpu, chromadb) могут отсутствовать в окружении.

Параметр prefer_backend строго уважается:
    - "faiss"  → пытаемся подключить FAISS, иначе NumPy;
    - "chroma" → пытаемся подключить ChromaDB, иначе NumPy;
    - "numpy"  → всегда используем NumPy (без тяжёлых бэкендов).

Интерфейс:
    VectorStore.add(embedding, metadata) -> id
    VectorStore.search(query_vector, k) -> List[SearchHit]
    VectorStore.persist() / VectorStore.load()
    VectorStore.count() / VectorStore.clear()
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("learning.vector_store")


# Заглушка-класс для типизации, чтобы не требовать фаисс на импорте.
class _FAISSBackend:
    def __init__(self, store: "VectorStore") -> None:  # pragma: no cover
        self.store = store
        self._index = None

    @property
    def available(self) -> bool:
        return self._index is not None


@dataclass
class SearchHit:
    """Результат векторного поиска."""

    id: str
    score: float  # косинусное сходство 0..1 (1 = максимально похоже)
    metadata: Dict[str, Any] = dc_field(default_factory=dict)


class VectorStore:
    """
    Универсальное векторное хранилище с graceful-fallback.

    Args:
        persist_dir: Папка для персистентного сохранения паттернов (JSON + бинарь).
        vector_size: Ожидаемая размерность векторов (для валидации).
        prefer_backend: Предпочтительный бэкенд ("faiss" | "chroma" | "numpy").
    """

    def __init__(
        self,
        persist_dir: Path,
        vector_size: int = 10,
        prefer_backend: str = "faiss",
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.vector_size = vector_size
        self.backend_name = "numpy"  # дефолт
        self._vectors: List[List[float]] = []
        self._ids: List[str] = []
        self._metadata: List[Dict[str, Any]] = []
        self._id_counter = 0

        # Попытка подключить более быстрые бэкенды.
        self._faiss = self._init_faiss(prefer_backend)
        self._chroma = self._init_chroma(prefer_backend)
        if self._chroma is not None:
            self.backend_name = "chroma"
        elif self._faiss is not None and self._faiss.available:
            self.backend_name = "faiss"

        logger.info("Векторное хранилище инициализировано: backend=%s", self.backend_name)

    # ------------------------------------------------------------------ init
    def _init_faiss(self, prefer: str) -> Optional[_FAISSBackend]:
        # При prefer=numpy и prefer=chroma не используем FAISS.
        if prefer in ("chroma", "numpy"):
            return None
        try:
            import faiss  # type: ignore

            index = faiss.IndexFlatIP(self.vector_size)  # inner product == cosine после нормировки
            backend = _FAISSBackend(self)
            backend._index = index
            logger.info("FAISS-бэкенд активен (IndexFlatIP, dim=%s)", self.vector_size)
            return backend
        except Exception as exc:  # noqa: BLE001
            logger.debug("FAISS недоступен, используем fallback: %s", exc)
            return None

    def _init_chroma(self, prefer: str):
        # При prefer=numpy и prefer=faiss не используем ChromaDB.
        if prefer in ("faiss", "numpy"):
            return None
        try:
            import chromadb  # type: ignore

            client = chromadb.PersistentClient(path=str(self.persist_dir / "chroma"))
            collection = client.get_or_create_collection(
                "edit_patterns", metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB-бэкенд активен")
            return {"client": client, "collection": collection}
        except Exception as exc:  # noqa: BLE001
            logger.debug("ChromaDB недоступен, используем fallback: %s", exc)
            return None

    # --------------------------------------------------------------- core ops
    def add(self, embedding: List[float], metadata: Optional[Dict[str, Any]] = None) -> str:
        """Добавляет вектор с метаданными и возвращает его id."""
        if len(embedding) != self.vector_size:
            raise ValueError(
                f"Неверная размерность вектора: {len(embedding)}, ожидается {self.vector_size}"
            )
        self._id_counter += 1
        item_id = f"pat_{self._id_counter:06d}"

        if self._chroma is not None:
            # ChromaDB не принимает пустой dict в metadata — используем непустой плейсхолдер.
            chroma_meta = metadata if metadata else {"_stored": True}
            self._chroma["collection"].add(
                ids=[item_id],
                embeddings=[embedding],
                metadatas=[chroma_meta],
            )
        elif self._faiss is not None and self._faiss.available:
            import faiss  # type: ignore

            vec = [embedding]
            faiss.normalize_L2(vec)  # нормируем для косинусного сходства через inner product
            self._faiss._index.add(vec)
            self._vectors.append(embedding)
            self._ids.append(item_id)
            self._metadata.append(metadata or {})
        else:
            self._vectors.append(embedding)
            self._ids.append(item_id)
            self._metadata.append(metadata or {})

        return item_id

    def search(self, query_vector: List[float], k: int = 5) -> List[SearchHit]:
        """Ищет k наиболее похожих паттернов. Возвращает SearchHit-список."""
        if len(query_vector) != self.vector_size:
            raise ValueError(
                f"Неверная размерность query: {len(query_vector)}, ожидается {self.vector_size}"
            )
        k = max(1, min(k, self.count()))

        if self._chroma is not None:
            res = self._chroma["collection"].query(
                query_embeddings=[query_vector], n_results=k
            )
            hits: List[SearchHit] = []
            ids = (res.get("ids") or [[]])[0]
            dists = (res.get("distances") or [[]])[0]
            metas = (res.get("metadatas") or [[]])[0]
            for i, item_id in enumerate(ids):
                # Chroma возвращает расстояние; для косинуса конвертируем в сходство.
                score = max(0.0, 1.0 - float(dists[i]))
                hits.append(SearchHit(id=str(item_id), score=score, metadata=metas[i] or {}))
            return hits

        if self._faiss is not None and self._faiss.available:
            import faiss  # type: ignore

            q = [list(query_vector)]
            faiss.normalize_L2(q)
            scores, idx = self._faiss._index.search(q, k)
            hits = []
            for j in range(k):
                pos = int(idx[0][j])
                if pos < 0:
                    continue
                hits.append(
                    SearchHit(
                        id=self._ids[pos],
                        score=float(scores[0][j]),
                        metadata=self._metadata[pos],
                    )
                )
            return hits

        # NumPy fallback: честный косинус по всем векторам.
        return self._search_numpy(query_vector, k)

    def _search_numpy(self, query_vector: List[float], k: int) -> List[SearchHit]:
        """In-memory поиск по косинусному сходству (бэкенд numpy)."""
        if not self._vectors:
            return []
        q = _normalize(query_vector)
        scored: List[SearchHit] = []
        for i, vec in enumerate(self._vectors):
            sim = _dot(q, _normalize(vec))
            scored.append(SearchHit(id=self._ids[i], score=sim, metadata=self._metadata[i]))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:k]

    # ------------------------------------------------------------- persistence
    def persist(self) -> None:
        """Сохраняет паттерны на диск (JSON + .npy) для переживания рестарта."""
        if self._chroma is not None:
            # Chroma персистит автоматически через PersistentClient.
            logger.info("ChromaDB персистирует данные автоматически")
            return

        data = {
            "version": 1,
            "backend": self.backend_name,
            "ids": self._ids,
            "metadata": self._metadata,
        }
        meta_path = self.persist_dir / "patterns.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        import numpy as np

        np.save(self.persist_dir / "vectors.npy", np.array(self._vectors, dtype="float32"))
        logger.info("Паттерны сохранены: %d записей -> %s", self.count(), meta_path)

    def load(self) -> int:
        """Загружает ранее сохранённые паттерны. Возвращает число записей."""
        if self._chroma is not None:
            try:
                col = self._chroma["collection"].count()
                return int(col)
            except Exception:  # noqa: BLE001
                return 0

        meta_path = self.persist_dir / "patterns.json"
        vec_path = self.persist_dir / "vectors.npy"
        if not meta_path.exists() or not vec_path.exists():
            return 0

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            import numpy as np

            vectors = np.load(vec_path).tolist()
            self._ids = list(data.get("ids", []))
            self._metadata = list(data.get("metadata", []))
            self._vectors = list(vectors)
            self._id_counter = len(self._ids)

            if self._faiss is not None and self._faiss.available:
                import faiss  # type: ignore

                index = faiss.IndexFlatIP(self.vector_size)
                arr = np.array(vectors, dtype="float32")
                faiss.normalize_L2(arr)
                index.add(arr)
                self._faiss._index = index

            logger.info("Загружено %d паттернов из хранилища", self.count())
            return self.count()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось загрузить хранилище: %s", exc)
            return 0

    def count(self) -> int:
        if self._chroma is not None:
            try:
                return int(self._chroma["collection"].count())
            except Exception:  # noqa: BLE001
                return 0
        return len(self._ids)

    def clear(self) -> None:
        """Очищает хранилище (в памяти и на диске)."""
        if self._chroma is not None:
            try:
                self._chroma["collection"].delete(where={})
            except Exception:  # noqa: BLE001
                pass
        self._vectors = []
        self._ids = []
        self._metadata = []
        self._id_counter = 0
        logger.info("Хранилище очищено")


# ==============================================================================
# Утилиты для бэкенда numpy
# ==============================================================================
def _normalize(vec: List[float]) -> List[float]:
    """Нормирует вектор до единичной длины."""
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return list(vec)
    return [v / norm for v in vec]


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


# ==============================================================================
# Фабрика
# ==============================================================================
def get_vector_store(
    persist_dir: Path,
    vector_size: int = 10,
    prefer_backend: str = "faiss",
) -> VectorStore:
    """Создаёт и загружает векторное хранилище (фабрика)."""
    store = VectorStore(persist_dir, vector_size=vector_size, prefer_backend=prefer_backend)
    store.load()
    return store