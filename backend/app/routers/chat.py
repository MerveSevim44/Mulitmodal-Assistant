"""
Chat API router.
Streaming chat with Server-Sent Events (SSE) and chat history management.
"""
import json
import time
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.middleware.auth import get_current_user_id
from app.db.repository import get_repository, Repository
from app.db.supabase import get_supabase_admin
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
        image_files: list[str] = []
        try:
            async for token in stream_pipeline(
                question=body.message,
                course_id=course_id,
                topic_id=topic_id,
                image_path=body.image_path if body.include_image else None,
                audio_path=body.audio_path if body.include_audio else None,
                history=history,
                image_files_out=image_files,
            ):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"

            sources = _detect_sources(full_response)

            # Attach the images the answer actually drew on, so the reader can
            # see what is being described. Only when the answer cites them —
            # retrieval always returns its nearest neighbours, relevant or not.
            images = (
                _resolve_images(repo, topic_id, image_files)
                if sources["image"]
                else []
            )

            # Send completion signal
            yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

            # Save assistant response to database. Storage paths are persisted
            # rather than signed URLs, which expire; they are signed on read.
            repo.create_message(
                topic_id=topic_id,
                role="assistant",
                content=full_response,
                metadata={"sources": sources, "images": images},
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
    _sign_image_urls(messages)
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


IMAGE_BUCKET = "images"
SIGNED_URL_TTL = 3600  # 1 hour
SIGNED_URL_MIN_LIFE = 600  # re-sign once less than 10 minutes remain

# Signing mints a fresh token every call, which changes the URL and therefore
# misses the browser cache — the image is downloaded again on every history
# read. Reusing a still-valid URL keeps it cacheable. Process-local and
# self-limiting: one entry per image material.
_signed_url_cache: dict[str, tuple[str, float]] = {}


def _resolve_images(repo: Repository, topic_id: str, image_files: list) -> list:
    """
    Map the file names stored in vector metadata back to material records.

    Ingestion stores the basename of the uploaded object as `dosya`, while the
    materials table keeps the full storage path and the original file name, so
    the two are joined on that basename.
    """
    if not image_files:
        return []

    by_stored_name = {
        os.path.basename(m["storage_path"]): m
        for m in repo.list_materials(topic_id)
        if m.get("type") == "image" and m.get("storage_path")
    }

    images = []
    for file_name in image_files:
        material = by_stored_name.get(file_name)
        if material:
            images.append({
                "file_name": material["file_name"],
                "storage_path": material["storage_path"],
            })
    return images


def _sign_image_urls(messages: list) -> None:
    """
    Add a short-lived `url` to every image attached to a message, in place.

    The `images` bucket is private, and its read policy expects a per-user
    folder prefix that these topic-scoped paths do not have, so the URLs are
    signed here with the service role rather than fetched by the browser.
    """
    paths = list(dict.fromkeys(
        img["storage_path"]
        for msg in messages
        for img in (msg.get("metadata") or {}).get("images") or []
        if img.get("storage_path")
    ))
    if not paths:
        return

    now = time.time()
    url_by_path = {}
    stale = []
    for path in paths:
        cached = _signed_url_cache.get(path)
        if cached and cached[1] - now > SIGNED_URL_MIN_LIFE:
            url_by_path[path] = cached[0]
        else:
            stale.append(path)

    if stale:
        try:
            signed = get_supabase_admin().storage.from_(IMAGE_BUCKET).create_signed_urls(
                stale, SIGNED_URL_TTL
            )
        except Exception as e:
            print(f"⚠️ Could not sign image URLs: {e}")
            signed = []

        expires_at = now + SIGNED_URL_TTL
        for r in signed:
            path = r.get("path")
            url = r.get("signedURL") or r.get("signedUrl")
            if r.get("error") or not path or not url:
                continue
            _signed_url_cache[path] = (url, expires_at)
            url_by_path[path] = url

    for msg in messages:
        for img in (msg.get("metadata") or {}).get("images") or []:
            img["url"] = url_by_path.get(img.get("storage_path"))


def _detect_sources(response_text: str) -> dict:
    """Detect which sources were used in the response based on content markers."""
    return {
        "pdf": "📄" in response_text or "PDF: ✓" in response_text,
        "audio": "🎤" in response_text or "Ses: ✓" in response_text,
        "image": "🖼️" in response_text or "Görüntü: ✓" in response_text,
    }
