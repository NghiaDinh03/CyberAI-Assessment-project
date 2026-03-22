"""Vector Store — Semantic chunking with header hierarchy and cosine similarity scoring."""

import chromadb
import os
import re
import logging
from pathlib import Path
from core.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, persist_dir: str = None):
        persist_dir = persist_dir or settings.VECTOR_STORE_PATH
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="iso_documents", metadata={"hnsw:space": "cosine"})
        self._initialized = False

    def _chunk_text(self, text: str, chunk_size: int = 600, overlap: int = 150) -> list:
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_length = 0
        current_headers = []

        for line in lines:
            if line.startswith('# '):
                current_headers = [line.strip()]
            elif line.startswith('## '):
                current_headers = current_headers[:1] + [line.strip()]
            elif line.startswith('### '):
                current_headers = current_headers[:2] + [line.strip()]

            current_chunk.append(line)
            current_length += len(line)

            is_natural_break = (
                current_length >= chunk_size
                and not line.startswith('|')
                and not line.startswith('- ')
                and not line.startswith('  ')
            )

            if is_natural_break:
                chunk_text = '\n'.join(current_chunk)
                if current_headers and not chunk_text.strip().startswith('#'):
                    chunk_text = f"[Context: {' > '.join(current_headers)}]\n{chunk_text}"
                chunks.append(chunk_text.strip())

                overlap_lines, overlap_len = [], 0
                for l in reversed(current_chunk):
                    overlap_lines.insert(0, l)
                    overlap_len += len(l)
                    if overlap_len >= overlap:
                        break
                current_chunk = overlap_lines
                current_length = overlap_len

        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            if chunk_text.strip():
                if current_headers and not chunk_text.strip().startswith('#'):
                    chunk_text = f"[Context: {' > '.join(current_headers)}]\n{chunk_text}"
                chunks.append(chunk_text.strip())

        return chunks

    def index_documents(self, docs_dir: str = None):
        docs_dir = docs_dir or settings.ISO_DOCS_PATH
        docs_path = Path(docs_dir)

        if not docs_path.exists():
            return {"status": "error", "message": f"Directory not found: {docs_dir}"}

        md_files = list(docs_path.glob("*.md"))
        if not md_files:
            return {"status": "error", "message": "No markdown files found"}

        all_chunks, all_ids, all_metadata = [], [], []

        for file_path in md_files:
            content = file_path.read_text(encoding="utf-8")
            chunks = self._chunk_text(content)
            filename = file_path.stem
            first_line = content.split('\n')[0].strip().lstrip('#').strip()

            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_ids.append(f"{filename}_{i}")
                all_metadata.append({
                    "source": filename, "file": file_path.name,
                    "chunk_index": i, "total_chunks": len(chunks),
                    "doc_title": first_line[:100],
                })

        existing = self.collection.get()
        if existing["ids"]:
            self.collection.delete(ids=existing["ids"])

        for i in range(0, len(all_chunks), 100):
            end = min(i + 100, len(all_chunks))
            self.collection.add(documents=all_chunks[i:end], ids=all_ids[i:end], metadatas=all_metadata[i:end])

        self._initialized = True
        logger.info(f"Indexed {len(md_files)} files → {len(all_chunks)} chunks")
        return {"status": "ok", "files": len(md_files), "chunks": len(all_chunks),
                "file_names": [f.name for f in md_files]}

    def ensure_indexed(self):
        if not self._initialized:
            if self.collection.count() == 0:
                self.index_documents()
            else:
                self._initialized = True

    def search(self, query: str, top_k: int = 5) -> list:
        self.ensure_indexed()
        if self.collection.count() == 0:
            return []

        results = self.collection.query(query_texts=[query], n_results=min(top_k, self.collection.count()))

        docs = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                score = 1.0
                if results.get("distances") and results["distances"][0]:
                    score = round(1 - results["distances"][0][i], 4)
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                docs.append({
                    "text": doc, "score": score, "source": metadata.get("source", "unknown"),
                    "file": metadata.get("file", ""), "doc_title": metadata.get("doc_title", ""),
                    "chunk_index": metadata.get("chunk_index", 0),
                })

        docs.sort(key=lambda x: x["score"], reverse=True)
        return docs

    def multi_query_search(self, query: str, top_k: int = 5) -> list:
        queries = [query]
        if "iso" in query.lower() or "tcvn" in query.lower():
            queries.append(f"tiêu chuẩn {query}")
        if "đánh giá" in query.lower():
            queries.append(query.replace("đánh giá", "kiểm toán"))

        seen_ids = set()
        all_results = []
        for q in queries:
            for r in self.search(q, top_k=top_k):
                result_id = f"{r['source']}_{r['chunk_index']}"
                if result_id not in seen_ids:
                    seen_ids.add(result_id)
                    all_results.append(r)

        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:top_k]
