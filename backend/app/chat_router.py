"""Chat endpoint for RAG Q&A with streaming support."""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.rag_chain import query_rag, query_rag_stream
from app.rate_limiter import limiter

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    question: str = Field(..., max_length=2000)
    session_id: str = "default"
    stream: bool = True


@router.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, body: ChatRequest):
    """Ask a question against uploaded documents.

    Supports streaming (default) and non-streaming responses.
    """
    if body.stream:
        return StreamingResponse(
            query_rag_stream(body.question, body.session_id),
            media_type="text/plain",
        )
    result = await query_rag(body.question, body.session_id)
    return result
