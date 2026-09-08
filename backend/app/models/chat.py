"""
Pydantic models for Chat-related requests and responses.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class ChatRequest(BaseModel):
    """Request body for sending a chat message."""
    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    include_image: bool = Field(False, description="Include active image in context")
    include_audio: bool = Field(False, description="Include active audio in context")
    image_path: Optional[str] = Field(None, description="Path to active image file")
    audio_path: Optional[str] = Field(None, description="Path to active audio file")


class ChatMessageResponse(BaseModel):
    """Response body for a single chat message."""
    id: UUID
    topic_id: UUID
    role: str
    content: str
    metadata: Optional[dict] = Field(default_factory=dict)
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    """Response body for chat history."""
    messages: list[ChatMessageResponse]
    total: int


class StreamToken(BaseModel):
    """A single token in a streaming response."""
    token: Optional[str] = None
    done: bool = False
    sources: Optional[dict] = None
    error: Optional[str] = None
