-- Run this in Supabase SQL Editor to support profile picture uploads.
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

drop policy if exists "Users upload own profile images" on storage.objects;
create policy "Users upload own profile images"
on storage.objects for insert
to authenticated
with check (
    bucket_id = 'profile-images'
    and (storage.foldername(name))[1] = auth.uid()::text
);

drop policy if exists "Users update own profile images" on storage.objects;
create policy "Users update own profile images"
on storage.objects for update
to authenticated
using (
    bucket_id = 'profile-images'
    and (storage.foldername(name))[1] = auth.uid()::text
)
with check (
    bucket_id = 'profile-images'
    and (storage.foldername(name))[1] = auth.uid()::text
);

notify pgrst, 'reload schema';
