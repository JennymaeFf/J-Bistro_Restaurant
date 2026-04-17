import json
import os
import re
from base64 import urlsafe_b64decode
from typing import Any

import requests
from env_loader import load_env_file

load_env_file()

REQUEST_TIMEOUT = 15
PLACEHOLDER_VALUES = {
    "https://your-project.supabase.co",
    "your-supabase-anon-key",
    "",
}

SAMPLE_MENU_ITEMS = [
    {
        "id": 1,
        "name": "Chicken Adobo",
        "description": "Tender chicken cooked in soy sauce, vinegar, and garlic.",
        "category": "main-course",
        "price": 120.0,
        "image": "spicychicken.png",
    },
    {
        "id": 2,
        "name": "Beef Steak",
        "description": "Juicy beef steak grilled to perfection.",
        "category": "main-course",
        "price": 150.0,
        "image": "beefsteak.png",
    },
    {
        "id": 3,
        "name": "Fried Chicken",
        "description": "Crispy fried chicken with herbs and spices.",
        "category": "main-course",
        "price": 100.0,
        "image": "fried_chicken.png",
    },
    {
        "id": 4,
        "name": "Pork Sinigang",
        "description": "Sour soup with pork, vegetables, and tamarind.",
        "category": "main-course",
        "price": 130.0,
        "image": "pork_sinigang.png",
    },
    {
        "id": 5,
        "name": "Grilled Fish",
        "description": "Fresh fish grilled with lemon and herbs.",
        "category": "main-course",
        "price": 140.0,
        "image": "salmonfillet.png",
    },
    {
        "id": 6,
        "name": "French Fries",
        "description": "Crispy golden fries served hot.",
        "category": "appetizers",
        "price": 40.0,
        "image": "french_fries.png",
    },
    {
        "id": 7,
        "name": "Spring Rolls",
        "description": "Crispy rolls filled with vegetables and meat.",
        "category": "appetizers",
        "price": 50.0,
        "image": "spring_rolls.png",
    },
    {
        "id": 8,
        "name": "Nachos",
        "description": "Tortilla chips with cheese and toppings.",
        "category": "appetizers",
        "price": 60.0,
        "image": "nachos.png",
    },
    {
        "id": 9,
        "name": "Calamares",
        "description": "Crispy fried squid rings.",
        "category": "appetizers",
        "price": 70.0,
        "image": "calamares.png",
    },
    {
        "id": 10,
        "name": "Garlic Bread",
        "description": "Toasted bread with garlic butter.",
        "category": "appetizers",
        "price": 45.0,
        "image": "garlic_bread.png",
    },
    {
        "id": 11,
        "name": "Coke",
        "description": "Refreshing carbonated cola drink.",
        "category": "beverages",
        "price": 25.0,
        "image": "coke.png",
        "sizes": {"small": 20.0, "medium": 25.0, "large": 30.0}
    },
    {
        "id": 12,
        "name": "Iced Tea",
        "description": "Chilled tea with lemon.",
        "category": "beverages",
        "price": 20.0,
        "image": "ice_tea.png",
        "sizes": {"small": 18.0, "medium": 20.0, "large": 25.0}
    },
    {
        "id": 13,
        "name": "Mango Juice",
        "description": "Fresh mango juice.",
        "category": "beverages",
        "price": 30.0,
        "image": "mango_juice.png",
        "sizes": {"small": 25.0, "medium": 30.0, "large": 35.0}
    },
    {
        "id": 14,
        "name": "Lemonade",
        "description": "Sweet and tangy lemonade.",
        "category": "beverages",
        "price": 25.0,
        "image": "lemonade.png",
        "sizes": {"small": 20.0, "medium": 25.0, "large": 30.0}
    },
    {
        "id": 15,
        "name": "Water",
        "description": "Pure drinking water.",
        "category": "beverages",
        "price": 15.0,
        "image": "water.png",
        "sizes": {"small": 12.0, "medium": 15.0, "large": 18.0}
    },
]


