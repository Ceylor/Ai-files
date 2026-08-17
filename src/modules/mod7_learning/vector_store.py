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