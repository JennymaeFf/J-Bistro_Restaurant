-- Adds availability support for Admin Menu items.
-- Run this in the Supabase SQL Editor, then refresh/redeploy the app if needed.

alter table public.menu_items
add column if not exists is_available boolean not null default true;

update public.menu_items
set is_available = true
where is_available is null;

notify pgrst, 'reload schema';

select column_name, data_type, column_default, is_nullable
from information_schema.columns
where table_schema = 'public'
  and table_name = 'menu_items'
  and column_name = 'is_available';
