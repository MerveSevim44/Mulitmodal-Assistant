"""
Materials API router.
Processes files already uploaded to Supabase Storage by the frontend.
"""
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.middleware.auth import get_current_user_id
from app.db.repository import get_repository, Repository
from app.models.material import (
    MaterialResponse,
    MaterialListResponse,
    MaterialUploadResponse,
    MaterialLibraryItem,
    MaterialLibraryResponse,
)
from app.config import get_settings
from app.db.supabase import get_supabase_admin

router = APIRouter(prefix="/materials", tags=["materials"])

class ProcessMaterialRequest(BaseModel):
    file_name: str
    storage_path: str
    type: str
    bucket: str


@router.get("", response_model=MaterialLibraryResponse)
def list_all_materials(
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """
    Every material the user has uploaded, across all courses and topics.

    Feeds the standalone "Materyaller" page, which is a flat view of the
    library rather than the per-topic sidebar.
    """
    rows = repo.list_all_materials(user_id)

    items: list[MaterialLibraryItem] = []
    counts = {"pdf": 0, "audio": 0, "image": 0}

    for row in rows:
        topic = row.get("topics") or {}
        course = topic.get("courses") or {}
        if row.get("type") in counts:
            counts[row["type"]] += 1
        items.append(
            MaterialLibraryItem(
                id=row["id"],
                type=row["type"],
                file_name=row["file_name"],
                storage_path=row["storage_path"],
                chunk_count=row.get("chunk_count") or 0,
                created_at=row["created_at"],
                topic_id=topic.get("id") or row["topic_id"],
                topic_name=topic.get("name") or "",
                course_id=course.get("id") or topic.get("course_id"),
                course_name=course.get("name") or "",
            )
        )

    return MaterialLibraryResponse(
        materials=items,
        total=len(items),
        pdf_count=counts["pdf"],
        audio_count=counts["audio"],
        image_count=counts["image"],
    )


@router.get("/topics/{topic_id}/materials", response_model=MaterialListResponse)
def list_materials(
    topic_id: str,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """List all materials for a topic."""
    topic = repo.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    if topic.get("courses", {}).get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    materials = repo.list_materials(topic_id)
    return MaterialListResponse(
        materials=[MaterialResponse(**m) for m in materials],
        total=len(materials),
    )


@router.post("/topics/{topic_id}/materials/process", response_model=MaterialUploadResponse, status_code=201)
def process_material(
    topic_id: str,
    body: ProcessMaterialRequest,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """
    Download a file from Supabase Storage (uploaded directly by frontend),
    process it (ingest), and store metadata in the database.
    """
    # Verify ownership
    topic = repo.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    if topic.get("courses", {}).get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    course_id = topic["course_id"]
    course = repo.get_course(course_id, user_id)
    course_name = course["name"] if course else ""
    topic_name = topic["name"]

    settings = get_settings()
    supabase = get_supabase_admin()
    
    # 1. Download file from Supabase Storage to Vercel /tmp directory
    os.makedirs(settings.TEMP_UPLOAD_DIR, exist_ok=True)
    local_path = os.path.join(settings.TEMP_UPLOAD_DIR, os.path.basename(body.storage_path))

    try:
        res = supabase.storage.from_(body.bucket).download(body.storage_path)
        with open(local_path, 'wb') as f:
            f.write(res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download from storage: {str(e)}")

    # 2. Process file based on type
    chunk_count = 0
    try:
        if body.type == "pdf":
            from ai_engine.ingest import ingest_pdf
            chunk_count = ingest_pdf(local_path, course_name, course_id, topic_name, topic_id)
        elif body.type == "audio":
            from ai_engine.ingest import ingest_audio
            chunk_count = ingest_audio(local_path, course_name, course_id, topic_name, topic_id)
        elif body.type == "image":
            from ai_engine.ingest import ingest_image
            chunk_count = ingest_image(local_path, course_name, course_id, topic_name, topic_id)
        else:
            raise ValueError(f"Invalid material type: {body.type}")
            
        # 3. Record in database
        material = repo.create_material(
            topic_id=topic_id,
            material_type=body.type,
            file_name=body.file_name,
            storage_path=body.storage_path,
            chunk_count=chunk_count,
        )

        return MaterialUploadResponse(
            id=material["id"],
            file_name=body.file_name,
            type=body.type,
            chunk_count=chunk_count,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        # Clean up /tmp file
        if os.path.exists(local_path):
            os.remove(local_path)


@router.delete("/{material_id}", status_code=204)
def delete_material(
    material_id: str,
    user_id: str = Depends(get_current_user_id),
    repo: Repository = Depends(get_repository),
):
    """Delete a material and its vector chunks."""
    from ai_engine.retriever import delete_by_file

    material = repo.delete_material(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    # Delete from Supabase Storage
    supabase = get_supabase_admin()
    bucket = "pdfs" if material["type"] == "pdf" else "audio" if material["type"] == "audio" else "images"
    supabase.storage.from_(bucket).remove([material["storage_path"]])

    # Delete associated vector chunks. Ingestion keys them on the basename of
    # the stored object (timestamp-prefixed), not on the original file name.
    delete_by_file(os.path.basename(material["storage_path"]), material["topic_id"])
