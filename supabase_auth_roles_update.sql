-- Update app_users role handling for the Flask + Supabase auth flow.
-- Run this in the Supabase SQL Editor.

alter table public.app_users
    add column if not exists role varchar(20) default 'customer';

update public.app_users
set role = 'customer'
where role is null or lower(role) = 'user';

alter table public.app_users
    alter column role set default 'customer';

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'app_users_role_check'
    ) then
        alter table public.app_users
            add constraint app_users_role_check
            check (role in ('admin', 'customer', 'staff'));
    end if;
end $$;
