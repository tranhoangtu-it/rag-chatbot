"""Tests for RAG query chain and chat endpoint.

Mocks OpenAI API calls and vector store to test logic without external deps.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.rag_chain import build_rag_prompt, get_conversation, add_to_conversation, _conversations


# --- Unit tests for prompt building ---


def test_build_rag_prompt_with_chunks():
    """Prompt should include context from retrieved chunks."""
    chunks = [
        {"content": "Refund policy is 30 days.", "source_file": "faq.pdf", "chunk_index": 0},
        {"content": "Contact support@test.com.", "source_file": "faq.pdf", "chunk_index": 1},
    ]
    prompt = build_rag_prompt("How do I get a refund?", chunks)
    assert "Refund policy is 30 days" in prompt
    assert "Source 1: faq.pdf" in prompt
    assert "Source 2: faq.pdf" in prompt
    assert "How do I get a refund?" in prompt


def test_build_rag_prompt_no_chunks():
    """Prompt should handle empty context gracefully."""
    prompt = build_rag_prompt("random question", [])
    assert "No relevant documents found" in prompt


# --- Unit tests for conversation memory ---


def test_conversation_memory():
    """Should store and retrieve conversation history."""
    _conversations.clear()
    add_to_conversation("test-session", "user", "Hello")
    add_to_conversation("test-session", "assistant", "Hi!")
    history = get_conversation("test-session")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["content"] == "Hi!"
    _conversations.clear()


def test_conversation_memory_window():
    """Should limit conversation to last k turns."""
    _conversations.clear()
    for i in range(20):
        add_to_conversation("test-session", "user", f"msg {i}")
        add_to_conversation("test-session", "assistant", f"reply {i}")
    history = get_conversation("test-session")
    # MAX_MEMORY_WINDOW = 5, so 5*2 = 10 messages
    assert len(history) == 10
    _conversations.clear()


def test_conversation_empty_session():
    """Should return empty list for unknown session."""
    _conversations.clear()
    assert get_conversation("nonexistent") == []


# --- Integration test for chat endpoint ---


@pytest.mark.asyncio
async def test_chat_endpoint_non_streaming():
    """Chat endpoint should return answer with sources (non-streaming)."""
    mock_chunks = [
        {"content": "Return within 30 days.", "source_file": "policy.pdf", "chunk_index": 0, "distance": 0.1},
    ]

    # Mock the vector store query
    with patch("app.rag_chain.query_store", return_value=mock_chunks):
        # Mock OpenAI response
        mock_message = MagicMock()
        mock_message.content = "You can return items within 30 days."
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.rag_chain.get_openai_client", return_value=mock_client):
            from app.main import app
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/chat",
                    json={"question": "How do I return?", "stream": False},
                )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert data["sources"][0]["source_file"] == "policy.pdf"
