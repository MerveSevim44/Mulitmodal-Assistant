-- Spaced repetition (SM-2) scheduling state.
--
-- The review schedule lives on `topics` itself rather than in a side table:
-- every topic has exactly one schedule, and the home dashboard orders the
-- whole review queue by `next_review_at` in a single query. The per-review
-- log below is separate, because that one is append-only and unbounded.
--
-- Source of truth for the algorithm: backend/app/services/spaced_repetition.py

-- ---------------------------------------------------------------------------
-- Scheduling state on topics
-- ---------------------------------------------------------------------------
alter table public.topics
  -- Null until the topic has been reviewed at least once.
  add column if not exists last_reviewed_at timestamptz,
  -- Defaults to now(): a freshly added topic — and every topic that already
  -- existed before this migration — is due straight away.
  add column if not exists next_review_at   timestamptz not null default now(),
  -- SM-2 ease factor. Starts at 2.5 and is floored at 1.3 by the algorithm.
  add column if not exists ease_factor      real        not null default 2.5,
  -- Length of the current interval, in days. 0 = never scheduled yet.
  add column if not exists interval_days    integer     not null default 0,
  -- Consecutive successful reviews; reset to 0 on a failed ("Zor") review.
  add column if not exists repetitions      integer     not null default 0,
  -- How many times the topic has been failed. Never reset — it is the
  -- long-run signal for weak-topic detection.
  add column if not exists lapses           integer     not null default 0;

alter table public.topics
  drop constraint if exists topics_ease_factor_range;
alter table public.topics
  add constraint topics_ease_factor_range check (ease_factor >= 1.3 and ease_factor <= 5.0);

alter table public.topics
  drop constraint if exists topics_interval_days_nonneg;
alter table public.topics
  add constraint topics_interval_days_nonneg check (interval_days >= 0);

-- The review queue is always "ordered by next_review_at, oldest first".
create index if not exists topics_next_review_at_idx
  on public.topics (next_review_at);

-- ---------------------------------------------------------------------------
-- Review log — one row per graded review
-- ---------------------------------------------------------------------------
create table if not exists public.topic_reviews (
  id            uuid        primary key default gen_random_uuid(),
  topic_id      uuid        not null references public.topics(id) on delete cascade,
  -- The button the user pressed.
  grade         text        not null check (grade in ('hard', 'medium', 'easy', 'very_easy')),
  -- The SM-2 quality that grade maps to (2..5), stored so a later change to
  -- the mapping does not rewrite the meaning of past reviews.
  quality       smallint    not null check (quality between 0 and 5),
  -- The scheduling state this review produced.
  ease_factor   real        not null,
  interval_days integer     not null,
  repetitions   integer     not null,
  next_review_at timestamptz not null,
  reviewed_at   timestamptz not null default now()
);

create index if not exists topic_reviews_topic_id_reviewed_at_idx
  on public.topic_reviews (topic_id, reviewed_at desc);

-- ---------------------------------------------------------------------------
-- RLS — same topic -> course -> user chain the other child tables use
-- ---------------------------------------------------------------------------
alter table public.topic_reviews enable row level security;

drop policy if exists "Users read own topic reviews" on public.topic_reviews;
create policy "Users read own topic reviews"
  on public.topic_reviews for select
  to authenticated
  using (
    exists (
      select 1
      from public.topics t
      join public.courses c on c.id = t.course_id
      where t.id = topic_reviews.topic_id
        and c.user_id = auth.uid()
    )
  );

drop policy if exists "Users insert own topic reviews" on public.topic_reviews;
create policy "Users insert own topic reviews"
  on public.topic_reviews for insert
  to authenticated
  with check (
    exists (
      select 1
      from public.topics t
      join public.courses c on c.id = t.course_id
      where t.id = topic_reviews.topic_id
        and c.user_id = auth.uid()
    )
  );

drop policy if exists "Users delete own topic reviews" on public.topic_reviews;
create policy "Users delete own topic reviews"
  on public.topic_reviews for delete
  to authenticated
  using (
    exists (
      select 1
      from public.topics t
      join public.courses c on c.id = t.course_id
      where t.id = topic_reviews.topic_id
        and c.user_id = auth.uid()
    )
  );

-- ---------------------------------------------------------------------------
-- PostgREST caches the table schema, and the API keeps answering "column
-- topics.last_reviewed_at does not exist" until that cache is refreshed.
-- Supabase's own event trigger usually does this, but not always straight
-- away — so it is asked for explicitly here.
-- ---------------------------------------------------------------------------
notify pgrst, 'reload schema';