def valid_email_message(email: str) -> str | None:
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return "Please enter a valid email address."
    return None


def normalize_env_value(value: str | None, fallback: str) -> str:
    cleaned = (value or fallback).strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
        cleaned = cleaned[1:-1].strip()
    return cleaned


def current_supabase_config() -> tuple[str, str]:
    url = normalize_env_value(os.environ.get("SUPABASE_URL"), "")
    api_key = normalize_env_value(os.environ.get("SUPABASE_API_KEY"), "")
    return url, api_key


def decode_jwt_payload(token: str) -> dict[str, Any] | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None

    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = urlsafe_b64decode(payload + padding).decode("utf-8")
        data = json.loads(decoded)
        return data if isinstance(data, dict) else None
    except (ValueError, UnicodeDecodeError):
        return None


def detect_key_type(api_key: str) -> str:
    if api_key.startswith("sb_publishable_"):
        return "publishable"
    payload = decode_jwt_payload(api_key)
    if not payload:
        return "unknown"
    return str(payload.get("role", "unknown"))


def supabase_config_error() -> str | None:
    supabase_url, supabase_api_key = current_supabase_config()
    if supabase_url in PLACEHOLDER_VALUES or supabase_api_key in PLACEHOLDER_VALUES:
        return (
            "Supabase credentials are still using placeholder values. "
            "Update SUPABASE_URL and SUPABASE_API_KEY in your Vercel environment variables."
        )
    if "your-project" in supabase_url or "your-supabase" in supabase_api_key:
        return (
            "Supabase credentials still look like placeholders. "
            "Use your real project URL and anon public key from the Supabase dashboard."
        )
    if not supabase_url.startswith("https://") or ".supabase.co" not in supabase_url:
        return "SUPABASE_URL is not in the correct format. It should look like https://your-project-ref.supabase.co"
    if len(supabase_api_key) < 80:
        return "SUPABASE_API_KEY looks too short. Use the full anon public key from Supabase."
    key_type = detect_key_type(supabase_api_key)
    if key_type == "publishable":
        return "You are using the Supabase publishable key. Use the anon JWT key instead."
    if key_type == "service_role":
        return "You are using the Supabase service_role key. Do not use that in this app. Use the anon key instead."
    if key_type not in {"anon", "authenticated"}:
        return f"SUPABASE_API_KEY does not look like a valid anon key. Detected key type: {key_type}."
    return None


def supabase_headers(prefer_return: str | None = None) -> dict[str, str]:
    _, supabase_api_key = current_supabase_config()
    headers = {
        "apikey": supabase_api_key,
        "Authorization": f"Bearer {supabase_api_key}",
        "Content-Type": "application/json",
    }
    if prefer_return:
        headers["Prefer"] = prefer_return
    return headers


def auth_headers() -> dict[str, str]:
    _, supabase_api_key = current_supabase_config()
    return {
        "apikey": supabase_api_key,
        "Authorization": f"Bearer {supabase_api_key}",
        "Content-Type": "application/json",
    }


