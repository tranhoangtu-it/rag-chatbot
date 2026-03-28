"""Tests for PDF upload and chunking pipeline."""

import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.document_processor import extract_text_from_pdf, chunk_text, process_pdf

# --- Unit tests for document_processor ---


def test_chunk_text_produces_chunks():
    """Chunking should split long text into multiple pieces."""
    text = "Hello world. " * 200  # ~2600 chars, should produce multiple chunks
    chunks = chunk_text(text)
    assert len(chunks) > 1
    assert all("content" in c and "chunk_index" in c for c in chunks)
    assert chunks[0]["chunk_index"] == 0


def test_chunk_text_short_text_single_chunk():
    """Short text should produce exactly one chunk."""
    chunks = chunk_text("Short text.")
    assert len(chunks) == 1
    assert chunks[0]["content"] == "Short text."


def test_process_pdf_empty_raises():
    """Processing a PDF with no text should raise ValueError."""
    # Create a minimal valid PDF with no text content
    import fitz
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()
    with pytest.raises(ValueError, match="No text content"):
        process_pdf(pdf_bytes, "empty.pdf")


def test_process_pdf_with_text():
    """Processing a PDF with text should return chunks with source metadata."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "This is a test document with enough content. " * 30)
    pdf_bytes = doc.tobytes()
    doc.close()
    chunks = process_pdf(pdf_bytes, "test.pdf")
    assert len(chunks) >= 1
    assert all(c["source_file"] == "test.pdf" for c in chunks)


# --- Integration tests for upload endpoint ---


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf():
    """Upload should reject non-PDF files."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/upload",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_rejects_oversized():
    """Upload should reject files larger than MAX_UPLOAD_SIZE_MB."""
    # Create content larger than 5MB
    big_content = b"x" * (6 * 1024 * 1024)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/upload",
            files={"file": ("big.pdf", big_content, "application/pdf")},
        )
    assert response.status_code == 400
    assert "large" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_valid_pdf():
    """Upload a valid PDF should return chunk count."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Sample support document content. " * 50)
    pdf_bytes = doc.tobytes()
    doc.close()

    # Mock vector store to avoid OpenAI API calls
    with patch("app.upload_router.add_chunks_to_store", return_value=3):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/upload",
                files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
            )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "sample.pdf"
    assert data["chunk_count"] >= 1
    assert data["status"] == "processed"
