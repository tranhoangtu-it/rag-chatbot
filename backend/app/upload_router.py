"""Upload endpoint for PDF documents."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Request

from app.config import MAX_UPLOAD_SIZE_MB
from app.document_processor import process_pdf
from app.vector_store import add_chunks_to_store
from app.rate_limiter import limiter

router = APIRouter(prefix="/api", tags=["upload"])

MAX_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/upload")
@limiter.limit("5/minute")
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    """Upload a PDF file, parse and chunk it for RAG ingestion.

    Returns document ID and chunk count.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_MB}MB.",
        )

    # Process PDF
    try:
        chunks = process_pdf(content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Store chunks in vector store
    stored_count = add_chunks_to_store(chunks)
    return {
        "filename": file.filename,
        "chunk_count": stored_count,
        "status": "processed",
    }
