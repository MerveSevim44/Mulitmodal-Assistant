"""
Pydantic models for Material-related requests and responses.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID


class MaterialResponse(BaseModel):
    """Response body for a material."""
    id: UUID
    topic_id: UUID
    type: Literal["pdf", "audio", "image"]
    file_name: str
    storage_path: str
    chunk_count: int = 0
    created_at: datetime


class MaterialListResponse(BaseModel):
    """Response body for listing materials."""
    materials: list[MaterialResponse]
    total: int


class MaterialUploadResponse(BaseModel):
    """Response after successfully uploading and ingesting a material."""
    id: UUID
    file_name: str
    type: str
    chunk_count: int
    message: str = "Material uploaded and indexed successfully"


class MaterialLibraryItem(BaseModel):
    """A material shown on the library page, with where it lives."""
    id: UUID
    type: Literal["pdf", "audio", "image"]
    file_name: str
    storage_path: str
    chunk_count: int = 0
    created_at: datetime
    topic_id: UUID
    topic_name: str
    course_id: UUID
    course_name: str


class MaterialLibraryResponse(BaseModel):
    """Every material the user owns, plus the per-type totals."""
    materials: list[MaterialLibraryItem]
    total: int
    pdf_count: int = 0
    audio_count: int = 0
    image_count: int = 0