def parse_response_error(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"Request failed with status {response.status_code}."

    for key in ("msg", "message", "error_description", "error"):
        value = payload.get(key)
        if value:
            return str(value)
    return f"Request failed with status {response.status_code}."


def register_user(email: str, password: str) -> tuple[bool, str]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error

    supabase_url, _ = current_supabase_config()
    try:
        signup_response = requests.post(
            f"{supabase_url}/auth/v1/signup",
            headers=auth_headers(),
            json={"email": email, "password": password},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to contact Supabase right now."

    if signup_response.status_code >= 400:
        return False, parse_response_error(signup_response)

    payload = signup_response.json()
    user_data = payload.get("user") or {}
    user_id = user_data.get("id")
    if not user_id:
        return False, "Registration succeeded, but no user id was returned."

    try:
        profile_response = requests.post(
            f"{supabase_url}/rest/v1/app_users",
            headers=supabase_headers("return=minimal,resolution=merge-duplicates"),
            json={"id": user_id, "email": email},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Account created, but the app profile could not be saved."

    if profile_response.status_code >= 400:
        return False, parse_response_error(profile_response)

    return True, "Registration successful."


def authenticate_user(email: str, password: str) -> tuple[bool, str, dict[str, Any] | None]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error, None

    supabase_url, _ = current_supabase_config()
    try:
        response = requests.post(
            f"{supabase_url}/auth/v1/token?grant_type=password",
            headers=auth_headers(),
            json={"email": email, "password": password},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to contact Supabase right now.", None

    if response.status_code >= 400:
        return False, parse_response_error(response), None

    payload = response.json()
    user_data = payload.get("user") or {}
    user_session = {
        "id": user_data.get("id"),
        "email": user_data.get("email", email),
        "access_token": payload.get("access_token"),
    }
    return True, "Login successful.", user_session


def fetch_menu_items() -> tuple[list[dict[str, Any]], str | None]:
    # For development, always return sample items
    return SAMPLE_MENU_ITEMS, None


def fetch_orders() -> tuple[list[dict[str, Any]], str | None]:
    config_error = supabase_config_error()
    if config_error:
        return [], config_error

    supabase_url, _ = current_supabase_config()
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/orders",
            headers=supabase_headers(),
            params={"select": "*", "order": "created_at.desc"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return [], "Unable to load orders from Supabase right now."

    if response.status_code >= 400:
        return [], parse_response_error(response)

    orders = response.json()
    for order in orders:
        if isinstance(order.get("items"), str):
            try:
                order["items"] = json.loads(order["items"])
            except json.JSONDecodeError:
                order["items"] = []
    return orders, None


def get_next_table_number() -> tuple[int, str | None]:
    """Get the next table number based on existing orders."""
    orders, error = fetch_orders()
    if error:
        return 1, None  # Default to 1 if we can't fetch orders
    
    # Find the highest table number
    max_table = 0
    for order in orders:
        table_str = order.get("table_number", "")
        if table_str and table_str.startswith("Table "):
            try:
                table_num = int(table_str.replace("Table ", ""))
                max_table = max(max_table, table_num)
            except ValueError:
                continue
    
    return max_table + 1, None


def create_order(customer_name: str, cart: list[dict[str, Any]], total_amount: float, payment_method: str) -> tuple[bool, str]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error

    # Get next table number
    table_number, table_error = get_next_table_number()
    if table_error:
        return False, f"Unable to generate table number: {table_error}"

    supabase_url, _ = current_supabase_config()
    payload = {
        "customer_name": customer_name,
        "table_number": f"Table {table_number}",
        "items": cart,
        "total_amount": total_amount,
        "payment_method": payment_method,
        "status": "Pending",
    }
    try:
        response = requests.post(
            f"{supabase_url}/rest/v1/orders",
            headers=supabase_headers("return=minimal"),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to save the order right now."

    if response.status_code >= 400:
        return False, parse_response_error(response)

    return True, f"Order submitted successfully. Your table number is {table_number}."


def update_order_status(order_id: int, status: str) -> tuple[bool, str]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error

    supabase_url, _ = current_supabase_config()
    try:
        response = requests.patch(
            f"{supabase_url}/rest/v1/orders",
            headers=supabase_headers("return=minimal"),
            params={"id": f"eq.{order_id}"},
            json={"status": status},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to update the order right now."

    if response.status_code >= 400:
        return False, parse_response_error(response)

    return True, "Order status updated."


def delete_order(order_id: int) -> tuple[bool, str]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error

    supabase_url, _ = current_supabase_config()
    try:
        response = requests.delete(
            f"{supabase_url}/rest/v1/orders",
            headers=supabase_headers("return=minimal"),
            params={"id": f"eq.{order_id}"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to delete the order right now."

    if response.status_code >= 400:
        return False, parse_response_error(response)

    return True, "Order deleted."
