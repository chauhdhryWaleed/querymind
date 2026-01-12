"""bge-small-en-v1.5 embedder (384-dim, CPU): lazily-loaded, thread-safe process singleton."""

from __future__ import annotations

import threading
from typing import Protocol

EMBED_DIM = 384
_MODEL_NAME = "BAAI/bge-small-en-v1.5"
# Recommended bge query instruction for short-query → passage retrieval.
_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class EmbedderProtocol(Protocol):
    dim: int

    def encode_documents(self, texts: list[str]) -> list[list[float]]: ...

    def encode_query(self, text: str) -> list[float]: ...


class Embedder:
    """Wraps a sentence-transformers model. Construction triggers the load."""

    dim = EMBED_DIM

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(_MODEL_NAME, device="cpu")

    def encode_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vecs = self._model.encode(
            texts, normalize_embeddings=True, batch_size=64, show_progress_bar=False
        )
        return [v.tolist() for v in vecs]

    def encode_query(self, text: str) -> list[float]:
        vec = self._model.encode(
            _QUERY_INSTRUCTION + text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vec.tolist()


_instance: Embedder | None = None
_lock = threading.Lock()


def get_embedder() -> Embedder:
    """Return the process-wide embedder, building it once on first call."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = Embedder()
    return _instance
