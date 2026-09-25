"""Vector Store — Semantic chunking with header hierarchy and BAAI/bge-m3 cosine similarity scoring."""

import asyncio
import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
import httpx
import logging
from pathlib import Path
from typing import List, Optional
from core.config import settings

logger = logging.getLogger(__name__)

DOMAIN_FILE_MAP = {
    "iso27001":  ["iso27001_annex_a.md", "iso27002_2022.md", "assessment_criteria.md"],
    "tcvn11930": ["tcvn_11930_2017.md", "nd85_2016_cap_do_httt.md", "assessment_criteria.md"],
    "nd13":      ["nghi_dinh_13_2023_bvdlcn.md", "luat_an_ninh_mang_2018.md"],
    "nist_csf":  ["nist_csf_2.md", "nist_sp800_53.md"],
    "pci_dss":   ["pci_dss_4.md"],
    "hipaa":     ["hipaa_security_rule.md"],
    "gdpr":      ["gdpr_compliance.md"],
    "soc2":      ["soc2_trust_criteria.md"],
}


class BgeM3EmbeddingFunction(EmbeddingFunction[Documents]):
    """ChromaDB embedding function that calls Ollama /api/embed using BAAI/bge-m3 (dim 1024)."""

    def __init__(self, model_name: Optional[str] = None, ollama_url: Optional[str] = None):
        self.model_name = model_name or getattr(settings, "EMBEDDING_MODEL_NAME", "bge-m3")
        self.ollama_url = ollama_url or getattr(settings, "OLLAMA_URL", "http://ollama:11434")
        self._batch_size = 32
        self._timeout = 60.0
        self._fallback_ef = None

    def name(self) -> str:
        return f"ollama-{self.model_name}"

    def get_config(self) -> dict:
        return {"model_name": self.model_name, "ollama_url": self.ollama_url}

    def _get_candidate_urls(self) -> List[str]:
        primary = (self.ollama_url or "http://ollama:11434").rstrip("/")
        candidates = [primary]
        for fallback in ["http://host.docker.internal:11434", "http://ollama:11434", "http://127.0.0.1:11434"]:
            if fallback not in candidates:
                candidates.append(fallback)
        return candidates

    def __call__(self, input: Documents) -> Embeddings:
        if not input:
            return []

        all_embeddings: List[List[float]] = []
        candidate_urls = self._get_candidate_urls()

        for i in range(0, len(input), self._batch_size):
            batch = input[i : i + self._batch_size]
            batch_success = False

            for url in candidate_urls:
                try:
                    with httpx.Client(timeout=self._timeout) as client:
                        resp = client.post(
                            f"{url}/api/embed",
                            json={"model": self.model_name, "input": batch},
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            embeddings = data.get("embeddings", [])
                            if embeddings and len(embeddings) == len(batch):
                                all_embeddings.extend(embeddings)
                                batch_success = True
                                break
                except Exception as exc:
                    logger.debug(f"[BgeM3Embedding] Request to {url} failed: {exc}")
                    continue

            if not batch_success:
                logger.warning(
                    f"[BgeM3Embedding] Ollama embed failed for batch of {len(batch)} items. Falling back to synthetic 1024-dim embedding."
                )
                try:
                    if self._fallback_ef is None:
                        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
                        self._fallback_ef = DefaultEmbeddingFunction()
                    fallback_res = self._fallback_ef(batch)
                    for vec in fallback_res:
                        v_list = list(vec)
                        if len(v_list) < 1024:
                            v_list = v_list + [0.0] * (1024 - len(v_list))
                        elif len(v_list) > 1024:
                            v_list = v_list[:1024]
                        all_embeddings.append(v_list)
                except Exception as exc:
                    logger.error(f"[BgeM3Embedding] Fallback embedding failed: {exc}")
                    all_embeddings.extend([[0.0] * 1024 for _ in batch])

        return all_embeddings


class VectorStore:
    def __init__(self, persist_dir: str = None):
        persist_dir = persist_dir or settings.VECTOR_STORE_PATH
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.embedding_fn = BgeM3EmbeddingFunction(
            model_name=getattr(settings, "EMBEDDING_MODEL_NAME", "bge-m3"),
            ollama_url=getattr(settings, "OLLAMA_URL", "http://ollama:11434"),
        )
        # Dictionary mapping domain name to its collection
        self.collections = {}
        self._initialized = {}

    def get_collection(self, domain: str = "iso_documents", organisation: str = ""):
        """Get or create a collection for a specific domain, isolated by organisation if provided.
        Automatically migrates legacy collections if an embedding function conflict or dimension mismatch is detected.
        """
        col_name = domain
        if organisation:
            # Clean organisation name to make it a valid ChromaDB collection name
            clean_org = "".join([c if c.isalnum() or c in ("_", "-") else "_" for c in organisation])
            col_name = f"org_{clean_org}_{domain}"
            if len(col_name) > 63:
                col_name = col_name[:63]

        if col_name not in self.collections:
            recreate = False
            try:
                existing_col = self.client.get_collection(name=col_name)
                meta = existing_col.metadata or {}
                if meta.get("embedding_model") != self.embedding_fn.model_name:
                    logger.warning(
                        f"Collection '{col_name}' uses legacy embedding. Recreating with {self.embedding_fn.model_name} (1024-dim)..."
                    )
                    recreate = True
            except Exception:
                recreate = False

            if recreate:
                try:
                    self.client.delete_collection(name=col_name)
                except Exception as exc:
                    logger.debug(f"Failed to delete old collection {col_name}: {exc}")

            try:
                coll = self.client.get_or_create_collection(
                    name=col_name,
                    embedding_function=self.embedding_fn,
                    metadata={"hnsw:space": "cosine", "embedding_model": self.embedding_fn.model_name},
                )
            except Exception as exc:
                logger.warning(f"Error getting collection {col_name}, forcing recreation: {exc}")
                try:
                    self.client.delete_collection(name=col_name)
                except Exception:
                    pass
                coll = self.client.create_collection(
                    name=col_name,
                    embedding_function=self.embedding_fn,
                    metadata={"hnsw:space": "cosine", "embedding_model": self.embedding_fn.model_name},
                )

            self.collections[col_name] = coll
            self._initialized[col_name] = False
        return self.collections[col_name]

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

    def index_documents(self, docs_dir: str = None, domain: str = "iso_documents", organisation: str = ""):
        docs_dir = docs_dir or settings.ISO_DOCS_PATH
        docs_path = Path(docs_dir)

        if not docs_path.exists():
            return {"status": "error", "message": f"Directory not found: {docs_dir}"}

        collection = self.get_collection(domain, organisation)
        col_name = domain
        if organisation:
            clean_org = "".join([c if c.isalnum() or c in ("_", "-") else "_" for c in organisation])
            col_name = f"org_{clean_org}_{domain}"
            if len(col_name) > 63:
                col_name = col_name[:63]

        all_md_files = list(docs_path.glob("*.md"))
        if not all_md_files:
            return {"status": "error", "message": "No markdown files found"}

        # Filter files by domain map if applicable
        if domain in DOMAIN_FILE_MAP:
            target_names = set(DOMAIN_FILE_MAP[domain])
            md_files = [f for f in all_md_files if f.name in target_names]
            if not md_files:
                md_files = all_md_files
        else:
            md_files = all_md_files

        all_chunks, all_ids, all_metadata = [], [], []

        for file_path in md_files:
            content = file_path.read_text(encoding="utf-8")
            chunks = self._chunk_text(content)
            filename = file_path.stem
            first_line = content.split('\n')[0].strip().lstrip('#').strip()

            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_ids.append(f"{domain}_{filename}_{i}")
                all_metadata.append({
                    "source": filename, "file": file_path.name,
                    "chunk_index": i, "total_chunks": len(chunks),
                    "doc_title": first_line[:100],
                    "domain": domain,
                })

        try:
            existing = collection.get()
            if existing and existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception as exc:
            logger.debug(f"Pre-delete failed on {col_name}: {exc}")

        try:
            for i in range(0, len(all_chunks), 100):
                end = min(i + 100, len(all_chunks))
                collection.add(documents=all_chunks[i:end], ids=all_ids[i:end], metadatas=all_metadata[i:end])
        except Exception as exc:
            if "dimension" in str(exc).lower() or "invalidargumenterror" in type(exc).__name__.lower():
                logger.warning(f"Dimension mismatch on add for {col_name}. Recreating collection...")
                try:
                    self.client.delete_collection(name=col_name)
                except Exception:
                    pass
                collection = self.client.create_collection(
                    name=col_name,
                    embedding_function=self.embedding_fn,
                    metadata={"hnsw:space": "cosine", "embedding_model": self.embedding_fn.model_name},
                )
                self.collections[col_name] = collection
                for i in range(0, len(all_chunks), 100):
                    end = min(i + 100, len(all_chunks))
                    collection.add(documents=all_chunks[i:end], ids=all_ids[i:end], metadatas=all_metadata[i:end])
            else:
                raise

        self._initialized[col_name] = True
        logger.info(f"Indexed {len(md_files)} files into {col_name} with {self.embedding_fn.model_name} -> {len(all_chunks)} chunks")
        return {"status": "ok", "files": len(md_files), "chunks": len(all_chunks),
                "file_names": [f.name for f in md_files]}

    def ensure_indexed(self, domain: str = "iso_documents", organisation: str = ""):
        collection = self.get_collection(domain, organisation)
        col_name = domain
        if organisation:
            clean_org = "".join([c if c.isalnum() or c in ("_", "-") else "_" for c in organisation])
            col_name = f"org_{clean_org}_{domain}"
            if len(col_name) > 63:
                col_name = col_name[:63]

        if not self._initialized.get(col_name, False):
            if collection.count() == 0:
                self.index_documents(domain=domain, organisation=organisation)
            else:
                self._initialized[col_name] = True

    def search(self, query: str, top_k: int = 5, domain: str = "iso_documents", organisation: str = "") -> list:
        self.ensure_indexed(domain, organisation)
        collection = self.get_collection(domain, organisation)

        if collection.count() == 0:
            return []

        results = collection.query(query_texts=[query], n_results=min(top_k, collection.count()))

        docs = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                score = 1.0
                if results.get("distances") and results["distances"][0]:
                    score = round(1 - results["distances"][0][i], 4)
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                chunk_id = (
                    results["ids"][0][i]
                    if results.get("ids") and results["ids"][0] and i < len(results["ids"][0])
                    else f"{metadata.get('domain', domain)}_{metadata.get('source', 'unknown')}_{metadata.get('chunk_index', i)}"
                )
                docs.append({
                    "id": chunk_id,
                    "text": doc, "score": score, "source": metadata.get("source", "unknown"),
                    "file": metadata.get("file", ""), "doc_title": metadata.get("doc_title", ""),
                    "chunk_index": metadata.get("chunk_index", 0),
                })

        docs.sort(key=lambda x: x["score"], reverse=True)
        return docs

    async def search_async(self, query: str, top_k: int = 5, domain: str = "iso_documents", organisation: str = "") -> list:
        return await asyncio.to_thread(self.search, query, top_k, domain, organisation)

    def multi_query_search(self, query: str, top_k: int = 5, domain: str = "iso_documents", organisation: str = "") -> list:
        queries = [query]
        if "iso" in query.lower() or "tcvn" in query.lower():
            queries.append(f"tiêu chuẩn {query}")
        if "đánh giá" in query.lower():
            queries.append(query.replace("đánh giá", "kiểm toán"))

        seen_ids = set()
        all_results = []
        for q in queries:
            for r in self.search(q, top_k=top_k, domain=domain, organisation=organisation):
                result_id = f"{r['source']}_{r['chunk_index']}"
                if result_id not in seen_ids:
                    seen_ids.add(result_id)
                    all_results.append(r)

        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:top_k]


# Singleton instance for evaluation and direct repository access
vector_store = VectorStore()

