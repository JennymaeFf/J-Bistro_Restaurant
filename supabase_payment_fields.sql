-- Run this in Supabase SQL Editor to store GCash/bank payment details.

alter table public.orders
add column if not exists payment_bank text;

alter table public.orders
add column if not exists payment_reference text;

notify pgrst, 'reload schema';
