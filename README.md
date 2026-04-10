# J'Bistro Restaurant Flask Project

This project was converted from a Next.js setup into a Python Flask web application for a school restaurant system.

## Tech Stack

- Backend: Flask
- Frontend: Flask Jinja templates, HTML, CSS, JavaScript
- Database: Supabase

## Project Structure

```text
app.py
templates/
static/
  css/
  js/
  images/
requirements.txt
supabase_schema.sql
```

## Features

- Home page
- Menu page
- Add to cart
- Order page
- Dashboard page
- Supabase CRUD for orders
- Supabase read for menu items

## Supabase Setup

Project Name: `J'Bistro_Restaurant`

1. Open your Supabase SQL Editor.
2. Run the SQL inside `supabase_schema.sql`.
3. Make sure the REST API is enabled for the tables.

Default connection values inside `app.py`:

- Supabase URL: `https://fvfvgqpeawafwyczpfbd.supabase.co`
- API key: uses the provided anon/public key by default

You can also override them with environment variables:

```powershell
$env:SUPABASE_URL="https://fvfvgqpeawafwyczpfbd.supabase.co"
$env:SUPABASE_API_KEY="your-key"
$env:FLASK_SECRET_KEY="your-secret"
```

## Installation

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000`.

## Routes

- `/` = Home page
- `/menu` = Menu page
- `/order` = Order page
- `/dashboard` = Dashboard page

## Notes

- If the `menu_items` table is empty or unavailable, the app shows sample menu items so the interface can still be demonstrated.
- Orders require the `orders` table in Supabase to exist.
