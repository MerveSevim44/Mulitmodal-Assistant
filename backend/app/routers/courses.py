"""
Courses API router.
CRUD operations for academic courses.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.middleware.auth import get_current_user_id
from app.db.repository import get_repository, Repository
from app.models.course import CourseCreate, CourseUpdate, CourseResponse, CourseListResponse

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=CourseListResponse)
async def list_courses(
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """List all courses for the authenticated user."""
    courses = repo.list_courses(user_id)
    course_responses = []
    for c in courses:
        # Extract topic count from nested aggregate
        topic_count = 0
        if isinstance(c.get("topics"), list) and c["topics"]:
            topic_count = c["topics"][0].get("count", 0)

        course_responses.append(
            CourseResponse(
                id=c["id"],
                user_id=c["user_id"],
                name=c["name"],
                created_at=c["created_at"],
                updated_at=c["updated_at"],
                topic_count=topic_count,
            )
        )

    return CourseListResponse(courses=course_responses, total=len(course_responses))

   

@router.post("", response_model=CourseResponse, status_code=201)
async def create_course(
    body: CourseCreate,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):

    """Create a new course."""
    from postgrest.exceptions import APIError
    
    try:
        course = repo.create_course(user_id, body.name)
    except APIError as e:
        if "courses_user_id_fkey" in str(e):
            raise HTTPException(
                status_code=401, 
                detail="User not found in database. Your session might be stale. Please log out and log in again."
            )
        raise e
        
    return CourseResponse(
        id=course["id"],
        user_id=course["user_id"],
        name=course["name"],
        created_at=course["created_at"],
        updated_at=course["updated_at"],
        topic_count=0,
    )


@router.patch("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    body: CourseUpdate,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """Update a course name."""
    course = repo.update_course(course_id, user_id, body.name)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseResponse(
        id=course["id"],
        user_id=course["user_id"],
        name=course["name"],
        created_at=course["created_at"],
        updated_at=course["updated_at"],
    )


@router.delete("/{course_id}", status_code=204)
async def delete_course(
    course_id: str,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """Delete a course and all associated data (topics, materials, messages, vectors)."""
    from ai_engine.retriever import delete_by_course

    # Delete vector chunks first
    delete_by_course(course_id)

    # Delete from database (cascades to topics, materials, messages)
    deleted = repo.delete_course(course_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Course not found")
