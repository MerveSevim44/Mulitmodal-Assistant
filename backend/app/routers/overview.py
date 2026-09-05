"""
Overview API router.
Feeds the home dashboard with the whole course/topic/material tree in one call.
"""
from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user_id
from app.db.repository import get_repository, Repository
from app.models.overview import OverviewResponse, CourseOverview, TopicOverview

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("", response_model=OverviewResponse)
async def get_overview(
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """
    Summarise the user's library for the home dashboard.

    Fetched as one nested query rather than a courses call followed by a topics
    call per course, which is what the home page would otherwise need.
    """
    tree = repo.get_overview_tree(user_id)

    courses: list[CourseOverview] = []
    topics: list[TopicOverview] = []
    total_materials = 0
    empty_topics = 0

    for course in tree:
        course_topics = course.get("topics") or []
        courses.append(
            CourseOverview(
                id=course["id"],
                name=course["name"],
                created_at=course["created_at"],
                topic_count=len(course_topics),
            )
        )

        for topic in course_topics:
            materials = topic.get("materials") or []
            counts = {"pdf": 0, "audio": 0, "image": 0}
            for material in materials:
                if material.get("type") in counts:
                    counts[material["type"]] += 1

            total_materials += len(materials)
            if not materials:
                empty_topics += 1

            topics.append(
                TopicOverview(
                    id=topic["id"],
                    name=topic["name"],
                    course_id=course["id"],
                    course_name=course["name"],
                    created_at=topic["created_at"],
                    pdf_count=counts["pdf"],
                    audio_count=counts["audio"],
                    image_count=counts["image"],
                )
            )

    # Newest topics first — the home page shows the most recent work at the top.
    topics.sort(key=lambda t: t.created_at, reverse=True)

    return OverviewResponse(
        courses=courses,
        topics=topics,
        total_courses=len(courses),
        total_topics=len(topics),
        total_materials=total_materials,
        empty_topics=empty_topics,
    )
