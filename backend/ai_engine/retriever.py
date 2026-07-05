"""
Vector database retriever.
Migrated to use Supabase pgvector (SupabaseVectorStore).
"""
import os
from langchain_community.vectorstores.supabase import SupabaseVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from app.db.supabase import get_supabase_admin


def create_embeddings(model_name: str = None) -> HuggingFaceEmbeddings:
    """Create the embedding model instance."""
    if model_name is None:
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    return HuggingFaceEmbeddings(model_name=model_name)


# Module-level instances (lazy initialization)
_embeddings = None
_vector_db = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Get the singleton embedding model."""
    global _embeddings
    if _embeddings is None:
        _embeddings = create_embeddings()
    return _embeddings


def get_vector_db() -> SupabaseVectorStore:
    """Get the singleton vector database."""
    global _vector_db
    if _vector_db is None:
        _vector_db = SupabaseVectorStore(
            client=get_supabase_admin(),
            embedding=get_embeddings(),
            table_name="documents",
            query_name="match_documents"
        )
    return _vector_db


def retrieve_documents(
    query: str,
    course_id: str = None,
    topic_id: str = None,
    source_type: str = None,
    k: int = 8,
    fetch_k: int = 25,
) -> list:
    """
    Retrieve relevant documents.

    Args:
        query: The search query
        course_id: Filter by course ID
        topic_id: Filter by topic ID
        source_type: Filter by source type ('pdf_dokuman', 'ses_kaydi', 'goruntu')
        k: Number of results to return
        fetch_k: Number of candidates to fetch
    """
    db = get_vector_db()

    # Build exact match filters for Supabase metadata JSONB column
    filter_conditions = {}
    if topic_id:
        filter_conditions["konu_id"] = topic_id
    elif course_id:
        filter_conditions["ders_id"] = course_id
    if source_type:
        filter_conditions["kaynak"] = source_type

    # Note: SupabaseVectorStore supports dict filters which are translated to @>
    docs = db.similarity_search(
        query, 
        k=k, 
        filter=filter_conditions if filter_conditions else None
    )

    return docs


def retrieve_text(
    query: str,
    course_id: str = None,
    topic_id: str = None,
    source_type: str = None,
    k: int = 3,
) -> str:
    """Retrieve documents and return concatenated text content."""
    docs = retrieve_documents(
        query,
        course_id=course_id,
        topic_id=topic_id,
        source_type=source_type,
        k=k,
    )
    if not docs:
        return ""
    return "\n\n".join(doc.page_content for doc in docs)


def delete_by_topic(topic_id: str) -> int:
    """Delete all vector chunks for a topic."""
    client = get_supabase_admin()
    response = client.table("documents").delete().eq("metadata->>konu_id", topic_id).execute()
    return len(response.data) if response.data else 0


def delete_by_course(course_id: str) -> int:
    """Delete all vector chunks for a course."""
    client = get_supabase_admin()
    response = client.table("documents").delete().eq("metadata->>ders_id", course_id).execute()
    return len(response.data) if response.data else 0


def delete_by_file(file_name: str, topic_id: str = None) -> int:
    """Delete vector chunks for a specific file."""
    client = get_supabase_admin()
    query = client.table("documents").delete().eq("metadata->>dosya", file_name)
    if topic_id:
        query = query.eq("metadata->>konu_id", topic_id)
    response = query.execute()
    return len(response.data) if response.data else 0
