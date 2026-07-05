"""
Document ingestion module.
Migrated from week1_rag/ingest_rag.py — removed top-level side effects.
"""
import os
from datetime import datetime
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from pypdf import PdfReader

from ai_engine.retriever import get_vector_db, delete_by_file
from ai_engine.stt import transcribe_audio
from ai_engine.vision import analyze_image


def _remove_existing_file(file_path: str, topic_id: str = None) -> None:
    """Remove existing chunks for a file to prevent duplicates."""
    file_name = os.path.basename(file_path)
    deleted = delete_by_file(file_name, topic_id)
    if deleted > 0:
        print(f"⚠️ Removed {deleted} existing chunks for {file_name}")


def ingest_pdf(
    file_path: str,
    course_name: str,
    course_id: str,
    topic_name: str = None,
    topic_id: str = None,
) -> int:
    """
    Ingest a PDF file: extract text page by page, split into chunks,
    and store in ChromaDB with metadata.

    Returns:
        Number of chunks created
    """
    _remove_existing_file(file_path, topic_id)

    reader = PdfReader(file_path)
    print(f"PDF pages: {len(reader.pages)}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text or len(text) < 100:
            continue

        chunks = splitter.create_documents(
            texts=[text],
            metadatas=[
                {
                    "kaynak": "pdf_dokuman",
                    "ders_id": course_id,
                    "ders_adi": course_name,
                    "konu_id": topic_id or "",
                    "konu_adi": topic_name or "",
                    "tarih": datetime.now().strftime("%Y-%m-%d"),
                    "sayfa_numarasi": i + 1,
                    "dosya": os.path.basename(file_path),
                }
            ],
        )
        docs.extend(chunks)

    if docs:
        db = get_vector_db()
        db.add_documents(docs)
        print(f"PDF ingested: {len(docs)} chunks")

    return len(docs)


def ingest_audio(
    file_path: str,
    course_name: str,
    course_id: str,
    topic_name: str = None,
    topic_id: str = None,
) -> int:
    """
    Ingest an audio file: transcribe with Whisper, split into chunks,
    and store in ChromaDB with metadata.

    Returns:
        Number of chunks created
    """
    _remove_existing_file(file_path, topic_id)

    result = transcribe_audio(file_path)
    full_text = result["full_text"]

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.create_documents(
        texts=[full_text],
        metadatas=[
            {
                "kaynak": "ses_kaydi",
                "ders_id": course_id,
                "ders_adi": course_name,
                "konu_id": topic_id or "",
                "konu_adi": topic_name or "",
                "tarih": datetime.now().strftime("%Y-%m-%d"),
                "dosya": os.path.basename(file_path),
            }
        ],
    )

    if chunks:
        db = get_vector_db()
        db.add_documents(chunks)
        print(f"Audio ingested: {len(chunks)} chunks")

    return len(chunks)


def ingest_image(
    file_path: str,
    course_name: str,
    course_id: str,
    topic_name: str = None,
    topic_id: str = None,
) -> int:
    """
    Ingest an image: analyze with vision model and store the analysis
    as a single document in ChromaDB.

    Returns:
        Number of chunks created (always 1 for images)
    """
    _remove_existing_file(file_path, topic_id)

    print(f"Analyzing image: {os.path.basename(file_path)}")
    analysis_text = analyze_image(file_path)

    doc = Document(
        page_content=analysis_text,
        metadata={
            "kaynak": "goruntu",
            "ders_id": course_id,
            "ders_adi": course_name,
            "konu_id": topic_id or "",
            "konu_adi": topic_name or "",
            "tarih": datetime.now().strftime("%Y-%m-%d"),
            "dosya": os.path.basename(file_path),
        },
    )

    db = get_vector_db()
    db.add_documents([doc])
    print("Image ingested: 1 chunk")

    return 1
