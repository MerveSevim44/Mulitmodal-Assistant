# Phase 5 — Integration Testing, Deployment & Production Hardening

## Objective
Ensure all components work together seamlessly, implement production-grade error handling, security measures, and prepare deployment configurations.

---

## Tasks

### 5.1 Docker Compose Configuration
Local development orchestration:
- `backend` service: FastAPI on port 8000
- `frontend` service: Next.js on port 3000
- Shared `.env` file for configuration
- Volume mounts for hot-reload development

### 5.2 Integration Testing

#### Auth Flow
1. Register new user → verify Supabase creates user
2. Login → verify JWT returned
3. API request with JWT → verify backend authenticates
4. API request without JWT → verify 401 returned
5. Access other user's data → verify 403/empty result (RLS)

#### Course/Topic CRUD
1. Create course → verify in database
2. Create topic under course → verify relationship
3. Update course name → verify propagation
4. Delete course → verify cascade deletes topics, materials, messages

#### Material Ingestion Flow
1. Upload PDF → verify file in Supabase Storage
2. Verify ChromaDB chunks created with correct metadata
3. Upload same file again → verify old chunks replaced (no duplicates)
4. Delete material → verify chunks removed from ChromaDB

#### Streaming Chat
1. Send message → verify SSE stream opens
2. Verify tokens arrive incrementally
3. Verify final message saved to chat_messages table
4. Verify source attribution badges match retrieved sources
5. Verify conversation history maintains context

### 5.3 Production Security Checklist
- [ ] Rate limiting: 60 req/min per user on API, 10 req/min on chat
- [ ] File validation: type + size checked server-side (not just MIME header)
- [ ] CORS: whitelist only the frontend origin
- [ ] API keys: never exposed to frontend; backend-only
- [ ] SQL injection: prevented by Supabase client parameterized queries
- [ ] XSS: React's default escaping + CSP headers

### 5.4 Error Handling
- Global FastAPI exception handler → structured JSON error responses
- Frontend Axios interceptor → toast notifications for errors
- Logging: structured JSON logs with request ID tracing

### 5.5 Performance Optimization
- [ ] Frontend: Code splitting via Next.js dynamic imports
- [ ] Frontend: Image optimization via next/image
- [ ] Backend: Connection pooling for Supabase
- [ ] Backend: Async I/O for all external API calls
- [ ] Caching: Course/topic lists with short TTL

### 5.6 Deployment Configuration
- `Dockerfile` for backend (Python 3.10+, multi-stage build)
- Next.js deployment config (Vercel or standalone)
- Environment variable documentation
- Health check endpoint at `/api/v1/health`

---

## Acceptance Criteria
- [ ] All integration tests pass
- [ ] Docker Compose starts all services successfully
- [ ] No security vulnerabilities in checklist
- [ ] Error states handled gracefully (network down, API error, invalid input)
- [ ] Application performs well under normal usage patterns
