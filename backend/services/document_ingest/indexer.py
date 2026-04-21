"""Indexer for the ChromaDB ``"evidence"`` collection.

This module is the *only* place where ingest pipeline code talks to the
vector store. Keeping the surface tiny (``upsert``, ``delete_document``,
``query``) lets unit tests inject a fake collection without spinning up
ChromaDB.

The collection is reused across documents — every chunk row carries
``doc_id`` and ``chunk_index`` so we can scope retrieval / deletion to a
single uploaded file.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Protocol

from .chunker import Chunk

logger = logging.getLogger(__name__)

EVIDENCE_COLLECTION = "evidence"


class _Collection(Protocol):
    """Subset of chromadb's Collection API we actually use."""

    def add(
        self,
        documents: List[str],
        ids: List[str],
        metadatas: List[dict],
    ) -> None: ...

    def delete(self, ids: Optional[List[str]] = None, where: Optional[dict] = None) -> None: ...

    def query(
        self,
        query_texts: List[str],
        n_results: int,
        where: Optional[dict] = None,
    ) -> dict: ...


def _chunk_id(doc_id: str, index: int) -> str:
    """Stable, human-readable chunk id (``{doc_id}::chunk-{N}``)."""
    return f"{doc_id}::chunk-{index}"


class EvidenceIndexer:
    """Persists evidence chunks to a ChromaDB collection.

    The constructor takes an *optional* collection so tests can pass a
    fake; in production it lazily resolves the real one via
    :class:`repositories.vector_store.VectorStore`.
    """

    def __init__(self, collection: Optional[_Collection] = None) -> None:
        self._collection = collection

    def _resolve(self) -> Optional[_Collection]:
        if self._collection is not None:
            return self._collection
        try:
            from repositories.vector_store import VectorStore

            self._collection = VectorStore().get_collection(EVIDENCE_COLLECTION)
            return self._collection
        except Exception as exc:
            # ChromaDB unavailable (offline tests, missing dep) — degrade
            # gracefully so upload still succeeds without indexing.
            logger.warning(
                "evidence indexer: vector store unavailable, skipping indexing: %s",
                exc,
            )
            return None

    def upsert(
        self,
        doc_id: str,
        chunks: List[Chunk],
        *,
        filename: str,
        mime_type: str,
    ) -> List[str]:
        """Index *chunks* and return the persisted chunk ids.

        Re-indexing the same ``doc_id`` first deletes prior rows so the
        store stays consistent when a document is re-uploaded after edit.
        """
        if not chunks:
            return []

        collection = self._resolve()
        ids = [_chunk_id(doc_id, c.index) for c in chunks]

        if collection is None:
            return ids  # caller still gets ids; storage is the source of truth

        try:
            self.delete_document(doc_id)
        except Exception as exc:  # pragma: no cover — defensive only
            logger.warning("evidence indexer: pre-delete failed for %s: %s", doc_id, exc)

        documents = [c.text for c in chunks]
        metadatas = [
            {
                "doc_id": doc_id,
                "chunk_index": c.index,
                "filename": filename,
                "mime_type": mime_type,
            }
            for c in chunks
        ]

        try:
            collection.add(documents=documents, ids=ids, metadatas=metadatas)
            logger.info(
                "evidence indexer: upserted doc_id=%s chunks=%d",
                doc_id, len(chunks),
            )
        except Exception as exc:
            logger.warning(
                "evidence indexer: upsert failed for doc_id=%s: %s",
                doc_id, exc,
            )
        return ids

    def delete_document(self, doc_id: str) -> None:
        """Remove every chunk belonging to *doc_id*. No-op if none exist."""
        collection = self._resolve()
        if collection is None:
            return
        collection.delete(where={"doc_id": doc_id})

    def query(self, text: str, *, top_k: int = 5, doc_id: Optional[str] = None) -> List[dict]:
        """Cosine-similarity search inside the evidence collection.

        When *doc_id* is given the search is constrained to chunks of
        that single document — useful for "what does this policy say
        about X?" interactions in the chatbot.
        """
        collection = self._resolve()
        if collection is None:
            return []

        where = {"doc_id": doc_id} if doc_id else None
        try:
            raw = collection.query(
                query_texts=[text],
                n_results=top_k,
                where=where,
            )
        except Exception as exc:
            logger.warning("evidence indexer: query failed: %s", exc)
            return []

        out: List[dict] = []
        documents = (raw or {}).get("documents") or [[]]
        metadatas = (raw or {}).get("metadatas") or [[]]
        distances = (raw or {}).get("distances") or [[]]
        for i, doc in enumerate(documents[0]):
            meta = metadatas[0][i] if metadatas[0] else {}
            score = 1.0
            if distances and distances[0]:
                score = round(1 - distances[0][i], 4)
            out.append({
                "text": doc,
                "score": score,
                "doc_id": meta.get("doc_id"),
                "chunk_index": meta.get("chunk_index"),
                "filename": meta.get("filename"),
            })
        return out
