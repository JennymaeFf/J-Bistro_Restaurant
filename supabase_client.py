import json
import os
import re
import time
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


def current_supabase_service_config() -> tuple[str, str]:
    url = normalize_env_value(os.environ.get("SUPABASE_URL"), "")
    service_key = normalize_env_value(os.environ.get("SUPABASE_SERVICE_ROLE_KEY"), "")
    return url, service_key


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


def jwt_expiration_timestamp(token: str) -> int | None:
    payload = decode_jwt_payload(token)
    if not payload:
        return None
    try:
        return int(payload.get("exp"))
    except (TypeError, ValueError):
        return None


def token_is_expired(token: str, leeway_seconds: int = 60) -> bool:
    exp = jwt_expiration_timestamp(token)
    if exp is None:
        return True
    return exp <= int(time.time()) + leeway_seconds


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


def user_auth_headers(access_token: str) -> dict[str, str]:
    _, supabase_api_key = current_supabase_config()
    return {
        "apikey": supabase_api_key,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def supabase_service_config_error() -> str | None:
    supabase_url, service_key = current_supabase_service_config()
    if supabase_url in PLACEHOLDER_VALUES:
        return "SUPABASE_URL is missing or still using a placeholder value."
    if not service_key:
        return (
            "SUPABASE_SERVICE_ROLE_KEY is missing. Add the full service_role key to your server "
            "environment variables, then restart or redeploy the app."
        )
    if "..." in service_key or len(service_key) < 80:
        return (
            "SUPABASE_SERVICE_ROLE_KEY looks truncated or too short. Paste the full service_role key "
            "from Supabase API settings into the server environment. If this is deployed on Vercel, "
            "update the Vercel Environment Variables and redeploy; editing local .env will not change "
            "the deployed app."
        )
    key_type = detect_key_type(service_key)
    if key_type != "service_role":
        return (
            f"SUPABASE_SERVICE_ROLE_KEY must be the service_role key. Detected key type: {key_type}. "
            "Do not use the anon key for this variable."
        )
    return None


def storage_upload_headers(content_type: str) -> dict[str, str]:
    _, service_key = current_supabase_service_config()
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": content_type,
        "x-upsert": "true",
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


def update_user_profile_image(user_id: str, profile_image: str) -> tuple[bool, str, dict[str, Any] | None]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error, None

    if not user_id:
        return False, "Please log in first.", None

    supabase_url, _ = current_supabase_config()
    try:
        response = requests.patch(
            f"{supabase_url}/rest/v1/app_users",
            headers=supabase_headers("return=representation"),
            params={"id": f"eq.{user_id}"},
            json={"profile_image": profile_image.strip() or None},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to update profile picture right now.", None

    if response.status_code >= 400:
        error_message = parse_response_error(response)
        if is_schema_cache_column_error(error_message, "profile_image") or "profile_image" in error_message.lower():
            return False, schema_cache_fix_message("app_users.profile_image"), None
        return False, error_message, None

    try:
        rows = response.json()
    except ValueError:
        rows = []
    profile = rows[0] if rows else {"id": user_id, "profile_image": profile_image}
    return True, "Profile picture updated successfully.", profile


def upload_profile_image_to_storage(
    owner_id: str,
    filename: str,
    content_type: str,
    image_bytes: bytes,
) -> tuple[bool, str, str | None]:
    config_error = supabase_service_config_error()
    if config_error:
        return False, config_error, None
    if not owner_id:
        return False, "Please log in first.", None
    if not image_bytes:
        return False, "The uploaded image is empty.", None

    bucket = os.environ.get("SUPABASE_PROFILE_BUCKET", "profile-images").strip() or "profile-images"
    object_path = f"{owner_id}/{filename}"
    supabase_url, _ = current_supabase_service_config()
    try:
        response = requests.post(
            f"{supabase_url}/storage/v1/object/{bucket}/{object_path}",
            headers=storage_upload_headers(content_type),
            data=image_bytes,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to upload profile picture to Supabase Storage right now.", None

    if response.status_code >= 400:
        error_message = parse_response_error(response)
        return False, (
            f"Supabase Storage upload failed: {error_message}. "
            f"Make sure the '{bucket}' bucket exists and SUPABASE_SERVICE_ROLE_KEY is configured server-side."
        ), None

    public_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{object_path}"
    return True, "Profile picture uploaded successfully.", public_url


def update_admin_account_profile(
    user_id: str,
    access_token: str,
    full_name: str,
    email: str,
    phone_number: str,
) -> tuple[bool, str, dict[str, Any] | None]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error, None

    full_name = full_name.strip()
    email = email.strip().lower()
    phone_number = phone_number.strip()
    if not full_name:
        return False, "Full name is required.", None
    email_error = valid_email_message(email)
    if email_error:
        return False, email_error, None

    supabase_url, _ = current_supabase_config()
    profile_payload = {
        "full_name": full_name,
        "email": email,
        "phone_number": phone_number or None,
    }
    try:
        profile_response = requests.patch(
            f"{supabase_url}/rest/v1/app_users",
            headers=supabase_headers("return=representation"),
            params={"id": f"eq.{user_id}"},
            json=profile_payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to update admin profile right now.", None

    if profile_response.status_code >= 400:
        error_message = parse_response_error(profile_response)
        if is_schema_cache_column_error(error_message, "full_name", "phone_number"):
            return False, schema_cache_fix_message("app_users.full_name", "app_users.phone_number"), None
        return False, error_message, None

    try:
        rows = profile_response.json()
    except ValueError:
        rows = []

    profile = rows[0] if rows else {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "phone_number": phone_number,
    }

    if access_token:
        try:
            auth_response = requests.put(
                f"{supabase_url}/auth/v1/user",
                headers=user_auth_headers(access_token),
                json={"email": email},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException:
            return False, "Profile saved, but the auth email could not be updated right now.", None

        if auth_response.status_code >= 400:
            auth_error = parse_response_error(auth_response)
            if "expired" in auth_error.lower() or "jwt" in auth_error.lower():
                return True, (
                    "Profile saved. To change your sign-in email, please log out, log in again, "
                    "then update the email while your session is fresh."
                ), profile
            return True, f"Profile saved, but auth email update failed: {auth_error}", profile

    return True, "Admin profile updated successfully.", profile


def update_admin_password(access_token: str, password: str) -> tuple[bool, str]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error
    if not access_token:
        return False, "Please log in again before changing your password."

    password = password.strip()
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."

    supabase_url, _ = current_supabase_config()
    try:
        response = requests.put(
            f"{supabase_url}/auth/v1/user",
            headers=user_auth_headers(access_token),
            json={"password": password},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to update password right now."

    if response.status_code >= 400:
        return False, parse_response_error(response)
    return True, "Password updated successfully."


def refresh_auth_session(refresh_token: str) -> tuple[bool, str, dict[str, Any] | None]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error, None
    if not refresh_token:
        return False, "Your session expired. Please log in again and try uploading your profile photo.", None

    supabase_url, _ = current_supabase_config()
    try:
        response = requests.post(
            f"{supabase_url}/auth/v1/token?grant_type=refresh_token",
            headers=auth_headers(),
            json={"refresh_token": refresh_token},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to refresh your session right now. Please log in again.", None

    if response.status_code >= 400:
        return False, "Your session expired. Please log in again and try uploading your profile photo.", None

    payload = response.json()
    return True, "Session refreshed.", {
        "access_token": payload.get("access_token"),
        "refresh_token": payload.get("refresh_token") or refresh_token,
        "expires_in": payload.get("expires_in"),
        "expires_at": payload.get("expires_at"),
    }


def send_password_reset(email: str) -> tuple[bool, str]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error

    email = email.strip().lower()
    email_error = valid_email_message(email)
    if email_error:
        return False, email_error

    supabase_url, _ = current_supabase_config()
    try:
        response = requests.post(
            f"{supabase_url}/auth/v1/recover",
            headers=auth_headers(),
            json={"email": email},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return False, "Unable to send the password reset email right now."

    if response.status_code >= 400:
        return False, parse_response_error(response)
    return True, "If this email is registered, Supabase will send a password reset link."


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
        error_message = parse_response_error(response)
        if "invalid login credentials" in error_message.lower():
            return (
                False,
                "Invalid email or password. Make sure this account exists in Supabase Authentication and the password is correct.",
                None,
            )
        return False, error_message, None

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
        "refresh_token": payload.get("refresh_token"),
        "expires_in": payload.get("expires_in"),
        "expires_at": payload.get("expires_at"),
        "full_name": profile.get("full_name") or default_full_name(user_data.get("email", email)),
        "role": user_role,
        "phone_number": profile.get("phone_number") or "",
        "profile_image": profile.get("profile_image") or "",
    }
    return True, "Login successful.", user_session


def normalize_menu_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(item)
    normalized["is_available"] = item.get("is_available") is not False
    normalized["image"] = item.get("image") or "plogo.png"
    return normalized


def fetch_menu_items() -> tuple[list[dict[str, Any]], str | None]:
    config_error = supabase_config_error()
    if config_error:
        return [normalize_menu_item(item) for item in SAMPLE_MENU_ITEMS], config_error

    supabase_url, _ = current_supabase_config()
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/menu_items",
            headers=supabase_headers(),
            params={"select": "*", "order": "id.asc"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return [normalize_menu_item(item) for item in SAMPLE_MENU_ITEMS], "Unable to load menu items from Supabase right now."

    if response.status_code >= 400:
        return [normalize_menu_item(item) for item in SAMPLE_MENU_ITEMS], parse_response_error(response)

    try:
        rows = response.json()
    except ValueError:
        return [normalize_menu_item(item) for item in SAMPLE_MENU_ITEMS], "Unable to read menu items from Supabase."

    if not isinstance(rows, list):
        return [], None
    return [normalize_menu_item(item) for item in rows], None


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
        normalize_order_record(order)
    return orders, None


def format_order_number(order_number: Any) -> str:
    try:
        number = int(order_number)
    except (TypeError, ValueError):
        return "Order #---"
    if number <= 0:
        return "Order #---"
    return f"Order #{number:03d}"


def extract_order_number(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    match = re.search(r"\d+", str(value))
    if not match:
        return None
    try:
        number = int(match.group(0))
    except ValueError:
        return None
    return number if number > 0 else None


def normalize_order_record(order: dict[str, Any]) -> dict[str, Any]:
    if isinstance(order.get("items"), str):
        try:
            order["items"] = json.loads(order["items"])
        except json.JSONDecodeError:
            order["items"] = []
    elif not isinstance(order.get("items"), list):
        order["items"] = []

    order_number = extract_order_number(order.get("order_number"))
    if order_number is None:
        table_label = str(order.get("table_number") or "")
        if table_label.lower().startswith("order"):
            order_number = extract_order_number(table_label)
    if order_number is None:
        order_number = extract_order_number(order.get("id"))

    order["order_number"] = order_number
    order["order_number_label"] = format_order_number(order_number)
    order.setdefault("payment_bank", "")
    order.setdefault("payment_reference", "")
    return order


def fetch_latest_order(customer_name: str | None = None) -> tuple[dict[str, Any] | None, str | None]:
    config_error = supabase_config_error()
    if config_error:
        return None, config_error

    supabase_url, _ = current_supabase_config()
    select_variants = [
        "id,customer_name,order_number,order_type,table_number,items,total_amount,payment_method,payment_bank,payment_reference,status,created_at",
        "id,customer_name,order_number,order_type,table_number,items,total_amount,payment_method,payment_reference,status,created_at",
        "id,customer_name,order_type,table_number,items,total_amount,payment_method,status,created_at",
    ]
    last_error = None
    response = None

    for select_clause in select_variants:
        params = {
            "select": select_clause,
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

        if response.status_code < 400:
            break

        last_error = parse_response_error(response)
        if not any(column in last_error.lower() for column in ("order_number", "payment_bank", "payment_reference")):
            return None, last_error
    else:
        return None, last_error or "Unable to load the latest order right now."

    try:
        rows = response.json()
    except ValueError:
        return None, "Unable to read latest order data from Supabase."

    if not rows:
        return None, None

    latest_order = normalize_order_record(rows[0])
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
    return [normalize_menu_item(item) for item in rows] if isinstance(rows, list) else [], None


def create_admin_menu_item(
    name: str,
    description: str,
    category: str,
    price: float,
    image: str,
    is_available: bool = True,
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
        "is_available": is_available,
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
    is_available: bool = True,
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
        "is_available": is_available,
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
    select_variants = [
        ("id,email,full_name,phone_number,created_at,role", "created_at.desc", None),
        ("id,email,full_name,created_at,role", "created_at.desc", "phone_number"),
        ("id,email,phone_number,created_at,role", "created_at.desc", "full_name"),
        ("id,email,created_at,role", "created_at.desc", "full_name and phone_number"),
        ("id,email,full_name,phone_number,role", None, "created_at"),
        ("id,email,full_name,role", None, "phone_number and created_at"),
        ("id,email,phone_number,role", None, "full_name and created_at"),
        ("id,email,role", None, "full_name, phone_number, and created_at"),
        ("id,email", None, "full_name, phone_number, created_at, and role"),
    ]
    last_error = None
    missing_columns_note = None

    for select_clause, order_clause, missing_note in select_variants:
        params = {"select": select_clause}
        if order_clause:
            params["order"] = order_clause
        try:
            response = requests.get(
                f"{supabase_url}/rest/v1/app_users",
                headers=supabase_headers(),
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException:
            return [], "Unable to load users right now."

        if response.status_code < 400:
            try:
                rows = response.json()
            except ValueError:
                return [], "Unable to read users right now."
            missing_columns_note = missing_note
            break

        last_error = parse_response_error(response)
        if not any(column in last_error.lower() for column in ("full_name", "phone_number", "created_at", "role")):
            return [], last_error
    else:
        return [], last_error or "Unable to load users right now."

    if not isinstance(rows, list):
        return [], "Unable to read users right now."

    for row in rows:
        row.setdefault("email", "")
        if not str(row.get("full_name") or "").strip():
            row["full_name"] = default_full_name(row.get("email", ""))
        if not str(row.get("phone_number") or "").strip():
            row["phone_number"] = ""
        if not str(row.get("role") or "").strip():
            row["role"] = "user"

    if missing_columns_note:
        return rows, (
            f"Loaded users, but app_users is missing or has not refreshed: {missing_columns_note}. "
            "Run the latest supabase_schema.sql in Supabase SQL Editor, then run NOTIFY pgrst, 'reload schema'."
        )
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
        if is_schema_cache_column_error(error_message, "full_name", "phone_number") or any(
            column in error_message.lower() for column in ("full_name", "phone_number")
        ):
            fallback_payload = {}
            if "full_name" not in error_message.lower():
                fallback_payload["full_name"] = full_name.strip() or None
            if "phone_number" not in error_message.lower():
                fallback_payload["phone_number"] = phone_number.strip() or None
            if not fallback_payload:
                return False, schema_cache_fix_message("app_users.full_name", "app_users.phone_number")
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
            return True, "User updated successfully. Some optional profile columns are not available yet."
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


def get_next_order_number() -> tuple[int, str | None]:
    """Get the next visible order number based on existing orders."""
    orders, error = fetch_orders()
    if error:
        return 0, error

    max_order_number = 0
    for order in orders:
        for value in (order.get("order_number"), order.get("table_number"), order.get("id")):
            number = extract_order_number(value)
            if number is not None:
                max_order_number = max(max_order_number, number)

    return max_order_number + 1, None


def create_order(
    customer_name: str,
    cart: list[dict[str, Any]],
    total_amount: float,
    payment_method: str,
    order_type: str,
    payment_bank: str = "",
    payment_reference: str = "",
) -> tuple[bool, str]:
    config_error = supabase_config_error()
    if config_error:
        return False, config_error
    if order_type not in {"Dine-in", "Take-out"}:
        return False, "Please choose dine-in or take-out."
    if payment_method not in {"Cash", "GCash", "Card"}:
        return False, "Please choose a valid payment method."
    payment_bank = payment_bank.strip()
    payment_reference = payment_reference.strip()
    if payment_method == "GCash" and not payment_reference:
        return False, "Please enter your GCash transaction reference number."
    if payment_method == "Card":
        if payment_bank not in {"Landbank", "BDO", "BPI"}:
            return False, "Please choose a bank for card or bank payment."
        if not payment_reference:
            return False, "Please enter your bank transaction reference number."
    if not cart:
        return False, "Add menu items before placing an order."

    order_number, order_number_error = get_next_order_number()
    if order_number_error:
        return False, f"Unable to generate order number: {order_number_error}"
    order_number_label = format_order_number(order_number)

    supabase_url, _ = current_supabase_config()
    payload = {
        "customer_name": customer_name,
        "order_number": order_number,
        # Keep table_number as a legacy display field until all old deployments
        # and database rows have moved fully to order_number.
        "table_number": order_number_label,
        "items": cart,
        "total_amount": total_amount,
        "payment_method": payment_method,
        "payment_bank": payment_bank or None,
        "payment_reference": payment_reference or None,
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
        if is_schema_cache_column_error(error_message, "order_number") or "order_number" in error_message.lower():
            fallback_payload = dict(payload)
            fallback_payload.pop("order_number", None)
            fallback_payload.pop("payment_bank", None)
            fallback_payload.pop("payment_reference", None)
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

            return True, f"Order submitted successfully. Your order number is {order_number_label}."
        if any(column in error_message.lower() for column in ("payment_bank", "payment_reference")):
            fallback_payload = dict(payload)
            fallback_payload.pop("payment_bank", None)
            fallback_payload.pop("payment_reference", None)
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

            return True, (
                f"Order submitted successfully. Your order number is {order_number_label}. "
                "Payment reference could not be saved until the database schema is refreshed."
            )
        if is_schema_cache_column_error(error_message, "payment_method"):
            return False, schema_cache_fix_message("orders.payment_method")
        if is_schema_cache_column_error(error_message, "order_type"):
            fallback_payload = dict(payload)
            fallback_payload.pop("order_type", None)
            fallback_payload.pop("payment_bank", None)
            fallback_payload.pop("payment_reference", None)
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

            return True, f"Order submitted successfully. Your order number is {order_number_label}."
        return False, error_message

    return True, f"Order submitted successfully. Your order number is {order_number_label}."


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
