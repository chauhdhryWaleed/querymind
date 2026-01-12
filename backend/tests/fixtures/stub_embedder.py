"""Deterministic stub embedder for tests (no model download).

Bag-of-words hashing into 384 dims, L2-normalized. Texts that share tokens get
higher cosine similarity, so vector search behaves meaningfully and
reproducibly — exactly what the retrieval scoring tests need (PLAN §16).
"""

from __future__ import annotations

import hashlib
import math
import re

_DIM = 384
_TOKEN = re.compile(r"[a-z0-9_]+")


def _bucket(token: str) -> int:
    return int(hashlib.md5(token.encode()).hexdigest(), 16) % _DIM


def _embed(text: str) -> list[float]:
    vec = [0.0] * _DIM
    for tok in _TOKEN.findall(text.lower()):
        vec[_bucket(tok)] += 1.0
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


class StubEmbedder:
    dim = _DIM

    def encode_documents(self, texts: list[str]) -> list[list[float]]:
        return [_embed(t) for t in texts]

    def encode_query(self, text: str) -> list[float]:
        return _embed(text)
