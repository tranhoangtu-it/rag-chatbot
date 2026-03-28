"""FastAPI application entry point with CORS and rate limiting."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import ALLOWED_ORIGINS
from app.rate_limiter import limiter
from app.upload_router import router as upload_router
from app.chat_router import router as chat_router
from app.demo_loader import load_demo_data

app = FastAPI(
    title="RAG Customer Support Bot",
    description="AI-powered Q&A chatbot with document retrieval and source citations",
    version="1.0.0",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(upload_router)
app.include_router(chat_router)


@app.on_event("startup")
async def startup_load_demo():
    """Load demo dataset on first startup if vector store is empty."""
    try:
        count = load_demo_data()
        if count > 0:
            print(f"Loaded {count} demo chunks into vector store.")
    except Exception as e:
        print(f"Warning: Could not load demo data: {e}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "rag-chatbot-api"}
