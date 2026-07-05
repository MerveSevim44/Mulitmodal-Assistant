# Phase 2 — FastAPI Backend & AI Engine Migration

## Objective
Build a FastAPI backend that wraps the existing Multimodal RAG AI engine, exposing all features via RESTful API endpoints with Server-Sent Events (SSE) streaming for the chat functionality.

---

## Tasks

### 2.1 AI Engine Migration
Migrate and clean the existing AI modules from `multimodal-rag/` to `backend/ai_engine/`:

| Source File | Target File | Changes |
|-------------|-------------|---------|
| `week2_multimodal/pipeline.py` | `ai_engine/pipeline.py` | Remove Streamlit deps, add async/streaming, env-based config |
| `week2_multimodal/stt.py` | `ai_engine/stt.py` | Remove hardcoded ffmpeg paths, use PATH-based detection |
| `week2_multimodal/vision.py` | `ai_engine/vision.py` | Clean imports, add error handling |
| `week1_rag/retriever.py` | `ai_engine/retriever.py` | Parameterize DB path, add async wrappers |
| `week1_rag/ingest_rag.py` | `ai_engine/ingest.py` | Remove top-level side effects, add user_id scoping |
| `prompts/diyagram_turleri.yaml` | `ai_engine/prompts/diyagram_turleri.yaml` | No changes |

### 2.2 FastAPI Application Setup
- Entry point with lifespan events (startup/shutdown)
- CORS middleware configured for frontend origin
- Global exception handlers
- Request/response logging

### 2.3 API Endpoints Implementation

#### Courses Router (`/api/v1/courses`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List all courses for authenticated user |
| POST | `/` | Create new course |
| PATCH | `/{course_id}` | Update course name |
| DELETE | `/{course_id}` | Delete course + cascade all data |

#### Topics Router (`/api/v1/topics`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/courses/{course_id}/topics` | List topics for a course |
| POST | `/courses/{course_id}/topics` | Create new topic |
| PATCH | `/{topic_id}` | Update topic name |
| DELETE | `/{topic_id}` | Delete topic + cascade all data |

#### Materials Router (`/api/v1/materials`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/topics/{topic_id}/materials` | List materials for a topic |
| POST | `/topics/{topic_id}/materials/pdf` | Upload & ingest PDF |
| POST | `/topics/{topic_id}/materials/audio` | Upload & ingest audio |
| POST | `/topics/{topic_id}/materials/image` | Upload & ingest image |
| DELETE | `/{material_id}` | Delete material + vector chunks |

#### Chat Router (`/api/v1/chat`)
| Method | Path | Description | Response |
|--------|------|-------------|----------|
| POST | `/topics/{topic_id}/chat` | Send message | SSE `text/event-stream` |
| GET | `/topics/{topic_id}/chat/history` | Get chat history | JSON array |
| DELETE | `/topics/{topic_id}/chat/history` | Clear chat history | 204 No Content |

### 2.4 Streaming Implementation
The chat endpoint uses FastAPI's `StreamingResponse` with SSE format:

```
Event format:
data: {"token": "Bu"}\n\n
data: {"token": " konuda"}\n\n
data: {"token": " PDF"}\n\n
data: {"done": true, "sources": {"pdf": true, "audio": false, "image": false}}\n\n
```

LangChain's `.astream()` method on the LLM chain generates tokens incrementally.

### 2.5 Pydantic Models
Request/response schemas for all endpoints with validation.

---

## Technical Requirements
- FastAPI 0.115+ with async support
- LangChain 0.3+ with streaming callbacks
- python-multipart for file uploads
- SSE via `StreamingResponse`

---

## Acceptance Criteria
- [ ] All API endpoints respond correctly
- [ ] Chat endpoint streams tokens via SSE
- [ ] AI pipeline produces grounded answers
- [ ] File uploads trigger ingestion pipeline
- [ ] No Streamlit dependencies in backend code
