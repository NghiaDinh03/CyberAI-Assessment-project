"""Unit & Integration tests for BAAI/bge-m3 embedding and ChromaDB vector store indexing."""

import pytest
from repositories.vector_store import VectorStore, BgeM3EmbeddingFunction


def test_bge_m3_embedding_dimension():
    """Verify BgeM3EmbeddingFunction produces 1024-dimensional vectors."""
    ef = BgeM3EmbeddingFunction(model_name="bge-m3")
    texts = [
        "Chính sách bảo đảm an toàn thông tin ISO 27001",
        "Quy trình quản lý mật khẩu và xác thực 2 yếu tố MFA",
    ]
    embeddings = ef(texts)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 1024
    assert len(embeddings[1]) == 1024


def test_vector_store_bge_m3_indexing_and_search(tmp_path):
    """Verify VectorStore indexes and retrieves with bge-m3 semantic similarity."""
    vs = VectorStore(persist_dir=str(tmp_path / "test_vec_store"))
    coll = vs.get_collection(domain="test_domain")
    assert coll.metadata.get("embedding_model") == "bge-m3"

    # Add sample chunks
    coll.add(
        documents=[
            "A.5.17 Xác thực người dùng và mật khẩu mạnh bắt buộc tối thiểu 12 ký tự.",
            "A.8.20 Bảo mật mạng và phân vùng mạng firewall DMZ.",
            "A.8.24 Sử dụng mật mã và mã hóa dữ liệu lưu trữ AES-256.",
        ],
        ids=["chunk_1", "chunk_2", "chunk_3"],
        metadatas=[
            {"source": "iso_a5", "file": "iso27001.md", "chunk_index": 0},
            {"source": "iso_a8_network", "file": "iso27001.md", "chunk_index": 1},
            {"source": "iso_a8_crypto", "file": "iso27001.md", "chunk_index": 2},
        ],
    )

    # Search for password / authentication
    results = vs.search("chính sách mật khẩu người dùng", top_k=1, domain="test_domain")
    assert len(results) >= 1
    top_doc = results[0]
    assert "A.5.17" in top_doc["text"]
    assert top_doc["score"] > 0.4


def test_vector_store_auto_migration_on_conflict(tmp_path):
    """Verify that if an existing collection has a conflicting embedding function or dimension,
    VectorStore seamlessly recreates and migrates it to bge-m3.
    """
    import chromadb

    persist_dir = str(tmp_path / "migration_store")
    raw_client = chromadb.PersistentClient(path=persist_dir)

    # Simulate legacy 384-dim collection created without embedding_model tag
    legacy_col = raw_client.create_collection("legacy_domain", metadata={"hnsw:space": "cosine"})
    legacy_col.add(documents=["legacy text"], ids=["leg_1"])
    assert legacy_col.count() == 1

    # Now open with VectorStore (bge-m3)
    vs = VectorStore(persist_dir=persist_dir)
    migrated_col = vs.get_collection("legacy_domain")
    assert migrated_col.metadata.get("embedding_model") == "bge-m3"
    assert migrated_col.count() == 0  # Cleaned up and ready for re-indexing
