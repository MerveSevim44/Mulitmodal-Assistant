"""
FastAPI Application — Akademik Bellek Asistanı Backend

This is the main entry point for the backend server.
It wraps the existing Multimodal RAG AI engine and exposes
all features via RESTful API endpoints with SSE streaming.
"""
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the backend directory is in the Python path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.config import get_settings
from app.routers import health, courses, topics, materials, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Startup: initialize AI engine components.
    Shutdown: cleanup resources.
    """
    settings = get_settings()

    # Ensure temp upload directory exists
    os.makedirs(settings.TEMP_UPLOAD_DIR, exist_ok=True)

    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    print(f"   ChromaDB: {settings.CHROMA_DB_PATH}")
    print(f"   LLM: {settings.LLM_MODEL}")
    print(f"   Embedding: {settings.EMBEDDING_MODEL}")

    yield  # Application runs here

    print("👋 Shutting down...")


# ── Create FastAPI application ──────────────────────────────────

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multimodal RAG Academic Assistant — Backend API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS Middleware ─────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Register Routers ───────────────────────────────────────────

API_PREFIX = "/api/v1"

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(courses.router, prefix=API_PREFIX)
app.include_router(topics.router, prefix=API_PREFIX)
app.include_router(materials.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)


# ── Root Redirect ──────────────────────────────────────────────

@app.get("/")
async def root():
    """Root endpoint — redirects to API documentation."""
    return {
        "message": "Akademik Bellek Asistanı API",
        "docs": "/docs",
        "health": f"{API_PREFIX}/health",
    }
