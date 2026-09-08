"""
Pydantic models for the home dashboard overview.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class TopicOverview(BaseModel):
    """A topic with a summary of the material backing it."""
    id: UUID
    name: str
    course_id: UUID
    course_name: str
    created_at: datetime
    pdf_count: int = 0
    audio_count: int = 0
    image_count: int = 0

    # Spaced-repetition schedule, carried here so the home dashboard can order
    # its review queue without a second request. The full history and the
    # per-button interval preview live behind /reviews instead.
    last_reviewed_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None
    ease_factor: float = 2.5
    interval_days: int = 0
    repetitions: int = 0
    lapses: int = 0
    due: bool = True
    days_until_due: int = 0

    @property
    def material_count(self) -> int:
        return self.pdf_count + self.audio_count + self.image_count


class CourseOverview(BaseModel):
    """A course with its topic count."""
    id: UUID
    name: str
    created_at: datetime
    topic_count: int = 0


class OverviewResponse(BaseModel):
    """Everything the home dashboard needs, in one round trip."""
    courses: list[CourseOverview] = Field(default_factory=list)
    topics: list[TopicOverview] = Field(default_factory=list)
    total_courses: int = 0
    total_topics: int = 0
    total_materials: int = 0
    #: Topics with no material yet — surfaced as "materyal eklenmedi" rows.
    empty_topics: int = 0
    #: Topics whose next review date has passed — the size of today's queue.
    due_topics: int = 0
