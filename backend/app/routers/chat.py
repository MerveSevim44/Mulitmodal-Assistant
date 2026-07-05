"""
Chat API router.
Streaming chat with Server-Sent Events (SSE) and chat history management.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.middleware.auth import get_current_user_id
from app.db.repository import get_repository, Repository
from app.models.chat import (
    ChatRequest,
    ChatMessageResponse,
    ChatHistoryResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/topics/{topic_id}/chat")
async def chat_stream(
    topic_id: str,
    body: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """
    Send a message and receive a streaming response via Server-Sent Events.

    The response is a text/event-stream with the following format:
    - data: {"token": "..."}\n\n — individual tokens
    - data: {"done": true, "sources": {...}}\n\n — completion signal

    The user message and full assistant response are saved to chat_messages
    after streaming completes.
    """
    # Verify ownership
    topic = repo.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    if topic.get("courses", {}).get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    course_id = topic["course_id"]

    # Load conversation history for context
    existing_messages = repo.list_messages(topic_id)
    history = []
    for msg in existing_messages[-10:]:  # Last 5 turns (10 messages)
        if msg["role"] == "user":
            history.append(f"Öğrenci: {msg['content']}")
        else:
            history.append(f"Asistan: {msg['content']}")

    # Save user message immediately
    metadata = {}
    if body.include_image and body.image_path:
        metadata["image"] = body.image_path
    if body.include_audio and body.audio_path:
        metadata["audio"] = body.audio_path

    repo.create_message(
        topic_id=topic_id,
        role="user",
        content=body.message,
        metadata=metadata,
    )

    async def event_generator():
        """Generate SSE events with streaming tokens."""
        from ai_engine.pipeline import stream_pipeline

        full_response = ""
        try:
            async for token in stream_pipeline(
                question=body.message,
                course_id=course_id,
                topic_id=topic_id,
                image_path=body.image_path if body.include_image else None,
                audio_path=body.audio_path if body.include_audio else None,
                history=history,
            ):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"

            # Send completion signal
            yield f"data: {json.dumps({'done': True})}\n\n"

            # Save assistant response to database
            repo.create_message(
                topic_id=topic_id,
                role="assistant",
                content=full_response,
                metadata={"sources": _detect_sources(full_response)},
            )

        except Exception as e:
            error_msg = f"Yanıt oluşturulurken hata oluştu: {str(e)}"
            yield f"data: {json.dumps({'error': error_msg, 'done': True})}\n\n"

            # Save error as assistant message
            repo.create_message(
                topic_id=topic_id,
                role="assistant",
                content=f"❌ {error_msg}",
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/topics/{topic_id}/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    topic_id: str,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """Get all chat messages for a topic."""
    # Verify ownership
    topic = repo.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    if topic.get("courses", {}).get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    messages = repo.list_messages(topic_id)
    return ChatHistoryResponse(
        messages=[ChatMessageResponse(**m) for m in messages],
        total=len(messages),
    )


@router.delete("/topics/{topic_id}/chat/history", status_code=204)
async def clear_chat_history(
    topic_id: str,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """Clear all chat messages for a topic."""
    # Verify ownership
    topic = repo.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    if topic.get("courses", {}).get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    repo.delete_messages(topic_id)


def _detect_sources(response_text: str) -> dict:
    """Detect which sources were used in the response based on content markers."""
    return {
        "pdf": "📄" in response_text or "PDF: ✓" in response_text,
        "audio": "🎤" in response_text or "Ses: ✓" in response_text,
        "image": "🖼️" in response_text or "Görüntü: ✓" in response_text,
    }
