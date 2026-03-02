import chromadb
import os
import re
from pathlib import Path


class VectorStore:
    def __init__(self, persist_dir: str = None):
        persist_dir = persist_dir or os.getenv("VECTOR_STORE_PATH", "/data/vector_store")
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="iso_documents",
            metadata={"hnsw:space": "cosine"}
        )
        self._initialized = False

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> list:
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_length = 0
        current_header = ""

        for line in lines:
            if line.startswith('##'):
                current_header = line.strip()

            current_chunk.append(line)
            current_length += len(line)

            if current_length >= chunk_size:
                chunk_text = '\n'.join(current_chunk)
                if current_header and not chunk_text.startswith('#'):
                    chunk_text = f"{current_header}\n{chunk_text}"
                chunks.append(chunk_text.strip())

                overlap_lines = []
                overlap_len = 0
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
                chunks.append(chunk_text.strip())

        return chunks

    def index_documents(self, docs_dir: str = None):
        docs_dir = docs_dir or os.getenv("ISO_DOCS_PATH", "/data/iso_documents")
        docs_path = Path(docs_dir)

        if not docs_path.exists():
            return {"status": "error", "message": f"Directory not found: {docs_dir}"}

        md_files = list(docs_path.glob("*.md"))
        if not md_files:
            return {"status": "error", "message": "No markdown files found"}

        all_chunks = []
        all_ids = []
        all_metadata = []

        for file_path in md_files:
            content = file_path.read_text(encoding="utf-8")
            chunks = self._chunk_text(content)
            filename = file_path.stem

            for i, chunk in enumerate(chunks):
                chunk_id = f"{filename}_{i}"
                all_chunks.append(chunk)
                all_ids.append(chunk_id)
                all_metadata.append({
                    "source": filename,
                    "file": file_path.name,
                    "chunk_index": i
                })

        existing = self.collection.get()
        if existing["ids"]:
            self.collection.delete(ids=existing["ids"])

        batch_size = 100
        for i in range(0, len(all_chunks), batch_size):
            end = min(i + batch_size, len(all_chunks))
            self.collection.add(
                documents=all_chunks[i:end],
                ids=all_ids[i:end],
                metadatas=all_metadata[i:end]
            )

        self._initialized = True
        return {
            "status": "ok",
            "files": len(md_files),
            "chunks": len(all_chunks)
        }

    def ensure_indexed(self):
        if not self._initialized:
            count = self.collection.count()
            if count == 0:
                self.index_documents()
            else:
                self._initialized = True

    def search(self, query: str, top_k: int = 5) -> list:
        self.ensure_indexed()

        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, self.collection.count())
        )

        docs = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                score = 1.0
                if results.get("distances") and results["distances"][0]:
                    score = round(1 - results["distances"][0][i], 3)
                metadata = {}
                if results.get("metadatas") and results["metadatas"][0]:
                    metadata = results["metadatas"][0][i]
                docs.append({
                    "text": doc,
                    "score": score,
                    "source": metadata.get("source", "unknown"),
                    "file": metadata.get("file", "")
                })

        return docs
