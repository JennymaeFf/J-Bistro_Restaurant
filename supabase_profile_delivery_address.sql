-- Run this in Supabase SQL Editor to store default delivery address on user profiles.

alter table public.app_users
add column if not exists delivery_address text;

notify pgrst, 'reload schema';
