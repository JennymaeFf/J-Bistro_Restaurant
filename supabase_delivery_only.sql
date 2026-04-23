-- Run this in Supabase SQL Editor to migrate J'Bistro orders to delivery-only.

alter table public.orders
alter column order_type set default 'Delivery';

alter table public.orders
add column if not exists delivery_address text;

alter table public.orders
add column if not exists delivery_notes text;

update public.orders
set order_type = 'Delivery'
where order_type is null or btrim(order_type) = '' or order_type <> 'Delivery';

notify pgrst, 'reload schema';
