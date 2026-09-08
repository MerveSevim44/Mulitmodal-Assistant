"""
Pydantic models for Topic-related requests and responses.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class TopicCreate(BaseModel):
    """Request body for creating a new topic."""
    name: str = Field(..., min_length=1, max_length=200, description="Topic name")


class TopicUpdate(BaseModel):
    """Request body for updating a topic."""
    name: str = Field(..., min_length=1, max_length=200, description="New topic name")


class TopicResponse(BaseModel):
    """Response body for a topic."""
    id: UUID
    course_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    material_counts: Optional[dict] = Field(
        default_factory=lambda: {"pdf": 0, "audio": 0, "image": 0}
    )


class TopicListResponse(BaseModel):
    """Response body for listing topics."""
    topics: list[TopicResponse]
    total: int
