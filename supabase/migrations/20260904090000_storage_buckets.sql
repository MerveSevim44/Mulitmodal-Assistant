-- Storage buckets and access policies.
--
-- `supabase db pull` does not reliably reproduce bucket definitions or
-- storage.objects policies, so they are maintained here by hand. Source of
-- truth for the limits below: plan/phases/phase-3-supabase.md (section 3.4).
--
-- Layout convention: every object lives under a per-user folder, i.e.
--   <bucket>/<user_id>/<file_name>
-- The policies below rely on that first path segment.

-- ---------------------------------------------------------------------------
-- Buckets (all private; access goes through the policies further down)
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('pdfs',   'pdfs',   false,  52428800, array['application/pdf']),
  ('audio',  'audio',  false, 104857600, array['audio/*', 'video/mp4']),
  ('images', 'images', false,  10485760, array['image/png', 'image/jpeg'])
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- ---------------------------------------------------------------------------
-- Policies: an authenticated user may only touch objects inside their own
-- folder, in one of the three buckets above.
-- ---------------------------------------------------------------------------
drop policy if exists "Users read own files" on storage.objects;
create policy "Users read own files"
  on storage.objects for select
  to authenticated
  using (
    bucket_id in ('pdfs', 'audio', 'images')
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "Users upload to own folder" on storage.objects;
create policy "Users upload to own folder"
  on storage.objects for insert
  to authenticated
  with check (
    bucket_id in ('pdfs', 'audio', 'images')
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "Users update own files" on storage.objects;
create policy "Users update own files"
  on storage.objects for update
  to authenticated
  using (
    bucket_id in ('pdfs', 'audio', 'images')
    and (storage.foldername(name))[1] = auth.uid()::text
  )
  with check (
    bucket_id in ('pdfs', 'audio', 'images')
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "Users delete own files" on storage.objects;
create policy "Users delete own files"
  on storage.objects for delete
  to authenticated
  using (
    bucket_id in ('pdfs', 'audio', 'images')
    and (storage.foldername(name))[1] = auth.uid()::text
  );
