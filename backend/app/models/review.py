"""
Pydantic models for spaced-repetition review scheduling.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewGrade(str, Enum):
    """The four buttons on the review screen.

    Wire values are English so the API stays language-neutral; the Turkish
    labels (Zor / Orta / Kolay / Cok Kolay) live in the frontend.
    """

    HARD = "hard"
    MEDIUM = "medium"
    EASY = "easy"
    VERY_EASY = "very_easy"


class ReviewSubmit(BaseModel):
    """Request body for grading a topic."""

    grade: ReviewGrade = Field(..., description="How hard the recall was")


class ReviewSchedule(BaseModel):
    """A topic's current SM-2 scheduling state."""

    topic_id: UUID
    last_reviewed_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None
    ease_factor: float
    interval_days: int
    repetitions: int
    lapses: int
    #: True when `next_review_at` has passed - what the queue filters on.
    due: bool
    #: Whole days until the next review; negative when overdue.
    days_until_due: int


class ReviewTopic(BaseModel):
    """A queue entry: the topic, its course, and its schedule."""

    id: UUID
    name: str
    course_id: UUID
    course_name: str
    created_at: datetime
    pdf_count: int = 0
    audio_count: int = 0
    image_count: int = 0

    last_reviewed_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None
    ease_factor: float
    interval_days: int
    repetitions: int
    lapses: int
    due: bool
    days_until_due: int


class ReviewQueueResponse(BaseModel):
    """The review queue, already ordered by `next_review_at`."""

    topics: list[ReviewTopic] = Field(default_factory=list)
    #: How many of `topics` are due right now.
    due_count: int = 0
    total: int = 0


class ReviewResult(BaseModel):
    """What a submitted review produced."""

    schedule: ReviewSchedule
    #: What each button would schedule next time, in days - the review screen
    #: labels its buttons from this.
    preview_days: dict[str, int] = Field(default_factory=dict)


class ReviewLogEntry(BaseModel):
    """One past review."""

    id: UUID
    grade: ReviewGrade
    quality: int
    ease_factor: float
    interval_days: int
    repetitions: int
    next_review_at: datetime
    reviewed_at: datetime


class ReviewHistoryResponse(BaseModel):
    """A topic's schedule plus its recent reviews."""

    schedule: ReviewSchedule
    preview_days: dict[str, int] = Field(default_factory=dict)
    history: list[ReviewLogEntry] = Field(default_factory=list)
