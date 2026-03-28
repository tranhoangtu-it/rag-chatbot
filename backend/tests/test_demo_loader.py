"""Tests for demo data loader."""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

_temp_dir = tempfile.mkdtemp()
os.environ["CHROMA_PERSIST_DIR"] = _temp_dir

import app.vector_store as vs
from app.demo_loader import load_demo_data


def _fake_embed_documents(texts):
    return [[0.1] * 384 for _ in texts]


@pytest.fixture(autouse=True)
def _reset():
    vs._chroma_client = None
    vs._embeddings = None
    vs.CHROMA_PERSIST_DIR = _temp_dir
    yield
    try:
        vs.reset_store("test_demo")
    except Exception:
        pass


@pytest.fixture
def mock_embeddings():
    mock = MagicMock()
    mock.embed_documents = _fake_embed_documents
    with patch.object(vs, "get_embeddings", return_value=mock):
        yield mock


def test_load_demo_data_populates_store(mock_embeddings):
    """Demo loader should populate empty store with chunks."""
    count = load_demo_data(collection_name="test_demo")
    assert count > 0
    assert vs.collection_has_documents("test_demo") is True


def test_load_demo_data_skips_if_populated(mock_embeddings):
    """Demo loader should skip if store already has documents."""
    load_demo_data(collection_name="test_demo")
    # Second call should return 0
    count = load_demo_data(collection_name="test_demo")
    assert count == 0
