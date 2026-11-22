"""Retrieval service for the requirements collections used during ticket triage."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

from app.services.interfaces import RequirementsRetrieverInterface

load_dotenv(Path(__file__).resolve().parents[4] / ".env")


DEFAULT_COLLECTIONS = (
    "Modos_Operacao_CBL",
    "Modos_Operacao_TWC",
)


class RequirementsRetriever(RequirementsRetrieverInterface):
    """Busca os trechos dos requisitos mais relevantes dos documentos de modos de operação."""

    def __init__(
        self,
        collection_names: Sequence[str] = DEFAULT_COLLECTIONS,
    ) -> None:
        self._collection_names = tuple(collection_names)
        self._embeddings = OllamaEmbeddings(
            base_url=str(os.getenv("LOCAL_MODELS_BASE_URL")),
            model=str(os.getenv("EMBEDDING_MODEL")),
        )
        self._vector_stores = {
            name: Chroma(
                collection_name=name,
                embedding_function=self._embeddings,
                persist_directory=str(os.getenv("CHROMA_PERSIST_DIRECTORY")),
            )
            for name in self._collection_names
        }

    def search(self, query: str, k: int = 1) -> list[Document]:
        """Return the most relevant excerpts from all configured collections."""
        if not query.strip():
            return []
        if k <= 0:
            return []

        results: list[tuple[Document, float]] = []
        for collection_name, vector_store in self._vector_stores.items():
            for document, score in vector_store.similarity_search_with_score(
                query, k=k
            ):
                results.append(
                    (
                        Document(
                            page_content=document.page_content,
                            metadata={
                                **document.metadata,
                                "collection": collection_name,
                                "similarity_score": score,
                            },
                        ),
                        score,
                    )
                )

        results.sort(key=lambda item: item[1])
        return [document for document, _ in results[:k]]
