"""
Pydantic models for Course-related requests and responses.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class CourseCreate(BaseModel):
    """Request body for creating a new course."""
    name: str = Field(..., min_length=1, max_length=200, description="Course name")


class CourseUpdate(BaseModel):
    """Request body for updating a course."""
    name: str = Field(..., min_length=1, max_length=200, description="New course name")


class CourseResponse(BaseModel):
    """Response body for a course."""
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    topic_count: Optional[int] = 0


class CourseListResponse(BaseModel):
    """Response body for listing courses."""
    courses: list[CourseResponse]
    total: int
