-- Run this in Supabase SQL Editor to add order numbers to existing orders.
-- The app will display these as Order #001, Order #002, and so on.

alter table public.orders
add column if not exists order_number integer;

update public.orders
set order_number = id::integer
where order_number is null;

create sequence if not exists public.orders_order_number_seq;

select setval(
    'public.orders_order_number_seq',
    greatest(coalesce((select max(order_number) from public.orders), 0), 0) + 1,
    false
);

alter table public.orders
alter column order_number set default nextval('public.orders_order_number_seq');

create unique index if not exists orders_order_number_unique
on public.orders(order_number)
where order_number is not null;

notify pgrst, 'reload schema';
