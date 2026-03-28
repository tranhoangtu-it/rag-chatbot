"""RAG query chain with streaming and source citations."""

from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from app.config import OPENAI_API_KEY, CHAT_MODEL, RETRIEVAL_TOP_K
from app.vector_store import query_store

_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create async OpenAI client."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _client


# Conversation memory — simple in-memory dict keyed by session_id
_conversations: dict[str, list[dict]] = {}
MAX_MEMORY_WINDOW = 5
MAX_SESSIONS = 100


def get_conversation(session_id: str) -> list[dict]:
    """Get conversation history for a session, limited to last k turns."""
    return _conversations.get(session_id, [])[-MAX_MEMORY_WINDOW * 2:]


def add_to_conversation(session_id: str, role: str, content: str) -> None:
    """Add a message to conversation history. Evicts oldest sessions if limit exceeded."""
    if session_id not in _conversations:
        # Evict oldest session if at capacity
        if len(_conversations) >= MAX_SESSIONS:
            oldest = next(iter(_conversations))
            del _conversations[oldest]
        _conversations[session_id] = []
    _conversations[session_id].append({"role": role, "content": content})
    # Trim to window size to prevent per-session growth
    _conversations[session_id] = _conversations[session_id][-(MAX_MEMORY_WINDOW * 2):]


def build_rag_prompt(query: str, context_chunks: list[dict]) -> str:
    """Build the RAG prompt with retrieved context and source references."""
    if not context_chunks:
        return (
            "No relevant documents found. Please let the user know that "
            "you don't have information about their question and suggest "
            "they upload relevant documents.\n\n"
            f"User question: {query}"
        )

    context_parts = []
    for i, chunk in enumerate(context_chunks):
        source = chunk["source_file"]
        idx = chunk["chunk_index"]
        context_parts.append(f"[Source {i+1}: {source}, chunk {idx}]\n{chunk['content']}")

    context_text = "\n\n---\n\n".join(context_parts)

    return (
        "You are a helpful customer support assistant. Answer the user's question "
        "based ONLY on the provided context. If the context doesn't contain "
        "enough information, say so honestly.\n\n"
        "After your answer, list the sources you used in this format:\n"
        "**Sources:**\n"
        "- Source 1: filename, chunk N\n\n"
        f"Context:\n{context_text}\n\n"
        f"User question: {query}"
    )


async def query_rag(
    question: str,
    session_id: str = "default",
    collection_name: str = "documents",
) -> dict:
    """Run RAG query and return answer with sources (non-streaming)."""
    # Retrieve relevant chunks
    chunks = query_store(question, top_k=RETRIEVAL_TOP_K, collection_name=collection_name)

    # Build messages with conversation history
    history = get_conversation(session_id)
    system_prompt = build_rag_prompt(question, chunks)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    # Call OpenAI
    client = get_openai_client()
    response = await client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.3,
    )

    answer = response.choices[0].message.content or ""

    # Update conversation memory
    add_to_conversation(session_id, "user", question)
    add_to_conversation(session_id, "assistant", answer)

    # Return answer with source metadata
    sources = [
        {"source_file": c["source_file"], "chunk_index": c["chunk_index"], "distance": c["distance"]}
        for c in chunks
    ]
    return {"answer": answer, "sources": sources, "session_id": session_id}


async def query_rag_stream(
    question: str,
    session_id: str = "default",
    collection_name: str = "documents",
) -> AsyncGenerator[str, None]:
    """Run RAG query with streaming response. Yields text chunks.

    Final chunk is a JSON object with sources metadata.
    """
    import json

    chunks = query_store(question, top_k=RETRIEVAL_TOP_K, collection_name=collection_name)

    history = get_conversation(session_id)
    system_prompt = build_rag_prompt(question, chunks)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    client = get_openai_client()
    stream = await client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.3,
        stream=True,
    )

    full_answer = []
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            full_answer.append(delta.content)
            yield delta.content

    # Update memory
    answer_text = "".join(full_answer)
    add_to_conversation(session_id, "user", question)
    add_to_conversation(session_id, "assistant", answer_text)

    # Yield sources as final JSON event
    sources = [
        {"source_file": c["source_file"], "chunk_index": c["chunk_index"], "distance": c["distance"]}
        for c in chunks
    ]
    yield "\n<<SOURCES>>" + json.dumps(sources)
