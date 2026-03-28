"""Tests for ChromaDB vector store operations.

Uses a temporary ChromaDB directory and mocked OpenAI embeddings
to avoid API calls during testing.
"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# Override chroma dir before importing module
_temp_dir = tempfile.mkdtemp()
os.environ["CHROMA_PERSIST_DIR"] = _temp_dir

import app.vector_store as vs


def _fake_embed_documents(texts: list[str]) -> list[list[float]]:
    """Generate deterministic fake embeddings based on text length."""
    return [[float(len(t) % 100) / 100.0] * 384 for t in texts]


def _fake_embed_query(text: str) -> list[float]:
    """Generate deterministic fake query embedding."""
    return [float(len(text) % 100) / 100.0] * 384


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset module singletons and use temp dir for each test."""
    vs._chroma_client = None
    vs._embeddings = None
    vs.CHROMA_PERSIST_DIR = _temp_dir
    yield
    # Cleanup: reset store after each test
    try:
        vs.reset_store("test_collection")
    except Exception:
        pass


@pytest.fixture
def mock_embeddings():
    """Mock OpenAI embeddings to avoid API calls."""
    mock = MagicMock()
    mock.embed_documents = _fake_embed_documents
    mock.embed_query = _fake_embed_query
    with patch.object(vs, "get_embeddings", return_value=mock):
        yield mock


def _sample_chunks(n: int = 5, source: str = "test.pdf") -> list[dict]:
    """Generate sample chunks for testing."""
    return [
        {"content": f"Chunk {i} content about topic {i * 7}", "chunk_index": i, "source_file": source}
        for i in range(n)
    ]


def test_add_chunks_stores_documents(mock_embeddings):
    """Adding chunks should increase collection count."""
    chunks = _sample_chunks(3)
    stored = vs.add_chunks_to_store(chunks, collection_name="test_collection")
    assert stored == 3

    collection = vs.get_or_create_collection("test_collection")
    assert collection.count() == 3


def test_add_chunks_empty_list(mock_embeddings):
    """Adding empty list should return 0."""
    stored = vs.add_chunks_to_store([], collection_name="test_collection")
    assert stored == 0


def test_query_store_returns_results(mock_embeddings):
    """Querying after adding chunks should return relevant results."""
    chunks = _sample_chunks(5)
    vs.add_chunks_to_store(chunks, collection_name="test_collection")

    results = vs.query_store("topic", top_k=3, collection_name="test_collection")
    assert len(results) <= 3
    assert all("content" in r and "source_file" in r and "distance" in r for r in results)


def test_query_empty_store(mock_embeddings):
    """Querying empty store should return empty list."""
    results = vs.query_store("anything", collection_name="test_collection")
    assert results == []


def test_collection_has_documents(mock_embeddings):
    """Should correctly report whether collection has documents."""
    assert vs.collection_has_documents("test_collection") is False
    vs.add_chunks_to_store(_sample_chunks(2), collection_name="test_collection")
    assert vs.collection_has_documents("test_collection") is True


def test_reset_store(mock_embeddings):
    """Reset should clear all documents from collection."""
    vs.add_chunks_to_store(_sample_chunks(3), collection_name="test_collection")
    assert vs.collection_has_documents("test_collection") is True
    vs.reset_store("test_collection")
    assert vs.collection_has_documents("test_collection") is False
