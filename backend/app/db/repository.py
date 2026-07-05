"""
Data access layer for Supabase PostgreSQL.
All database operations go through this module.
"""
from typing import Optional
from uuid import UUID
from app.db.supabase import get_supabase_admin


class Repository:
    """Data access methods for all tables."""

    def __init__(self):
        self.client = get_supabase_admin()

    # ── COURSES ─────────────────────────────────────────────────

    def list_courses(self, user_id: str) -> list[dict]:
        """List all courses for a user."""
        response = (
            self.client.table("courses")
            .select("*, topics(count)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data

    def get_course(self, course_id: str, user_id: str) -> Optional[dict]:
        """Get a single course by ID."""
        response = (
            self.client.table("courses")
            .select("*")
            .eq("id", course_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return response.data

    def create_course(self, user_id: str, name: str) -> dict:
        """Create a new course."""
        response = (
            self.client.table("courses")
            .insert({"user_id": user_id, "name": name})
            .execute()
        )
        return response.data[0]

    def update_course(self, course_id: str, user_id: str, name: str) -> dict:
        """Update a course name."""
        response = (
            self.client.table("courses")
            .update({"name": name, "updated_at": "now()"})
            .eq("id", course_id)
            .eq("user_id", user_id)
            .execute()
        )
        return response.data[0] if response.data else None

    def delete_course(self, course_id: str, user_id: str) -> bool:
        """Delete a course and cascade to topics, materials, messages."""
        response = (
            self.client.table("courses")
            .delete()
            .eq("id", course_id)
            .eq("user_id", user_id)
            .execute()
        )
        return len(response.data) > 0

    # ── TOPICS ──────────────────────────────────────────────────

    def list_topics(self, course_id: str) -> list[dict]:
        """List all topics for a course."""
        response = (
            self.client.table("topics")
            .select("*, materials(count)")
            .eq("course_id", course_id)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data

    def get_topic(self, topic_id: str) -> Optional[dict]:
        """Get a single topic by ID."""
        response = (
            self.client.table("topics")
            .select("*, courses!inner(user_id)")
            .eq("id", topic_id)
            .single()
            .execute()
        )
        return response.data

    def create_topic(self, course_id: str, name: str) -> dict:
        """Create a new topic under a course."""
        response = (
            self.client.table("topics")
            .insert({"course_id": course_id, "name": name})
            .execute()
        )
        return response.data[0]

    def update_topic(self, topic_id: str, name: str) -> dict:
        """Update a topic name."""
        response = (
            self.client.table("topics")
            .update({"name": name, "updated_at": "now()"})
            .eq("id", topic_id)
            .execute()
        )
        return response.data[0] if response.data else None

    def delete_topic(self, topic_id: str) -> bool:
        """Delete a topic and cascade to materials and messages."""
        response = (
            self.client.table("topics")
            .delete()
            .eq("id", topic_id)
            .execute()
        )
        return len(response.data) > 0

    # ── MATERIALS ───────────────────────────────────────────────

    def list_materials(self, topic_id: str) -> list[dict]:
        """List all materials for a topic."""
        response = (
            self.client.table("materials")
            .select("*")
            .eq("topic_id", topic_id)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data

    def create_material(
        self,
        topic_id: str,
        material_type: str,
        file_name: str,
        storage_path: str,
        chunk_count: int = 0,
    ) -> dict:
        """Record a new material entry."""
        response = (
            self.client.table("materials")
            .insert({
                "topic_id": topic_id,
                "type": material_type,
                "file_name": file_name,
                "storage_path": storage_path,
                "chunk_count": chunk_count,
            })
            .execute()
        )
        return response.data[0]

    def delete_material(self, material_id: str) -> Optional[dict]:
        """Delete a material. Returns the deleted record for cleanup."""
        # First fetch to get storage_path before deleting
        fetch = (
            self.client.table("materials")
            .select("*")
            .eq("id", material_id)
            .single()
            .execute()
        )
        if not fetch.data:
            return None

        self.client.table("materials").delete().eq("id", material_id).execute()
        return fetch.data

    def get_material_counts(self, topic_id: str) -> dict:
        """Get material counts by type for a topic."""
        response = (
            self.client.table("materials")
            .select("type")
            .eq("topic_id", topic_id)
            .execute()
        )
        counts = {"pdf": 0, "audio": 0, "image": 0}
        for row in response.data:
            t = row.get("type")
            if t in counts:
                counts[t] += 1
        return counts

    # ── CHAT MESSAGES ───────────────────────────────────────────

    def list_messages(self, topic_id: str) -> list[dict]:
        """List all chat messages for a topic, ordered chronologically."""
        response = (
            self.client.table("chat_messages")
            .select("*")
            .eq("topic_id", topic_id)
            .order("created_at", desc=False)
            .execute()
        )
        return response.data

    def create_message(
        self,
        topic_id: str,
        role: str,
        content: str,
        metadata: dict = None,
    ) -> dict:
        """Save a chat message."""
        response = (
            self.client.table("chat_messages")
            .insert({
                "topic_id": topic_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
            })
            .execute()
        )
        return response.data[0]

    def delete_messages(self, topic_id: str) -> int:
        """Delete all chat messages for a topic."""
        response = (
            self.client.table("chat_messages")
            .delete()
            .eq("topic_id", topic_id)
            .execute()
        )
        return len(response.data)


def get_repository() -> Repository:
    """Factory for the repository — can be swapped for testing."""
    return Repository()
