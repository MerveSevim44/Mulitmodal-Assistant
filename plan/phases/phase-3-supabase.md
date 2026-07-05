# Phase 3 — Supabase Integration (Database, Auth, Storage)

## Objective
Replace the JSON file-based storage with Supabase-managed PostgreSQL database, implement user authentication via Supabase Auth (GoTrue), and set up Supabase Storage for file uploads.

---

## Tasks

### 3.1 Database Schema
Create PostgreSQL tables in Supabase:

#### Tables
1. **`courses`** — User's academic courses
   - `id` (UUID, PK)
   - `user_id` (UUID, FK → auth.users)
   - `name` (TEXT)
   - `created_at`, `updated_at` (TIMESTAMPTZ)

2. **`topics`** — Topics within a course
   - `id` (UUID, PK)
   - `course_id` (UUID, FK → courses, CASCADE)
   - `name` (TEXT)
   - `created_at`, `updated_at` (TIMESTAMPTZ)

3. **`materials`** — Uploaded learning materials
   - `id` (UUID, PK)
   - `topic_id` (UUID, FK → topics, CASCADE)
   - `type` (TEXT: 'pdf' | 'audio' | 'image')
   - `file_name` (TEXT)
   - `storage_path` (TEXT — Supabase Storage path)
   - `chunk_count` (INTEGER)
   - `created_at` (TIMESTAMPTZ)

4. **`chat_messages`** — Conversation history
   - `id` (UUID, PK)
   - `topic_id` (UUID, FK → topics, CASCADE)
   - `role` (TEXT: 'user' | 'assistant')
   - `content` (TEXT)
   - `metadata` (JSONB — image/audio refs, sources)
   - `created_at` (TIMESTAMPTZ)

### 3.2 Row Level Security (RLS)
Enable RLS on all tables. Policies ensure users can only access their own data:
- Courses: `auth.uid() = user_id`
- Topics: course belongs to user
- Materials: topic → course → user chain
- Chat messages: topic → course → user chain

### 3.3 Authentication
- Supabase Auth with email/password provider
- JWT verification in FastAPI middleware using Supabase's JWKS
- Session management handled by `@supabase/ssr` on the frontend

### 3.4 Storage Buckets
Create 3 storage buckets:

| Bucket | Allowed MIME Types | Max Size |
|--------|--------------------|----------|
| `pdfs` | `application/pdf` | 50MB |
| `audio` | `audio/*`, `video/mp4` | 100MB |
| `images` | `image/png`, `image/jpeg` | 10MB |

Storage policies: authenticated users can upload to their own folder (`{user_id}/...`).

### 3.5 Backend Integration
- `backend/app/db/supabase.py` — Supabase Python client initialization
- `backend/app/db/repository.py` — Data access methods for all tables
- `backend/app/middleware/auth.py` — JWT verification dependency

---

## Environment Variables Required
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret
```

---

## Acceptance Criteria
- [ ] All tables created with proper constraints
- [ ] RLS policies prevent cross-user data access
- [ ] Auth flow: register → login → JWT → API access
- [ ] Files upload to correct Supabase Storage bucket
- [ ] Backend reads/writes data via Supabase client
