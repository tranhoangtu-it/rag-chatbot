"""PDF parsing and text chunking pipeline."""

import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.config import CHUNK_SIZE, CHUNK_OVERLAP


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text content from PDF bytes. Supports text-based PDFs only."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def chunk_text(text: str) -> list[dict]:
    """Split text into overlapping chunks with metadata.

    Returns list of dicts with 'content' and 'chunk_index' keys.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [
        {"content": chunk, "chunk_index": i}
        for i, chunk in enumerate(chunks)
    ]


def process_pdf(pdf_bytes: bytes, filename: str) -> list[dict]:
    """Full pipeline: PDF bytes → extracted text → chunks with metadata.

    Each chunk dict contains: content, chunk_index, source_file.
    """
    text = extract_text_from_pdf(pdf_bytes)
    if not text.strip():
        raise ValueError(f"No text content found in '{filename}'. Only text-based PDFs are supported.")
    chunks = chunk_text(text)
    for chunk in chunks:
        chunk["source_file"] = filename
    return chunks
