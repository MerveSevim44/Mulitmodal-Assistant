# Phase 1 — Project Scaffolding & Directory Structure

## Objective
Create the monorepo directory structure for the full-stack application, establishing clear boundaries between the frontend, backend, and the existing AI engine code.

---

## Tasks

### 1.1 Backend Directory Structure
Create the `backend/` directory with the following layout:

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Pydantic Settings (env vars)
│   ├── dependencies.py       # Shared dependencies (DB, auth)
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py           # JWT verification middleware
│   │   └── cors.py           # CORS configuration
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── courses.py
│   │   ├── topics.py
│   │   ├── materials.py
│   │   └── chat.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── course_service.py
│   │   ├── topic_service.py
│   │   ├── material_service.py
│   │   ├── chat_service.py
│   │   └── ai_engine.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── course.py
│   │   ├── topic.py
│   │   ├── material.py
│   │   └── chat.py
│   └── db/
│       ├── __init__.py
│       ├── supabase.py
│       └── repository.py
├── ai_engine/                 # Migrated & cleaned AI core
│   ├── __init__.py
│   ├── pipeline.py
│   ├── stt.py
│   ├── vision.py
│   ├── retriever.py
│   ├── ingest.py
│   └── prompts/
│       └── diyagram_turleri.yaml
├── requirements.txt
└── Dockerfile
```

### 1.2 Frontend Directory Structure
Initialize Next.js 15 project with TypeScript in `frontend/`.

### 1.3 Shared Configuration
- `.env` at project root with all API keys and Supabase credentials
- `docker-compose.yml` for local development orchestration

---

## Technical Requirements
- Python 3.10+
- Node.js 20+ / npm 10+
- FastAPI 0.115+
- Next.js 15+
- TypeScript 5+

---

## Acceptance Criteria
- [ ] `backend/` directory exists with all subdirectories and `__init__.py` files
- [ ] `frontend/` directory exists with Next.js initialized
- [ ] `docker-compose.yml` exists at project root
- [ ] Both projects can start independently without errors
