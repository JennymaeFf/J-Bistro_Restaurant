-- Run this in Supabase SQL Editor for Delivery + Rider + Payment tracking support.

create table if not exists public.riders (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    phone text,
    status text not null default 'Available'
);

alter table public.orders add column if not exists payment_method text;
alter table public.orders add column if not exists payment_status text not null default 'Pending';
alter table public.orders add column if not exists total_amount numeric(10,2);
alter table public.orders add column if not exists delivery_option text not null default 'Delivery';
alter table public.orders add column if not exists delivery_address text;
alter table public.orders add column if not exists preferred_time text;
alter table public.orders add column if not exists rider_id uuid;
alter table public.orders add column if not exists delivery_status text not null default 'Waiting';

alter table public.riders add column if not exists phone text;
alter table public.riders add column if not exists status text not null default 'Available';

update public.orders
set payment_status = 'Pending'
where payment_status is null or btrim(payment_status) = '';

update public.orders
set delivery_option = 'Delivery'
where delivery_option is null or btrim(delivery_option) = '';

update public.orders
set delivery_status = 'Waiting'
where delivery_status is null or btrim(delivery_status) = '';

update public.riders
set status = 'Available'
where status is null or btrim(status) = '';

do $$
begin
    if not exists (
        select 1
        from information_schema.table_constraints
        where table_schema = 'public'
          and table_name = 'orders'
          and constraint_name = 'orders_rider_id_fkey'
    ) then
        alter table public.orders
        add constraint orders_rider_id_fkey
        foreign key (rider_id) references public.riders(id)
        on delete set null;
    end if;
end $$;

alter table public.riders enable row level security;

drop policy if exists "Allow riders read" on public.riders;
create policy "Allow riders read"
on public.riders for select
to anon
using (true);

drop policy if exists "Allow riders insert" on public.riders;
create policy "Allow riders insert"
on public.riders for insert
to anon
with check (true);

drop policy if exists "Allow riders update" on public.riders;
create policy "Allow riders update"
on public.riders for update
to anon
using (true)
with check (true);

drop policy if exists "Allow riders delete" on public.riders;
create policy "Allow riders delete"
on public.riders for delete
to anon
using (true);

notify pgrst, 'reload schema';
