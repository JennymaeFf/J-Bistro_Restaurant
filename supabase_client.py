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


def default_full_name(email: str) -> str:
    username = email.split("@")[0] if email else "Customer"
    return username.replace(".", " ").replace("_", " ").title()


def normalize_role(role_value: Any) -> str:
    role = str(role_value or "user").strip().lower()
    return role if role in {"admin", "user"} else "user"


def profile_role_error() -> str:
    return (
        "Login successful, but the app could not verify your account role from app_users.role. "
        "Check that the role column exists, the Supabase schema cache is refreshed, and the account "
        "is saved with role 'admin' or 'user'."
    )


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


def is_schema_cache_column_error(message: str, *columns: str) -> bool:
    lowered = message.lower()
    return "schema cache" in lowered and any(column.lower() in lowered for column in columns)


def schema_cache_fix_message(*columns: str) -> str:
    column_list = ", ".join(columns)
    return (
        f"Database schema is missing or has not refreshed these columns: {column_list}. "
        "Run the latest supabase_schema.sql in Supabase SQL Editor, then run "
        "NOTIFY pgrst, 'reload schema'; and try again."
    )


def register_user(email: str, password: str, role: str = "user") -> tuple[bool, str]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error
    requested_role = normalize_role(role)
    if requested_role not in {"user", "admin"}:
        requested_role = "user"

    supabase_url, _ = current_supabase_config()
    try:
        existing_response = requests.get(
            f"{supabase_url}/rest/v1/app_users",
            headers=supabase_headers(),
            params={"email": f"eq.{email}", "select": "id,email,role", "limit": "1"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        existing_response = None

    if existing_response and existing_response.status_code < 400:
        existing_rows = existing_response.json()
        if existing_rows:
            if requested_role == "admin":
                try:
                    promote_response = requests.patch(
                        f"{supabase_url}/rest/v1/app_users",
                        headers=supabase_headers("return=minimal"),
                        params={"email": f"eq.{email}"},
                        json={"role": "admin"},
                        timeout=REQUEST_TIMEOUT,
                    )
                except requests.RequestException:
                    return False, "Email already exists. Could not promote this account to admin right now."

                if promote_response.status_code >= 400:
                    return False, parse_response_error(promote_response)
                return True, "Existing account updated to admin."
            return False, "Email already exists."

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
        signup_error = parse_response_error(signup_response)
        lowered_signup_error = signup_error.lower()
        if (
            "already registered" in lowered_signup_error
            or "already exists" in lowered_signup_error
            or "duplicate" in lowered_signup_error
        ):
            if requested_role == "admin":
                try:
                    promote_existing_response = requests.patch(
                        f"{supabase_url}/rest/v1/app_users",
                        headers=supabase_headers("return=minimal"),
                        params={"email": f"eq.{email}"},
                        json={"role": "admin"},
                        timeout=REQUEST_TIMEOUT,
                    )
                except requests.RequestException:
                    return False, "Email already exists."

                if promote_existing_response.status_code < 400:
                    return True, "Existing account updated to admin."
            return False, "Email already exists."
        return False, signup_error

    payload = signup_response.json()
    user_data = payload.get("user") or {}
    user_id = user_data.get("id")
    if not user_id:
        return False, "Registration succeeded, but no user id was returned."

    try:
        profile_response = requests.post(
            f"{supabase_url}/rest/v1/app_users",
            headers=supabase_headers("return=minimal,resolution=merge-duplicates"),
            params={"on_conflict": "id"},
            # Role is set by database default ('user') to avoid registration
            # failures when the schema cache has not refreshed yet.
            json={
                "id": user_id,
                "email": email,
                "full_name": default_full_name(email),
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Account created, but the app profile could not be saved."

    if profile_response.status_code >= 400:
        error_message = parse_response_error(profile_response)
        lowered_error = error_message.lower()
        if "duplicate" in lowered_error or "already exists" in lowered_error:
            if requested_role == "admin":
                try:
                    promote_profile_response = requests.patch(
                        f"{supabase_url}/rest/v1/app_users",
                        headers=supabase_headers("return=minimal"),
                        params={"email": f"eq.{email}"},
                        json={"role": "admin"},
                        timeout=REQUEST_TIMEOUT,
                    )
                except requests.RequestException:
                    return False, "Email already exists."

                if promote_profile_response.status_code < 400:
                    return True, "Existing account updated to admin."
            return False, "Email already exists."
        if "full_name" not in lowered_error:
            return False, error_message

        fallback_payload = {"id": user_id, "email": email}

        try:
            fallback_response = requests.post(
                f"{supabase_url}/rest/v1/app_users",
                headers=supabase_headers("return=minimal,resolution=merge-duplicates"),
                params={"on_conflict": "id"},
                json=fallback_payload,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException:
            return False, "Account created, but the app profile could not be saved."

        if fallback_response.status_code >= 400:
            return False, parse_response_error(fallback_response)

    if requested_role == "admin":
        try:
            role_response = requests.patch(
                f"{supabase_url}/rest/v1/app_users",
                headers=supabase_headers("return=minimal"),
                params={"id": f"eq.{user_id}"},
                json={"role": "admin"},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException:
            return True, "Registration successful, but admin role could not be assigned right now."

        if role_response.status_code >= 400:
            role_error = parse_response_error(role_response)
            if is_schema_cache_column_error(role_error, "role") or "role" in role_error.lower():
                return True, (
                    "Registration successful, but admin role could not be assigned because the role column "
                    "is unavailable in schema cache. Run NOTIFY pgrst, 'reload schema'; and update role manually."
                )
            return True, f"Registration successful, but admin role assignment failed: {role_error}"
        return True, "Admin registration successful."

    return True, "Registration successful."


def fetch_user_profile(user_id: str, email: str = "") -> tuple[dict[str, Any] | None, str | None]:
    config_error = supabase_config_error()
    if config_error:
        return None, config_error

    supabase_url, _ = current_supabase_config()
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/app_users",
            headers=supabase_headers(),
            params={"id": f"eq.{user_id}", "select": "*", "limit": "1"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return None, "Unable to load your profile right now."

    if response.status_code >= 400:
        error_message = parse_response_error(response)
        if is_schema_cache_column_error(error_message, "role") or "role" in error_message.lower():
            return None, schema_cache_fix_message("app_users.role")
        return None, error_message

    rows = response.json()
    if rows:
        profile = rows[0]
        profile.setdefault("full_name", default_full_name(profile.get("email", email)))
        if "role" not in profile:
            return None, profile_role_error()
        profile["role"] = normalize_role(profile.get("role"))
        return profile, None

    if not email:
        return None, "Profile not found."

    # If the id-based lookup fails, try matching by email first.
    # This preserves role assignments like 'admin' on existing rows.
    try:
        email_lookup_response = requests.get(
            f"{supabase_url}/rest/v1/app_users",
            headers=supabase_headers(),
            params={"email": f"eq.{email}", "select": "*", "limit": "1"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        email_lookup_response = None

    if email_lookup_response and email_lookup_response.status_code < 400:
        email_rows = email_lookup_response.json()
        if email_rows:
            profile = email_rows[0]
            profile.setdefault("full_name", default_full_name(profile.get("email", email)))
            if "role" not in profile:
                return None, profile_role_error()
            profile["role"] = normalize_role(profile.get("role"))
            return profile, None

    profile = {
        "id": user_id,
        "email": email,
        "full_name": default_full_name(email),
        "role": "user",
    }
    try:
        create_response = requests.post(
            f"{supabase_url}/rest/v1/app_users",
            headers=supabase_headers("return=representation,resolution=merge-duplicates"),
            params={"on_conflict": "id"},
            json=profile,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return profile, "Profile loaded with default details, but could not be saved yet."

    if create_response.status_code >= 400:
        error_message = parse_response_error(create_response)
        lowered_error = error_message.lower()
        if "email" in lowered_error and "duplicate" in lowered_error:
            try:
                duplicate_email_lookup = requests.get(
                    f"{supabase_url}/rest/v1/app_users",
                    headers=supabase_headers(),
                    params={"email": f"eq.{email}", "select": "*", "limit": "1"},
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.RequestException:
                duplicate_email_lookup = None

            if duplicate_email_lookup and duplicate_email_lookup.status_code < 400:
                duplicate_rows = duplicate_email_lookup.json()
                if duplicate_rows:
                    resolved_profile = duplicate_rows[0]
                    resolved_profile.setdefault("full_name", default_full_name(resolved_profile.get("email", email)))
                    if "role" not in resolved_profile:
                        return None, profile_role_error()
                    resolved_profile["role"] = normalize_role(resolved_profile.get("role"))
                    return resolved_profile, None

        if is_schema_cache_column_error(error_message, "role") or "role" in error_message.lower():
            return None, schema_cache_fix_message("app_users.role")
        return profile, error_message

    created_rows = create_response.json()
    final_profile = created_rows[0] if created_rows else profile
    if "role" not in final_profile:
        return None, profile_role_error()
    final_profile["role"] = normalize_role(final_profile.get("role"))
    return final_profile, None


def update_user_profile(user_id: str, full_name: str) -> tuple[bool, str, dict[str, Any] | None]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error, None

    full_name = full_name.strip()
    if not full_name:
        return False, "Name is required.", None

    supabase_url, _ = current_supabase_config()
    try:
        response = requests.patch(
            f"{supabase_url}/rest/v1/app_users",
            headers=supabase_headers("return=representation"),
            params={"id": f"eq.{user_id}"},
            json={"full_name": full_name},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to update your profile right now.", None

    if response.status_code >= 400:
        error_message = parse_response_error(response)
        if is_schema_cache_column_error(error_message, "full_name"):
            return False, schema_cache_fix_message("app_users.full_name"), None
        return False, error_message, None

    rows = response.json()
    if not rows:
        return False, "Profile not found.", None
    return True, "Profile updated successfully.", rows[0]


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
    user_id = user_data.get("id")
    profile, profile_message = fetch_user_profile(user_id, user_data.get("email", email)) if user_id else (None, None)
    if not profile:
        return False, profile_message or "Login successful, but no app_users profile was found for this account.", None
    if profile_message:
        return False, profile_message, None

    user_role = normalize_role(profile.get("role"))
    user_session = {
        "id": user_id,
        "email": user_data.get("email", email),
        "access_token": payload.get("access_token"),
        "full_name": profile.get("full_name") or default_full_name(user_data.get("email", email)),
        "role": user_role,
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

    try:
        orders = response.json()
    except ValueError:
        return [], f"Unable to read orders from Supabase. Status code: {response.status_code}."

    for order in orders:
        if isinstance(order.get("items"), str):
            try:
                order["items"] = json.loads(order["items"])
            except json.JSONDecodeError:
                order["items"] = []
    return orders, None


def fetch_latest_order(customer_name: str | None = None) -> tuple[dict[str, Any] | None, str | None]:
    config_error = supabase_config_error()
    if config_error:
        return None, config_error

    supabase_url, _ = current_supabase_config()
    params = {
        "select": "id,customer_name,order_type,table_number,items,total_amount,payment_method,status,created_at",
        "order": "created_at.desc,id.desc",
        "limit": "1",
    }
    if customer_name:
        params["customer_name"] = f"eq.{customer_name}"

    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/orders",
            headers=supabase_headers(),
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return None, "Unable to load the latest order right now."

    if response.status_code >= 400:
        return None, parse_response_error(response)

    try:
        rows = response.json()
    except ValueError:
        return None, "Unable to read latest order data from Supabase."

    if not rows:
        return None, None

    latest_order = rows[0]
    if isinstance(latest_order.get("items"), str):
        try:
            latest_order["items"] = json.loads(latest_order["items"])
        except json.JSONDecodeError:
            latest_order["items"] = []
    return latest_order, None


def fetch_admin_dashboard_stats() -> tuple[dict[str, Any], str | None]:
    empty_stats = {
        "total_orders": 0,
        "total_sales": 0.0,
        "total_users": 0,
        "total_menu_items": 0,
    }
    config_error = supabase_config_error()
    if config_error:
        return empty_stats, config_error

    orders, order_error = fetch_orders()
    if order_error:
        return empty_stats, order_error

    total_sales = 0.0
    for order in orders:
        try:
            total_sales += float(order.get("total_amount") or 0)
        except (TypeError, ValueError):
            continue

    partial_stats = {
        "total_orders": len(orders),
        "total_sales": total_sales,
        "total_users": 0,
        "total_menu_items": 0,
    }

    supabase_url, _ = current_supabase_config()
    try:
        users_response = requests.get(
            f"{supabase_url}/rest/v1/app_users",
            headers=supabase_headers(),
            params={"select": "id"},
            timeout=REQUEST_TIMEOUT,
        )
        menu_response = requests.get(
            f"{supabase_url}/rest/v1/menu_items",
            headers=supabase_headers(),
            params={"select": "id"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return partial_stats, "Unable to load some dashboard data from Supabase right now."

    if users_response.status_code >= 400:
        return partial_stats, parse_response_error(users_response)

    try:
        users = users_response.json()
    except ValueError:
        return partial_stats, "Unable to read admin user data from Supabase."

    partial_stats["total_users"] = len(users) if isinstance(users, list) else 0

    if menu_response.status_code >= 400:
        return partial_stats, parse_response_error(menu_response)

    try:
        menu_items = menu_response.json()
    except ValueError:
        return partial_stats, "Unable to read admin menu data from Supabase."

    partial_stats["total_menu_items"] = len(menu_items) if isinstance(menu_items, list) else 0
    return partial_stats, None


def fetch_admin_menu_items() -> tuple[list[dict[str, Any]], str | None]:
    config_error = supabase_config_error()
    if config_error:
        return [], config_error

    supabase_url, _ = current_supabase_config()
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/menu_items",
            headers=supabase_headers(),
            params={"select": "*", "order": "id.asc"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return [], "Unable to load menu items right now."

    if response.status_code >= 400:
        return [], parse_response_error(response)

    try:
        rows = response.json()
    except ValueError:
        return [], "Unable to read menu items right now."
    return rows if isinstance(rows, list) else [], None


def create_admin_menu_item(
    name: str,
    description: str,
    category: str,
    price: float,
    image: str,
) -> tuple[bool, str]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error

    supabase_url, _ = current_supabase_config()
    payload = {
        "name": name.strip(),
        "description": description.strip(),
        "category": category.strip(),
        "price": price,
        "image": image.strip() or "plogo.png",
    }
    try:
        response = requests.post(
            f"{supabase_url}/rest/v1/menu_items",
            headers=supabase_headers("return=minimal"),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to add menu item right now."

    if response.status_code >= 400:
        return False, parse_response_error(response)
    return True, "Menu item added successfully."


def update_admin_menu_item(
    item_id: int,
    name: str,
    description: str,
    category: str,
    price: float,
    image: str,
) -> tuple[bool, str]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error

    supabase_url, _ = current_supabase_config()
    payload = {
        "name": name.strip(),
        "description": description.strip(),
        "category": category.strip(),
        "price": price,
        "image": image.strip() or "plogo.png",
    }
    try:
        response = requests.patch(
            f"{supabase_url}/rest/v1/menu_items",
            headers=supabase_headers("return=minimal"),
            params={"id": f"eq.{item_id}"},
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to update menu item right now."

    if response.status_code >= 400:
        return False, parse_response_error(response)
    return True, "Menu item updated successfully."


def delete_admin_menu_item(item_id: int) -> tuple[bool, str]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error

    supabase_url, _ = current_supabase_config()
    try:
        response = requests.delete(
            f"{supabase_url}/rest/v1/menu_items",
            headers=supabase_headers("return=minimal"),
            params={"id": f"eq.{item_id}"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to delete menu item right now."

    if response.status_code >= 400:
        return False, parse_response_error(response)
    return True, "Menu item deleted successfully."


def fetch_admin_users() -> tuple[list[dict[str, Any]], str | None]:
    config_error = supabase_config_error()
    if config_error:
        return [], config_error

    supabase_url, _ = current_supabase_config()
    params = {"select": "id,email,full_name,phone_number,created_at", "order": "created_at.desc"}
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/app_users",
            headers=supabase_headers(),
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return [], "Unable to load users right now."

    if response.status_code >= 400:
        error_message = parse_response_error(response)
        if is_schema_cache_column_error(error_message, "phone_number"):
            try:
                fallback_response = requests.get(
                    f"{supabase_url}/rest/v1/app_users",
                    headers=supabase_headers(),
                    params={"select": "id,email,full_name,created_at", "order": "created_at.desc"},
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.RequestException:
                return [], "Unable to load users right now."

            if fallback_response.status_code >= 400:
                return [], parse_response_error(fallback_response)

            rows = fallback_response.json()
            normalized = []
            for row in rows:
                row["phone_number"] = ""
                normalized.append(row)
            return normalized, None
        return [], error_message

    rows = response.json()
    for row in rows:
        row.setdefault("phone_number", "")
    return rows, None


def update_admin_user(user_id: str, full_name: str, phone_number: str) -> tuple[bool, str]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error

    supabase_url, _ = current_supabase_config()
    payload = {
        "full_name": full_name.strip() or None,
        "phone_number": phone_number.strip() or None,
    }
    try:
        response = requests.patch(
            f"{supabase_url}/rest/v1/app_users",
            headers=supabase_headers("return=minimal"),
            params={"id": f"eq.{user_id}"},
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to update user right now."

    if response.status_code >= 400:
        error_message = parse_response_error(response)
        if is_schema_cache_column_error(error_message, "phone_number"):
            fallback_payload = {"full_name": full_name.strip() or None}
            try:
                fallback_response = requests.patch(
                    f"{supabase_url}/rest/v1/app_users",
                    headers=supabase_headers("return=minimal"),
                    params={"id": f"eq.{user_id}"},
                    json=fallback_payload,
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.RequestException:
                return False, "Unable to update user right now."

            if fallback_response.status_code >= 400:
                return False, parse_response_error(fallback_response)
            return True, "User updated successfully (phone number column not available)."
        return False, error_message

    return True, "User updated successfully."


def delete_admin_user(user_id: str) -> tuple[bool, str]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error

    supabase_url, _ = current_supabase_config()
    try:
        response = requests.delete(
            f"{supabase_url}/rest/v1/app_users",
            headers=supabase_headers("return=minimal"),
            params={"id": f"eq.{user_id}"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to delete user right now."

    if response.status_code >= 400:
        return False, parse_response_error(response)
    return True, "User deleted successfully."


def admin_update_order_status(order_id: int, status: str) -> tuple[bool, str]:
    if status not in {"Pending", "Preparing", "Completed"}:
        return False, "Please choose a valid status."
    return update_order_status(order_id, status)


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


def create_order(
    customer_name: str,
    cart: list[dict[str, Any]],
    total_amount: float,
    payment_method: str,
    order_type: str,
) -> tuple[bool, str]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error
    if order_type not in {"Dine-in", "Take-out"}:
        return False, "Please choose dine-in or take-out."
    if payment_method not in {"Cash", "GCash", "Card"}:
        return False, "Please choose a valid payment method."
    if not cart:
        return False, "Add menu items before placing an order."

    if order_type == "Dine-in":
        table_number, table_error = get_next_table_number()
        if table_error:
            return False, f"Unable to generate table number: {table_error}"
        service_label = f"Table {table_number}"
    else:
        service_label = "Take-out"

    supabase_url, _ = current_supabase_config()
    payload = {
        "customer_name": customer_name,
        "table_number": service_label,
        "items": cart,
        "total_amount": total_amount,
        "payment_method": payment_method,
        "order_type": order_type,
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
        error_message = parse_response_error(response)
        if is_schema_cache_column_error(error_message, "payment_method"):
            return False, schema_cache_fix_message("orders.payment_method")
        if is_schema_cache_column_error(error_message, "order_type"):
            fallback_payload = dict(payload)
            fallback_payload.pop("order_type", None)
            try:
                fallback_response = requests.post(
                    f"{supabase_url}/rest/v1/orders",
                    headers=supabase_headers("return=minimal"),
                    json=fallback_payload,
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.RequestException:
                return False, "Unable to save the order right now."

            if fallback_response.status_code >= 400:
                return False, parse_response_error(fallback_response)

            if order_type == "Dine-in":
                return True, f"Order submitted successfully. Your table number is {service_label}."
            return True, "Take-out order submitted successfully. Please wait while your food is being prepared."
        return False, error_message

    if order_type == "Dine-in":
        return True, f"Order submitted successfully. Your table number is {service_label}."
    return True, "Take-out order submitted successfully. Please wait while your food is being prepared."


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
