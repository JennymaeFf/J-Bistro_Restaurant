-- Run this in Supabase SQL Editor for Delivery + Rider + Payment + Inventory + Employee tracking.

create table if not exists public.riders (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    phone text,
    status text not null default 'Available'
);

create table if not exists public.employees (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    position text not null,
    contact_number text,
    shift_schedule text,
    attendance_status text not null default 'Off Duty',
    employment_status text not null default 'Active',
    notes text,
    task_assignment text,
    time_in text,
    time_out text,
    created_at timestamptz not null default now()
);

alter table public.orders add column if not exists payment_method text;
alter table public.orders add column if not exists payment_status text not null default 'Pending';
alter table public.orders add column if not exists total_amount numeric(10,2);
alter table public.orders add column if not exists delivery_option text not null default 'Delivery';
alter table public.orders add column if not exists delivery_address text;
alter table public.orders add column if not exists preferred_time text;
alter table public.orders add column if not exists rider_id uuid;
alter table public.orders add column if not exists delivery_status text not null default 'Waiting';

alter table public.menu_items add column if not exists stock_quantity integer not null default 0;
alter table public.menu_items add column if not exists low_stock_threshold integer not null default 5;

alter table public.riders add column if not exists phone text;
alter table public.riders add column if not exists status text not null default 'Available';

alter table public.employees add column if not exists name text;
alter table public.employees add column if not exists position text;
alter table public.employees add column if not exists contact_number text;
alter table public.employees add column if not exists shift_schedule text;
alter table public.employees add column if not exists attendance_status text not null default 'Off Duty';
alter table public.employees add column if not exists employment_status text not null default 'Active';
alter table public.employees add column if not exists notes text;
alter table public.employees add column if not exists task_assignment text;
alter table public.employees add column if not exists time_in text;
alter table public.employees add column if not exists time_out text;
alter table public.employees add column if not exists created_at timestamptz not null default now();

update public.orders
set payment_status = 'Pending'
where payment_status is null or btrim(payment_status) = '';

update public.orders
set delivery_option = 'Delivery'
where delivery_option is null or btrim(delivery_option) = '';

update public.orders
set delivery_status = 'Waiting'
where delivery_status is null or btrim(delivery_status) = '';

update public.menu_items
set stock_quantity = 0
where stock_quantity is null or stock_quantity < 0;

update public.menu_items
set low_stock_threshold = 5
where low_stock_threshold is null or low_stock_threshold <= 0;

update public.menu_items
set is_available = false
where stock_quantity <= 0;

update public.riders
set status = 'Available'
where status is null or btrim(status) = '';

update public.employees
set attendance_status = 'Off Duty'
where attendance_status is null or btrim(attendance_status) = '';

update public.employees
set employment_status = 'Active'
where employment_status is null or btrim(employment_status) = '';

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
alter table public.employees enable row level security;

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

drop policy if exists "Allow employees read" on public.employees;
create policy "Allow employees read"
on public.employees for select
to anon
using (true);

drop policy if exists "Allow employees insert" on public.employees;
create policy "Allow employees insert"
on public.employees for insert
to anon
with check (true);

drop policy if exists "Allow employees update" on public.employees;
create policy "Allow employees update"
on public.employees for update
to anon
using (true)
with check (true);

drop policy if exists "Allow employees delete" on public.employees;
create policy "Allow employees delete"
on public.employees for delete
to anon
using (true);

notify pgrst, 'reload schema';
