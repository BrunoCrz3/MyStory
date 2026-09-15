"""Recuperacion local con TF-IDF (§8 capa L5, §20 punto 5).

Sin red y determinista. La interfaz queda lista para sustituir el indice por un
`EmbeddingProvider` real o por pgvector sin tocar el constructor de contexto.
"""

from __future__ import annotations

from typing import Protocol

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class Index(Protocol):
    """Contrato minimo de un indice de recuperacion."""

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]: ...


class Retriever:
    """Indice TF-IDF sobre los capitulos ya escritos."""

    def __init__(self, documents: list[str]) -> None:
        self.documents = [document for document in documents if document.strip()]

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        if top_k <= 0 or not self.documents or not query.strip():
            return []
        try:
            matrix = TfidfVectorizer().fit_transform([query, *self.documents])
        except ValueError:
            return []
        scores = cosine_similarity(matrix[0:1], matrix[1:])[0]
        ranked = sorted(zip(self.documents, scores, strict=True), key=lambda item: -item[1])
        return [(document, float(score)) for document, score in ranked[:top_k] if score > 0]
