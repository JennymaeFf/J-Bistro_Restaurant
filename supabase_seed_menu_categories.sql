-- Adds Appetizers and Beverages to the restaurant menu.
-- Run this in Supabase SQL Editor if those categories are empty.

alter table public.menu_items
add column if not exists is_available boolean not null default true;

insert into public.menu_items (name, description, category, price, image, is_available)
values
    ('French Fries', 'Crispy golden fries served hot with a classic dip.', 'Appetizers', 40.00, 'french_fries.png', true),
    ('Spring Rolls', 'Crispy rolls filled with vegetables and savory meat.', 'Appetizers', 50.00, 'spring_rolls.png', true),
    ('Nachos', 'Tortilla chips topped with cheese and flavorful toppings.', 'Appetizers', 60.00, 'nachos.png', true),
    ('Calamares', 'Golden fried squid rings with a crunchy coating.', 'Appetizers', 70.00, 'calamares.png', true),
    ('Garlic Bread', 'Toasted bread brushed with garlic butter.', 'Appetizers', 45.00, 'garlic_bread.png', true),
    ('Coke', 'Refreshing carbonated cola drink.', 'Beverages', 25.00, 'coke.png', true),
    ('Iced Tea', 'Chilled tea with a bright lemon flavor.', 'Beverages', 20.00, 'ice_tea.png', true),
    ('Mango Juice', 'Fresh mango juice with a smooth tropical taste.', 'Beverages', 30.00, 'mango_juice.png', true),
    ('Lemonade', 'Sweet and tangy lemonade served cold.', 'Beverages', 25.00, 'lemonade.png', true),
    ('Water', 'Pure drinking water.', 'Beverages', 15.00, 'water.png', true);

notify pgrst, 'reload schema';

select category, count(*) as item_count
from public.menu_items
group by category
order by category;
