"""ChromaDB vector store for document embeddings."""

import uuid
import chromadb
from langchain_openai import OpenAIEmbeddings

from app.config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL, OPENAI_API_KEY, RETRIEVAL_TOP_K

# Singleton instances
_chroma_client: chromadb.PersistentClient | None = None
_embeddings: OpenAIEmbeddings | None = None


def get_chroma_client() -> chromadb.PersistentClient:
    """Get or create persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return _chroma_client


def get_embeddings() -> OpenAIEmbeddings:
    """Get or create OpenAI embeddings instance."""
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            openai_api_key=OPENAI_API_KEY,
        )
    return _embeddings


def get_or_create_collection(collection_name: str = "documents") -> chromadb.Collection:
    """Get or create a ChromaDB collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks_to_store(
    chunks: list[dict],
    collection_name: str = "documents",
) -> int:
    """Embed and store document chunks in ChromaDB.

    Args:
        chunks: List of dicts with 'content', 'chunk_index', 'source_file' keys.
        collection_name: ChromaDB collection name.

    Returns:
        Number of chunks stored.
    """
    if not chunks:
        return 0

    collection = get_or_create_collection(collection_name)
    embeddings = get_embeddings()

    texts = [c["content"] for c in chunks]
    embedded = embeddings.embed_documents(texts)

    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [
        {
            "source_file": c["source_file"],
            "chunk_index": c["chunk_index"],
        }
        for c in chunks
    ]

    collection.add(
        ids=ids,
        embeddings=embedded,
        documents=texts,
        metadatas=metadatas,
    )
    return len(chunks)


def query_store(
    query: str,
    top_k: int = RETRIEVAL_TOP_K,
    collection_name: str = "documents",
) -> list[dict]:
    """Query vector store for relevant chunks.

    Returns list of dicts with 'content', 'source_file', 'chunk_index', 'distance'.
    """
    collection = get_or_create_collection(collection_name)
    if collection.count() == 0:
        return []

    embeddings = get_embeddings()
    query_embedding = embeddings.embed_query(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    retrieved = []
    for i in range(len(results["ids"][0])):
        retrieved.append({
            "content": results["documents"][0][i],
            "source_file": results["metadatas"][0][i]["source_file"],
            "chunk_index": results["metadatas"][0][i]["chunk_index"],
            "distance": results["distances"][0][i],
        })
    return retrieved


def collection_has_documents(collection_name: str = "documents") -> bool:
    """Check if collection has any documents."""
    collection = get_or_create_collection(collection_name)
    return collection.count() > 0


def reset_store(collection_name: str = "documents") -> None:
    """Delete and recreate collection. For testing only."""
    client = get_chroma_client()
    try:
        client.delete_collection(collection_name)
    except ValueError:
        pass
