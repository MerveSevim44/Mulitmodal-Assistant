"""
Reviews API router.

The spaced-repetition queue and the endpoint that grades a topic. The
scheduling maths itself lives in app/services/spaced_repetition.py; this module
only reads state from the database, hands it to the scheduler, and writes the
result back.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.repository import Repository, get_repository
from app.middleware.auth import get_current_user_id
from app.models.review import (
    ReviewHistoryResponse,
    ReviewLogEntry,
    ReviewQueueResponse,
    ReviewResult,
    ReviewSchedule,
    ReviewSubmit,
    ReviewTopic,
)
from app.services import spaced_repetition as sr

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _schedule(topic_id: str, state: sr.ReviewState, now: datetime) -> ReviewSchedule:
    return ReviewSchedule(
        topic_id=topic_id,
        last_reviewed_at=state.last_reviewed_at,
        next_review_at=state.next_review_at,
        ease_factor=round(state.ease_factor, 4),
        interval_days=state.interval_days,
        repetitions=state.repetitions,
        lapses=state.lapses,
        due=sr.is_due(state, now=now),
        days_until_due=sr.days_until_due(state, now=now),
    )


def _owned_topic(repo: Repository, topic_id: str, user_id: str) -> dict:
    """Fetch a topic, or fail with the same 404/403 pair the topics router
    uses."""
    topic = repo.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    if (topic.get("courses") or {}).get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return topic


@router.get("/queue", response_model=ReviewQueueResponse)
def get_review_queue(
    due_only: bool = Query(
        False,
        description="Return only topics whose next review date has passed",
    ),
    limit: int = Query(100, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """
    The review queue, soonest-due first.

    Ordering is done by Postgres on `next_review_at`, so the home dashboard's
    "Tekrar Listesi" is just the head of this list rather than something the
    client re-sorts.
    """
    now = datetime.now(timezone.utc)
    rows = repo.list_review_queue(user_id)

    topics: list[ReviewTopic] = []
    due_count = 0

    for row in rows:
        state = sr.ReviewState.from_row(row)
        due = sr.is_due(state, now=now)
        if due:
            due_count += 1
        if due_only and not due:
            continue

        counts = {"pdf": 0, "audio": 0, "image": 0}
        for material in row.get("materials") or []:
            if material.get("type") in counts:
                counts[material["type"]] += 1

        course = row.get("courses") or {}
        topics.append(
            ReviewTopic(
                id=row["id"],
                name=row["name"],
                course_id=row["course_id"],
                course_name=course.get("name", ""),
                created_at=row["created_at"],
                pdf_count=counts["pdf"],
                audio_count=counts["audio"],
                image_count=counts["image"],
                last_reviewed_at=state.last_reviewed_at,
                next_review_at=state.next_review_at,
                ease_factor=round(state.ease_factor, 4),
                interval_days=state.interval_days,
                repetitions=state.repetitions,
                lapses=state.lapses,
                due=due,
                days_until_due=sr.days_until_due(state, now=now),
            )
        )

    return ReviewQueueResponse(
        topics=topics[:limit],
        due_count=due_count,
        total=len(rows),
    )


@router.get("/topics/{topic_id}", response_model=ReviewHistoryResponse)
def get_topic_review(
    topic_id: str,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """A topic's schedule, the intervals each button would set, and its recent
    reviews."""
    topic = _owned_topic(repo, topic_id, user_id)
    now = datetime.now(timezone.utc)
    state = sr.ReviewState.from_row(topic)

    history = [
        ReviewLogEntry(
            id=entry["id"],
            grade=entry["grade"],
            quality=entry["quality"],
            ease_factor=entry["ease_factor"],
            interval_days=entry["interval_days"],
            repetitions=entry["repetitions"],
            next_review_at=entry["next_review_at"],
            reviewed_at=entry["reviewed_at"],
        )
        for entry in repo.list_reviews(topic_id)
    ]

    return ReviewHistoryResponse(
        schedule=_schedule(topic_id, state, now),
        preview_days=sr.preview_intervals(state, now=now),
        history=history,
    )


@router.post("/topics/{topic_id}", response_model=ReviewResult)
def submit_review(
    topic_id: str,
    body: ReviewSubmit,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """
    Grade a topic and reschedule it.

    The topic row is written first and the history row second: a failure
    between the two costs an audit entry, whereas the reverse order would
    leave a logged review the schedule never applied.
    """
    topic = _owned_topic(repo, topic_id, user_id)
    now = datetime.now(timezone.utc)

    grade = body.grade.value
    new_state = sr.review(sr.ReviewState.from_row(topic), grade, now=now)
    payload = new_state.to_update()

    if not repo.update_review_state(topic_id, payload):
        raise HTTPException(status_code=500, detail="Failed to save review schedule")

    repo.log_review(
        topic_id=topic_id,
        grade=grade,
        quality=sr.quality_for_grade(grade),
        state=payload,
        reviewed_at=now.isoformat(),
    )

    return ReviewResult(
        schedule=_schedule(topic_id, new_state, now),
        preview_days=sr.preview_intervals(new_state, now=new_state.next_review_at),
    )
