-- Run this in Supabase SQL Editor to support profile picture uploads.
-- The Flask backend uploads with SUPABASE_SERVICE_ROLE_KEY, which bypasses
-- row level policies server-side. Keep that key only in server env vars.
-- The Flask app stores public image URLs from this bucket in app_users.profile_image.

alter table public.app_users add column if not exists profile_image text;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'profile-images',
    'profile-images',
    true,
    5242880,
    array['image/jpeg', 'image/png']
)
on conflict (id) do update
set
    public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "Profile images are publicly readable" on storage.objects;
create policy "Profile images are publicly readable"
on storage.objects for select
to anon, authenticated
using (bucket_id = 'profile-images');

notify pgrst, 'reload schema';
