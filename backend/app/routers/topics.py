"""
Topics API router.
CRUD operations for course topics.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.middleware.auth import get_current_user_id
from app.db.repository import get_repository, Repository
from app.models.topic import TopicCreate, TopicUpdate, TopicResponse, TopicListResponse

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("/courses/{course_id}/topics", response_model=TopicListResponse)
async def list_topics(
    course_id: str,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """List all topics for a course."""
    # Verify course belongs to user
    course = repo.get_course(course_id, user_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    topics = repo.list_topics(course_id)

    topic_responses = []
    for t in topics:
        material_counts = repo.get_material_counts(t["id"])
        topic_responses.append(
            TopicResponse(
                id=t["id"],
                course_id=t["course_id"],
                name=t["name"],
                created_at=t["created_at"],
                updated_at=t["updated_at"],
                material_counts=material_counts,
            )
        )

    return TopicListResponse(topics=topic_responses, total=len(topic_responses))


@router.post("/courses/{course_id}/topics", response_model=TopicResponse, status_code=201)
async def create_topic(
    course_id: str,
    body: TopicCreate,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """Create a new topic under a course."""
    # Verify course belongs to user
    course = repo.get_course(course_id, user_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    topic = repo.create_topic(course_id, body.name)
    return TopicResponse(
        id=topic["id"],
        course_id=topic["course_id"],
        name=topic["name"],
        created_at=topic["created_at"],
        updated_at=topic["updated_at"],
        material_counts={"pdf": 0, "audio": 0, "image": 0},
    )


@router.patch("/{topic_id}", response_model=TopicResponse)
async def update_topic(
    topic_id: str,
    body: TopicUpdate,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """Update a topic name."""
    # Verify topic belongs to user's course
    topic_data = repo.get_topic(topic_id)
    if not topic_data:
        raise HTTPException(status_code=404, detail="Topic not found")
    if topic_data.get("courses", {}).get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    topic = repo.update_topic(topic_id, body.name)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    return TopicResponse(
        id=topic["id"],
        course_id=topic["course_id"],
        name=topic["name"],
        created_at=topic["created_at"],
        updated_at=topic["updated_at"],
    )


@router.delete("/{topic_id}", status_code=204)
async def delete_topic(
    topic_id: str,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """Delete a topic and all associated data."""
    from ai_engine.retriever import delete_by_topic

    # Verify ownership
    topic_data = repo.get_topic(topic_id)
    if not topic_data:
        raise HTTPException(status_code=404, detail="Topic not found")
    if topic_data.get("courses", {}).get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete vector chunks
    delete_by_topic(topic_id)

    # Delete from database (cascades to materials, messages)
    repo.delete_topic(topic_id)
