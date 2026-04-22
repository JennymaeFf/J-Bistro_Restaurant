-- Run this in Supabase SQL Editor if Admin Users shows:
-- column app_users.full_name does not exist
alter table public.app_users add column if not exists full_name text;
alter table public.app_users add column if not exists phone_number text;
alter table public.app_users add column if not exists role text not null default 'user';
alter table public.app_users add column if not exists created_at timestamptz not null default now();

update public.app_users
set full_name = initcap(replace(split_part(email, '@', 1), '.', ' '))
where full_name is null or btrim(full_name) = '';

update public.app_users
set role = 'user'
where role is null or btrim(role) = '';

notify pgrst, 'reload schema';
