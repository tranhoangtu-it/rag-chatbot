"""Load demo dataset into vector store on first startup."""

import os
from pathlib import Path

from app.document_processor import chunk_text
from app.vector_store import add_chunks_to_store, collection_has_documents

DEMO_DIR = Path(__file__).parent.parent / "data" / "demo"


def load_demo_data(collection_name: str = "documents") -> int:
    """Load demo text files into vector store if collection is empty.

    Returns number of chunks loaded (0 if already loaded).
    """
    if collection_has_documents(collection_name):
        return 0

    total_chunks = 0
    for filepath in DEMO_DIR.glob("*.txt"):
        text = filepath.read_text(encoding="utf-8")
        chunks = chunk_text(text)
        for chunk in chunks:
            chunk["source_file"] = filepath.name
        total_chunks += add_chunks_to_store(chunks, collection_name)

    return total_chunks
