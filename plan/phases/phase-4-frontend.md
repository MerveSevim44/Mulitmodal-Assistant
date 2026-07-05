# Phase 4 — Next.js Frontend Application

## Objective
Build a production-grade, visually stunning Next.js client application with TypeScript that communicates with the FastAPI backend via Axios and implements real-time streaming chat using Server-Sent Events (SSE).

---

## Tasks

### 4.1 Project Initialization
- Next.js 15 with App Router
- TypeScript configuration
- Vanilla CSS with CSS Modules
- Google Fonts: Outfit (body) + JetBrains Mono (labels/code)

### 4.2 Core Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| `axios` | latest | HTTP client for API requests |
| `@supabase/supabase-js` | latest | Auth + direct storage uploads |
| `@supabase/ssr` | latest | Server-side auth helpers |
| `zustand` | latest | Client state management |

### 4.3 Axios Client Configuration
- Base URL from `NEXT_PUBLIC_API_URL`
- Request interceptor: attach Supabase JWT as `Authorization: Bearer` header
- Response interceptor: handle 401 → redirect to login
- Error interceptor: toast notifications for API errors

### 4.4 Streaming Strategy
Axios handles all standard REST calls. For the chat endpoint (SSE), use native `fetch()` with `ReadableStream`:
- `POST /api/v1/topics/{id}/chat` returns `text/event-stream`
- Parse `data: {...}\n\n` lines incrementally
- Update React state token-by-token for animated typing effect

### 4.5 Pages

#### Authentication
- `/login` — Email/password login form
- `/register` — Registration form with password validation

#### Dashboard
- `/` — Course grid (home page after login)
- `/courses/[courseId]` — Topic grid for a specific course
- `/courses/[courseId]/topics/[topicId]` — Topic workspace (file upload + chat)

### 4.6 Key Components

#### Layout
- `Sidebar` — Course navigation, "New Course" button, active state
- `Breadcrumb` — Navigation trail (Home → Course → Topic)
- `Header` — User avatar, settings, logout

#### Courses & Topics
- `CourseCard` — Gradient card with course name, topic count
- `TopicCard` — Card with topic name, material indicators
- `CreateModal` — Reusable modal for creating courses/topics

#### Materials
- `FileUploader` — Drag-and-drop upload with progress indicator
- `MaterialList` — Grid of uploaded materials with type icons
- `MaterialCard` — Individual material with delete action

#### Chat
- `ChatContainer` — Full chat interface with message list and input
- `ChatMessage` — Individual message bubble (user/assistant styling)
- `StreamingMessage` — Typing animation with cursor for streaming responses
- `ChatInput` — Text input with optional image/audio attachment toggles
- `SourceBadge` — Colored badge showing source type (PDF/Audio/Image)

### 4.7 Design System
Dark-mode aesthetic matching the existing Streamlit theme:

```css
:root {
  --bg-primary: #0a0a10;
  --bg-secondary: #0d0d14;
  --bg-card: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  --accent: #6366f1;
  --accent-light: #818cf8;
  --accent-glow: rgba(99, 102, 241, 0.15);
  --text-primary: #e0e0ff;
  --text-secondary: #a0a0c0;
  --text-label: #6366f1;
  --border: #1e1e2e;
  --border-accent: #6366f1;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --shadow-card: 0 4px 12px rgba(99, 102, 241, 0.15);
  --shadow-hover: 0 8px 20px rgba(99, 102, 241, 0.25);
  --font-sans: 'Outfit', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --transition: all 0.3s ease;
}
```

### 4.8 Animations & Micro-Interactions
- Card hover: translateY(-2px) + glow shadow
- Page transitions: fade-in on route change
- Streaming text: cursor blink animation
- File upload: progress bar with gradient fill
- Toast notifications: slide-in from top-right
- Button press: scale(0.98) feedback
- Sidebar item: slide highlight on active state

---

## Acceptance Criteria
- [ ] Login/register works with Supabase Auth
- [ ] All API calls use Axios with JWT auth
- [ ] Streaming chat renders tokens progressively
- [ ] File uploads show progress and trigger ingestion
- [ ] Responsive layout works on desktop and tablet
- [ ] Design matches the dark-mode aesthetic specification
- [ ] All interactive elements have micro-animations
