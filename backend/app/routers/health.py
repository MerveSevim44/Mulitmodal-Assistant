"""
Health check router.
"""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "akademik-bellek-api",
        "version": "1.0.0",
    }
