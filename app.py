import os
import sys
import hmac
import re
import time
from uuid import uuid4
from datetime import timedelta
from functools import wraps
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

CURRENT_DIR = Path(__file__).resolve().parent
LOCAL_SITE_PACKAGES = CURRENT_DIR / ".venv" / "Lib" / "site-packages"

if LOCAL_SITE_PACKAGES.exists():
    sys.path.insert(0, str(LOCAL_SITE_PACKAGES))

from flask import Flask, flash, redirect, render_template, request, session, url_for
from env_loader import load_env_file
from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.utils import secure_filename

load_env_file()

from supabase_client import (
    authenticate_user,
    create_employee,
    create_admin_menu_item,
    create_rider,
    current_supabase_config,
    current_supabase_service_config,
    create_order,
    delete_employee,
    delete_admin_menu_item,
    delete_admin_user,
    delete_rider,
    detect_key_type,
    delete_order,
    fetch_admin_dashboard_stats,
    fetch_employees,
    fetch_admin_menu_items,
    fetch_admin_users,
    fetch_inventory_items,
    fetch_menu_items,
    fetch_latest_order,
    fetch_orders,
    fetch_riders,
    fetch_user_profile,
    register_user,
    resend_verification_email,
    check_email_verification_status,
    send_password_reset,
    update_order_tracking,
    update_employee,
    update_rider,
    update_admin_account_profile,
    update_admin_password,
    update_admin_menu_item,
    update_admin_user,
    update_inventory_item,
    update_order_status,
    upload_profile_image_to_storage,
    update_user_profile,
    update_user_profile_image,
    valid_email_message,
    verification_rate_limit_message,
    verification_required_message,
)

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "jbistro-school-project-secret-key")
UPLOAD_DIR = CURRENT_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_PROFILE_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
GCASH_PAYMENT_NUMBER = "0917 123 4567"
BANK_PAYMENT_ACCOUNTS = {
    "Landbank": {
        "account_name": "J'Bistro Restaurant",
        "account_number": "1234-5678-9012",
    },
    "BDO": {
        "account_name": "J'Bistro Restaurant",
        "account_number": "0088-1234-5678",
    },
    "BPI": {
        "account_name": "J'Bistro Restaurant",
        "account_number": "0921-4567-8901",
    },
}
ORDER_STATUS_OPTIONS = ("Pending", "Preparing", "Completed")
PAYMENT_STATUS_OPTIONS = ("Pending", "Paid", "COD")
DELIVERY_STATUS_OPTIONS = ("Waiting", "Assigned", "On the way", "Delivered")
DELIVERY_OPTION_VALUES = ("Pickup", "Delivery")
EMPLOYEE_ATTENDANCE_OPTIONS = ("On Duty", "Off Duty", "Absent")
EMPLOYEE_STATUS_OPTIONS = ("Active", "Inactive")

# SESSION COOKIE SETTINGS - Vercel uses HTTPS, local dev usually uses HTTP.
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("VERCEL") == "1"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"] = "jbistro_session"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)

# Wrap app with WhiteNoise for production static file serving
try:
    from whitenoise import WhiteNoise
    app.wsgi_app = WhiteNoise(app.wsgi_app, root=str(CURRENT_DIR / "static"), prefix="/static/")
except ImportError:
    pass  # WhiteNoise not installed, Flask will handle static files

def is_logged_in() -> bool:
    return bool(session.get("user"))


def current_session_role() -> str:
    role = session.get("role")
    if isinstance(role, str) and role.strip():
        normalized = role.strip().lower()
        if normalized == "user":
            normalized = "customer"
        return normalized if normalized in {"admin", "customer", "staff"} else "customer"

    user = session.get("user") or {}
    inferred = user.get("role")
    if isinstance(inferred, str) and inferred.strip():
        normalized = inferred.strip().lower()
        if normalized == "user":
            normalized = "customer"
        if normalized not in {"admin", "customer", "staff"}:
            normalized = "customer"
        session["role"] = normalized
        session.modified = True
        return normalized
    return "customer"


def redirect_for_role(role: str):
    normalized_role = role.strip().lower() if isinstance(role, str) else "customer"
    if normalized_role == "user":
        normalized_role = "customer"
    if normalized_role == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("home"))


def destination_for_role(role: str) -> str:
    normalized_role = role.strip().lower() if isinstance(role, str) else "customer"
    if normalized_role == "user":
        normalized_role = "customer"
    if normalized_role == "admin":
        return url_for("admin_dashboard")
    return url_for("home")


def start_verification_cooldown(seconds: int = 60) -> None:
    session["verification_resend_sent_at"] = time.time()
    session["verification_resend_cooldown"] = seconds
    session.modified = True


def current_verification_cooldown_seconds() -> int:
    cooldown_seconds = int(session.get("verification_resend_cooldown") or 60)
    last_sent_at = float(session.get("verification_resend_sent_at") or 0)
    seconds_since_last_send = time.time() - last_sent_at
    if seconds_since_last_send >= cooldown_seconds:
        return 0
    return max(0, int(cooldown_seconds - seconds_since_last_send))


def store_authenticated_session(user_session: dict[str, Any], fallback_email: str = "") -> str:
    existing_cart = list(session.get("cart") or [])
    session.clear()
    user_role = str((user_session or {}).get("role", "customer")).strip().lower()
    if user_role == "user":
        user_role = "customer"
    if user_role not in {"admin", "customer", "staff"}:
        user_role = "customer"
    user_session["role"] = user_role
    session["user"] = user_session
    session["role"] = user_role
    session["user_email"] = (user_session.get("email") or fallback_email).strip().lower()
    if existing_cart:
        session["cart"] = existing_cart
    session.permanent = True
    session.modified = True
    return user_role


def get_cart() -> list[dict[str, Any]]:
    cart = session.get("cart")
    if isinstance(cart, list):
        return cart
    session["cart"] = []
    return session["cart"]


def cart_total(cart: list[dict[str, Any]]) -> float:
    return sum(float(item["price"]) * int(item["quantity"]) for item in cart)


def coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def coerce_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "available"}


def normalize_category_slug(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def category_matches(item_category: Any, selected_category: str) -> bool:
    return normalize_category_slug(item_category) == normalize_category_slug(selected_category)


def normalize_receipt_items(raw_items: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []

    normalized_items: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        quantity = max(1, coerce_int(item.get("quantity"), 1))
        normalized_items.append(
            {
                "name": item.get("display_name") or item.get("name") or "Menu Item",
                "quantity": quantity,
                "price": max(0.0, coerce_float(item.get("price"), 0.0)),
            }
        )
    return normalized_items


def format_receipt_order_number(value: Any) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        match = re.search(r"\d+", str(value or ""))
        if not match:
            return "Order #---"
        number = int(match.group(0))
    if number <= 0:
        return "Order #---"
    return f"Order #{number:03d}"


def receipt_order_number_label(data: dict[str, Any]) -> str:
    if data.get("order_number_label"):
        return str(data["order_number_label"])
    if data.get("order_number"):
        return format_receipt_order_number(data.get("order_number"))
    table_label = str(data.get("table_number") or "")
    if table_label.lower().startswith("order"):
        return table_label
    if data.get("id"):
        return format_receipt_order_number(data.get("id"))
    return "Order #---"


def build_receipt_payload(source: Any, fallback_customer_name: str = "Customer") -> dict[str, Any]:
    data = source if isinstance(source, dict) else {}
    customer_name = (data.get("customer_name") or fallback_customer_name or "Customer").strip()
    delivery_option = (data.get("delivery_option") or data.get("order_type") or "Delivery").strip().title()
    if delivery_option not in DELIVERY_OPTION_VALUES:
        delivery_option = "Delivery"
    order_type = delivery_option
    order_number_label = receipt_order_number_label(data)
    payment_method = (data.get("payment_method") or "Cash").strip() or "Cash"
    payment_status = (data.get("payment_status") or "Pending").strip() or "Pending"
    payment_bank = (data.get("payment_bank") or "").strip()
    payment_reference = (data.get("payment_reference") or "").strip()
    delivery_address = (data.get("delivery_address") or "").strip()
    preferred_time = (data.get("preferred_time") or "").strip()
    delivery_notes = (data.get("delivery_notes") or "").strip()
    delivery_status = (data.get("delivery_status") or "Waiting").strip() or "Waiting"
    rider_name = (data.get("rider_name") or "").strip()
    rider_phone = (data.get("rider_phone") or "").strip()
    rider_status = (data.get("rider_status") or "").strip()
    items = normalize_receipt_items(data.get("items"))

    total_amount = coerce_float(data.get("total_amount"), 0.0)
    if total_amount <= 0 and items:
        total_amount = sum(item["price"] * item["quantity"] for item in items)

    return {
        "id": data.get("id"),
        "customer_name": customer_name,
        "order_number": data.get("order_number"),
        "order_number_label": order_number_label,
        "order_type": order_type,
        "delivery_option": delivery_option,
        "preferred_time": preferred_time,
        "payment_method": payment_method,
        "payment_status": payment_status,
        "payment_bank": payment_bank,
        "payment_reference": payment_reference,
        "delivery_address": delivery_address,
        "delivery_notes": delivery_notes,
        "delivery_status": delivery_status,
        "rider_name": rider_name,
        "rider_phone": rider_phone,
        "rider_status": rider_status,
        "items": items,
        "total_amount": max(0.0, total_amount),
        "status": data.get("status") or "Pending",
        "created_at": data.get("created_at"),
    }


def target_allows_get(target: str) -> bool:
    if not target.startswith("/") or target.startswith("//"):
        return False

    path = urlsplit(target).path or "/"
    url_adapter = app.url_map.bind_to_environ(request.environ)
    try:
        url_adapter.match(path, method="GET")
    except (MethodNotAllowed, NotFound):
        return False
    return True


def next_url_for_auth_redirect() -> str:
    if request.method == "GET":
        return request.full_path if request.query_string else request.path
    if request.endpoint == "order":
        return url_for("order")
    if request.endpoint == "remove_from_cart":
        return url_for("cart")
    return url_for("menu")


def pop_valid_next_url(default_endpoint: str = "home") -> str:
    next_url = session.pop("next_url", None)
    if isinstance(next_url, str) and target_allows_get(next_url):
        return next_url
    return url_for(default_endpoint)


def fallback_full_name(email: str) -> str:
    username = email.split("@")[0] if email else "Customer"
    return username.replace(".", " ").replace("_", " ").title()


def current_user_profile() -> dict[str, Any]:
    user = session.get("user") or {}
    email = user.get("email", "")
    return {
        "id": user.get("id"),
        "email": email,
        "full_name": user.get("full_name") or fallback_full_name(email),
        "phone_number": user.get("phone_number") or "",
        "delivery_address": user.get("delivery_address") or "",
        "role": user.get("role") or current_session_role(),
        "profile_image": user.get("profile_image") or "",
    }


def refresh_session_profile() -> tuple[dict[str, Any], str | None]:
    user = session.get("user") or {}
    user_id = user.get("id")
    if not user_id:
        return current_user_profile(), "Please log in first."

    profile, message = fetch_user_profile(user_id, user.get("email", ""))
    if profile:
        fallback_profile = current_user_profile()
        user.update(
            {
                "email": profile.get("email") or user.get("email"),
                "full_name": profile.get("full_name") or fallback_profile["full_name"],
                "phone_number": profile.get("phone_number") or fallback_profile.get("phone_number", ""),
                "delivery_address": profile.get("delivery_address") or fallback_profile.get("delivery_address", ""),
                "role": profile.get("role") or user.get("role") or current_session_role(),
                "profile_image": profile.get("profile_image") or fallback_profile.get("profile_image", ""),
            }
        )
        session["user"] = user
        session.modified = True
    return current_user_profile(), message


def profile_image_url(profile: dict[str, Any] | None) -> str:
    image_path = ((profile or {}).get("profile_image") or "").strip()
    if image_path:
        if image_path.startswith(("http://", "https://")):
            return image_path
        return url_for("static", filename=image_path)
    return url_for("static", filename="images/plogo.png")


def is_allowed_profile_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PROFILE_IMAGE_EXTENSIONS


def profile_image_content_type(extension: str) -> str:
    return "image/png" if extension == "png" else "image/jpeg"


def safe_upload_redirect(next_target: str = ""):
    if next_target and target_allows_get(next_target):
        return redirect(next_target)
    if current_session_role() == "admin":
        return redirect(url_for("admin_settings"))
    return redirect(url_for("profile"))


def attach_riders_to_orders(orders: list[dict[str, Any]], riders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rider_map: dict[str, dict[str, Any]] = {}
    for rider in riders:
        rider_id = str(rider.get("id") or "").strip()
        if rider_id:
            rider_map[rider_id] = rider

    for order in orders:
        rider_id = str(order.get("rider_id") or "").strip()
        rider_data = rider_map.get(rider_id, {})
        order["rider"] = rider_data
        order["rider_name"] = rider_data.get("name") or "Not assigned"
        order["rider_phone"] = rider_data.get("phone") or ""
        order["rider_status"] = rider_data.get("status") or ""
    return orders


def redirect_to_register_for_order() -> Any:
    session["next_url"] = next_url_for_auth_redirect()
    session.modified = True
    flash("Please log in first before adding items to the cart or placing an order.", "error")
    return redirect(url_for("login"))


def login_required_for_order(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not is_logged_in():
            return redirect_to_register_for_order()
        return view_function(*args, **kwargs)

    return wrapped_view


def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not is_logged_in():
            session["next_url"] = next_url_for_auth_redirect()
            session.modified = True
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)

    return wrapped_view


def is_admin_logged_in() -> bool:
    return current_session_role() == "admin"


def admin_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not is_admin_logged_in():
            if is_logged_in():
                flash("Admin access required for that page.", "error")
                return redirect(url_for("home"))
            flash("Please log in with an admin account.", "error")
            session["next_url"] = request.path
            session.modified = True
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)

    return wrapped_view


@app.context_processor
def inject_layout_data() -> dict[str, Any]:
    cart = get_cart()
    current_user = session.get("user")
    return {
        "cart_count": sum(int(item["quantity"]) for item in cart),
        "current_user": current_user,
        "current_user_image_url": profile_image_url(current_user),
        "is_logged_in": is_logged_in(),
        "is_admin_logged_in": is_admin_logged_in(),
        "get_cart": get_cart,
        "cart_total": cart_total,
        "profile_image_url": profile_image_url,
    }



@app.route("/")
def index():
    return redirect(url_for("home"))


@app.route("/home")
def home():
    if current_session_role() == "admin":
        return redirect(url_for("admin_dashboard"))
    selected_category = normalize_category_slug(request.args.get("category", ""))
    try:
        menu_items, menu_message = fetch_menu_items()
    except Exception:
        app.logger.exception("Failed to load menu items for home page.")
        menu_items = []
        menu_message = "Unable to load featured menu items right now."
    seen_categories: list[str] = []
    for item in menu_items:
        category = str(item.get("category") or "").strip()
        category_slug = normalize_category_slug(category)
        if category_slug in {"snack", "snacks"}:
            continue
        if category and category not in seen_categories:
            seen_categories.append(category)
    filtered_menu_items = menu_items
    if selected_category:
        filtered_menu_items = [
            item for item in menu_items if category_matches(item.get("category", ""), selected_category)
        ]
    return render_template(
        "home.html",
        menu_items=filtered_menu_items,
        best_sellers=menu_items[:3],
        categories=seen_categories,
        selected_category=selected_category,
        info_message=menu_message,
    )


@app.route("/best-sellers")
def best_sellers():
    return redirect(url_for("home", _anchor="best-sellers"))


@app.route("/menu")
def menu():
    category = normalize_category_slug(request.args.get("category", ""))
    menu_items, message = fetch_menu_items()
    if category:
        # Filter items by category
        menu_items = [item for item in menu_items if category_matches(item.get("category", ""), category)]
    return render_template("menu.html", menu_items=menu_items, info_message=message, selected_category=category)


@app.route("/cart/add/<int:item_id>", methods=["POST"])
@login_required_for_order
def add_to_cart(item_id: int):
    menu_items, _ = fetch_menu_items()
    selected_item = next((item for item in menu_items if int(item["id"]) == item_id), None)
    if not selected_item:
        flash("Menu item not found.", "error")
        return redirect(url_for("menu"))
    if selected_item.get("is_available") is False:
        flash(f"{selected_item.get('name', 'This item')} is currently out of stock.", "warning")
        return redirect(url_for("menu"))

    quantity = int(request.form.get("quantity", 1))
    size = request.form.get("size")
    price = float(request.form.get("price", selected_item["price"]))
    
    cart = get_cart()
    # Create a unique key for cart items with size
    item_key = f"{item_id}_{size}" if size else str(item_id)
    
    existing = next((item for item in cart if item.get("item_key") == item_key), None)
    if existing:
        existing["quantity"] += quantity
        item_name = existing.get("display_name", selected_item["name"])
    else:
        cart_item = {
            "id": int(selected_item["id"]),
            "name": selected_item["name"],
            "price": price,
            "image": selected_item.get("image", "plogo.png"),
            "quantity": quantity,
            "item_key": item_key,
        }
        if size:
            cart_item["size"] = size
            cart_item["display_name"] = f"{selected_item['name']} ({size.capitalize()})"
        else:
            cart_item["display_name"] = selected_item["name"]
        cart.append(cart_item)
        item_name = cart_item.get("display_name", selected_item["name"])

    session["cart"] = cart
    session.modified = True
    flash(f"{item_name} added to cart.", "success")
    return redirect(url_for("menu"))


@app.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required_for_order
def remove_from_cart(item_id: int):
    item_key = request.form.get("item_key", str(item_id))
    session["cart"] = [item for item in get_cart() if item.get("item_key", str(item["id"])) != item_key]
    session.modified = True
    flash("Item removed from cart.", "success")
    return redirect(url_for("cart"))


@app.route("/cart/update/<int:item_id>", methods=["POST"])
@login_required_for_order
def update_cart_quantity(item_id: int):
    item_key = request.form.get("item_key", str(item_id))
    delta = coerce_int(request.form.get("delta"), 0)
    if delta == 0:
        return redirect(url_for("cart"))

    cart = get_cart()
    target_item = next((item for item in cart if item.get("item_key", str(item["id"])) == item_key), None)
    if not target_item:
        flash("Cart item not found.", "error")
        return redirect(url_for("cart"))

    if delta > 0:
        menu_items, _ = fetch_menu_items()
        selected_item = next((item for item in menu_items if int(item["id"]) == item_id), None)
        if not selected_item or selected_item.get("is_available") is False:
            flash(f"{target_item.get('display_name', 'This item')} is currently out of stock.", "warning")
            return redirect(url_for("cart"))
        stock_quantity = coerce_int(selected_item.get("stock_quantity"), 0)
        current_quantity = coerce_int(target_item.get("quantity"), 1)
        if stock_quantity > 0 and current_quantity >= stock_quantity:
            flash(f"Only {stock_quantity} of {selected_item.get('name', 'this item')} is available right now.", "warning")
            return redirect(url_for("cart"))

    new_quantity = max(0, coerce_int(target_item.get("quantity"), 1) + delta)
    if new_quantity <= 0:
        session["cart"] = [item for item in cart if item.get("item_key", str(item["id"])) != item_key]
        flash("Item removed from cart.", "success")
    else:
        target_item["quantity"] = new_quantity
        session["cart"] = cart
        session.modified = True
    session.modified = True
    return redirect(url_for("cart"))


@app.route("/order", methods=["GET", "POST"])
@login_required_for_order
def order():
    cart = get_cart()
    user, profile_message = refresh_session_profile()
    if profile_message:
        flash(profile_message, "error")
    if request.method == "POST":
        customer_name = user.get("full_name") or fallback_full_name(user.get("email", ""))
        delivery_option = request.form.get("delivery_option", "Delivery").strip().title()
        delivery_address = request.form.get("delivery_address", "").strip()
        preferred_time = request.form.get("preferred_time", "").strip()
        delivery_notes = request.form.get("delivery_notes", "").strip()
        payment_method = request.form.get("payment_method", "").strip()
        payment_bank = request.form.get("payment_bank", "").strip()
        payment_reference = request.form.get("payment_reference", "").strip()

        app.logger.info(
            "Submitting order: payment_method=%s cart_items=%s",
            payment_method or "missing",
            len(cart),
        )

        if delivery_option not in DELIVERY_OPTION_VALUES:
            flash("Please choose Pickup or Delivery.", "error")
            return redirect(url_for("order"))
        if delivery_option == "Delivery" and not delivery_address:
            flash("Please enter a delivery address.", "error")
            return redirect(url_for("order"))
        if payment_method not in {"Cash", "GCash", "Card"}:
            flash("Please choose a valid payment method.", "error")
            return redirect(url_for("order"))
        if payment_method == "GCash" and not payment_reference:
            flash("Please enter your GCash transaction reference number.", "error")
            return redirect(url_for("order"))
        if payment_method == "Card":
            if payment_bank not in BANK_PAYMENT_ACCOUNTS:
                flash("Please choose a bank for card or bank payment.", "error")
                return redirect(url_for("order"))
            if not payment_reference:
                flash("Please enter your bank transaction reference number.", "error")
                return redirect(url_for("order"))
        if not customer_name:
            flash("Please complete your profile name before placing an order.", "error")
            return redirect(url_for("profile"))
        if not cart:
            flash("Add menu items before placing an order.", "error")
            return redirect(url_for("menu"))

        try:
            success, message = create_order(
                customer_name,
                cart,
                cart_total(cart),
                delivery_option,
                delivery_address,
                preferred_time,
                delivery_notes,
                payment_method,
                payment_bank,
                payment_reference,
            )
        except Exception:
            app.logger.exception("Unexpected error while placing an order.")
            flash("Something went wrong while placing your order. Please try again.", "error")
            return redirect(url_for("order"))

        flash(message, "success" if success else "error")
        if success:
            latest_order, latest_order_error = fetch_latest_order(customer_name)
            if latest_order_error:
                app.logger.warning("Failed to load latest order for receipt: %s", latest_order_error)

            if latest_order:
                receipt_payload = build_receipt_payload(latest_order, customer_name)
            else:
                order_number_label = "Order #---"
                if "Your order number is" in message:
                    try:
                        order_number_label = message.split("Your order number is ")[1].split(".")[0]
                    except IndexError:
                        order_number_label = "Order #---"
                receipt_payload = build_receipt_payload(
                    {
                        "customer_name": customer_name,
                        "order_type": delivery_option,
                        "delivery_option": delivery_option,
                        "order_number_label": order_number_label,
                        "items": [dict(item) for item in cart],
                        "total_amount": cart_total(cart),
                        "delivery_address": delivery_address,
                        "preferred_time": preferred_time,
                        "delivery_notes": delivery_notes,
                        "payment_method": payment_method,
                        "payment_status": "Pending",
                        "payment_bank": payment_bank,
                        "payment_reference": payment_reference,
                        "delivery_status": "Waiting",
                    },
                    customer_name,
                )

            session["last_receipt"] = receipt_payload
            session["cart"] = []
            session.modified = True
            return redirect(url_for("receipt"))

    return render_template(
        "order.html",
        cart=cart,
        total_amount=cart_total(cart),
        user=user,
        gcash_payment_number=GCASH_PAYMENT_NUMBER,
        bank_payment_accounts=BANK_PAYMENT_ACCOUNTS,
    )


@app.route("/receipt")
@login_required_for_order
def receipt():
    user_profile = current_user_profile()
    fallback_name = user_profile.get("full_name") or fallback_full_name(user_profile.get("email", ""))
    session_receipt = build_receipt_payload(session.get("last_receipt"), fallback_name)

    if session_receipt.get("items"):
        return render_template("receipt.html", receipt=session_receipt)

    latest_order, latest_order_error = fetch_latest_order(fallback_name)
    if latest_order_error:
        app.logger.warning("Failed to fetch latest order on receipt page: %s", latest_order_error)
    if latest_order:
        receipt_data = build_receipt_payload(latest_order, fallback_name)
        session["last_receipt"] = receipt_data
        session.modified = True
        return render_template("receipt.html", receipt=receipt_data)

    flash("No recent receipt found. Please place an order first.", "error")
    return redirect(url_for("menu"))


@app.route("/dashboard")
@login_required
def dashboard():
    current_role = current_session_role()
    if current_role == "admin":
        return redirect(url_for("admin_dashboard"))
    try:
        orders, message = fetch_orders()
    except Exception:
        app.logger.exception("Failed to load user dashboard orders.")
        orders = []
        message = "Unable to load your orders right now."

    riders, riders_message = fetch_riders()
    user_profile = current_user_profile()
    customer_name = user_profile.get("full_name") or fallback_full_name(user_profile.get("email", ""))
    user_orders = []
    for order in orders:
        if str(order.get("customer_name") or "").strip().lower() == customer_name.strip().lower():
            user_orders.append(order)
    user_orders = attach_riders_to_orders(user_orders, riders)
    if riders_message:
        if message:
            message = f"{message} {riders_message}"
        else:
            message = riders_message

    return render_template("dashboard.html", orders=user_orders, info_message=message)


@app.route("/dashboard/update/<int:order_id>", methods=["POST"])
@login_required
def dashboard_update(order_id: int):
    status = request.form.get("status", "").strip()
    if status not in {"Pending", "Preparing", "Completed", "Cancelled"}:
        flash("Please choose a valid order status.", "error")
        return redirect(url_for("dashboard"))

    success, message = update_order_status(order_id, status)
    flash(message, "success" if success else "error")
    return redirect(url_for("dashboard"))


@app.route("/dashboard/delete/<int:order_id>", methods=["POST"])
@login_required
def dashboard_delete(order_id: int):
    success, message = delete_order(order_id)
    flash(message, "success" if success else "error")
    return redirect(url_for("dashboard"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    return redirect(url_for("login"))


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    session.modified = True
    flash("Admin logged out.", "success")
    return redirect(url_for("login"))


@app.route("/admin")
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    try:
        stats, info_message = fetch_admin_dashboard_stats()
    except Exception:
        app.logger.exception("Unexpected error while loading admin dashboard.")
        stats = {
            "total_orders": 0,
            "total_sales": 0.0,
            "total_users": 0,
            "total_menu_items": 0,
        }
        info_message = "Unable to load dashboard data right now."
    return render_template(
        "admin/admin_dashboard.html",
        stats=stats,
        info_message=info_message,
        admin_section="dashboard",
    )


@app.route("/admin/orders")
@admin_required
def admin_orders():
    orders, info_message = fetch_orders()
    riders, riders_message = fetch_riders()
    orders = attach_riders_to_orders(orders, riders)
    if riders_message:
        if info_message:
            info_message = f"{info_message} {riders_message}"
        else:
            info_message = riders_message
    return render_template(
        "admin/orders.html",
        orders=orders,
        riders=riders,
        order_status_options=ORDER_STATUS_OPTIONS,
        payment_status_options=PAYMENT_STATUS_OPTIONS,
        delivery_status_options=DELIVERY_STATUS_OPTIONS,
        info_message=info_message,
        admin_section="orders",
    )


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def admin_orders_update_status(order_id: int):
    status = request.form.get("status", "").strip()
    payment_status = request.form.get("payment_status", "").strip()
    delivery_status = request.form.get("delivery_status", "").strip()
    rider_id = request.form.get("rider_id", "").strip()
    success, message = update_order_tracking(
        order_id,
        status,
        payment_status,
        delivery_status,
        rider_id,
    )
    flash(message, "success" if success else "error")
    return redirect(url_for("admin_orders"))


@app.route("/admin/inventory", methods=["GET", "POST"])
@admin_required
def admin_inventory():
    if request.method == "POST":
        item_id = coerce_int(request.form.get("item_id"), 0)
        stock_quantity = coerce_int(request.form.get("stock_quantity"), 0)
        low_stock_threshold = coerce_int(request.form.get("low_stock_threshold"), 5)
        success, message = update_inventory_item(item_id, stock_quantity, low_stock_threshold)
        flash(message, "success" if success else "error")
        return redirect(url_for("admin_inventory"))

    inventory_items, info_message = fetch_inventory_items()
    return render_template(
        "admin/inventory.html",
        inventory_items=inventory_items,
        info_message=info_message,
        admin_section="inventory",
    )


@app.route("/admin/riders", methods=["GET", "POST"])
@admin_required
def admin_riders():
    if request.method == "POST":
        action = request.form.get("action", "").strip()
        rider_id = request.form.get("rider_id", "").strip()
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        status = request.form.get("status", "Available").strip()

        if action == "create":
            success, message = create_rider(name, phone, status)
            flash(message, "success" if success else "error")
            return redirect(url_for("admin_riders"))

        if action == "update":
            success, message = update_rider(rider_id, name, phone, status)
            flash(message, "success" if success else "error")
            return redirect(url_for("admin_riders"))

        if action == "delete":
            success, message = delete_rider(rider_id)
            flash(message, "success" if success else "error")
            return redirect(url_for("admin_riders"))

        flash("Unknown rider action.", "error")
        return redirect(url_for("admin_riders"))

    riders, info_message = fetch_riders()
    return render_template(
        "admin/riders.html",
        riders=riders,
        rider_status_options=("Available", "Busy"),
        info_message=info_message,
        admin_section="riders",
    )


@app.route("/admin/employees", methods=["GET", "POST"])
@admin_required
def admin_employees():
    if request.method == "POST":
        action = request.form.get("action", "").strip()
        employee_id = request.form.get("employee_id", "").strip()
        name = request.form.get("name", "").strip()
        position = request.form.get("position", "").strip()
        contact_number = request.form.get("contact_number", "").strip()
        shift_schedule = request.form.get("shift_schedule", "").strip()
        attendance_status = request.form.get("attendance_status", "Off Duty").strip()
        employment_status = request.form.get("employment_status", "Active").strip()
        notes = request.form.get("notes", "").strip()
        task_assignment = request.form.get("task_assignment", "").strip()
        time_in = request.form.get("time_in", "").strip()
        time_out = request.form.get("time_out", "").strip()

        if action == "create":
            success, message = create_employee(
                name,
                position,
                contact_number,
                shift_schedule,
                attendance_status,
                employment_status,
                notes,
                task_assignment,
                time_in,
                time_out,
            )
            flash(message, "success" if success else "error")
            return redirect(url_for("admin_employees"))

        if action == "update":
            success, message = update_employee(
                employee_id,
                name,
                position,
                contact_number,
                shift_schedule,
                attendance_status,
                employment_status,
                notes,
                task_assignment,
                time_in,
                time_out,
            )
            flash(message, "success" if success else "error")
            return redirect(url_for("admin_employees"))

        if action == "delete":
            success, message = delete_employee(employee_id)
            flash(message, "success" if success else "error")
            return redirect(url_for("admin_employees"))

        flash("Unknown employee action.", "error")
        return redirect(url_for("admin_employees"))

    employees, info_message = fetch_employees()
    return render_template(
        "admin/employees.html",
        employees=employees,
        attendance_status_options=EMPLOYEE_ATTENDANCE_OPTIONS,
        employee_status_options=EMPLOYEE_STATUS_OPTIONS,
        info_message=info_message,
        admin_section="employees",
    )


@app.route("/admin/menu", methods=["GET", "POST"])
@admin_required
def admin_menu():
    if request.method == "POST":
        action = request.form.get("action", "").strip()
        if action == "create":
            name = request.form.get("name", "")
            description = request.form.get("description", "")
            category = request.form.get("category", "")
            image = request.form.get("image", "")
            price = coerce_float(request.form.get("price"), 0.0)
            is_available = coerce_bool(request.form.get("is_available"), True)
            if not name.strip() or not description.strip() or not category.strip() or price <= 0:
                flash("Name, description, category, and a valid price are required.", "error")
                return redirect(url_for("admin_menu"))
            success, message = create_admin_menu_item(
                name,
                description,
                category,
                price,
                image,
                is_available,
            )
            flash(message, "success" if success else "error")
            return redirect(url_for("admin_menu"))

        if action == "update":
            item_id = coerce_int(request.form.get("item_id"), 0)
            name = request.form.get("name", "")
            description = request.form.get("description", "")
            category = request.form.get("category", "")
            image = request.form.get("image", "")
            price = coerce_float(request.form.get("price"), 0.0)
            is_available = coerce_bool(request.form.get("is_available"), True)
            if item_id <= 0:
                flash("Invalid menu item id.", "error")
                return redirect(url_for("admin_menu"))
            if not name.strip() or not description.strip() or not category.strip() or price <= 0:
                flash("Name, description, category, and a valid price are required.", "error")
                return redirect(url_for("admin_menu"))
            success, message = update_admin_menu_item(
                item_id,
                name,
                description,
                category,
                price,
                image,
                is_available,
            )
            flash(message, "success" if success else "error")
            return redirect(url_for("admin_menu"))

        if action == "delete":
            item_id = coerce_int(request.form.get("item_id"), 0)
            if item_id <= 0:
                flash("Invalid menu item id.", "error")
                return redirect(url_for("admin_menu"))
            success, message = delete_admin_menu_item(item_id)
            flash(message, "success" if success else "error")
            return redirect(url_for("admin_menu"))

        flash("Unknown menu action.", "error")
        return redirect(url_for("admin_menu"))

    menu_items, info_message = fetch_admin_menu_items()
    return render_template(
        "admin/menu.html",
        menu_items=menu_items,
        info_message=info_message,
        admin_section="menu",
    )


@app.route("/admin/users", methods=["GET", "POST"])
@admin_required
def admin_users():
    if request.method == "POST":
        action = request.form.get("action", "").strip()
        user_id = request.form.get("user_id", "").strip()
        if not user_id:
            flash("User id is required.", "error")
            return redirect(url_for("admin_users"))

        if action == "update":
            full_name = request.form.get("full_name", "").strip()
            phone_number = request.form.get("phone_number", "").strip()
            success, message = update_admin_user(user_id, full_name, phone_number)
            flash(message, "success" if success else "error")
            return redirect(url_for("admin_users"))

        if action == "delete":
            success, message = delete_admin_user(user_id)
            flash(message, "success" if success else "error")
            return redirect(url_for("admin_users"))

        flash("Unknown user action.", "error")
        return redirect(url_for("admin_users"))

    users, info_message = fetch_admin_users()
    return render_template(
        "admin/users.html",
        users=users,
        info_message=info_message,
        admin_section="users",
    )


@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    user = session.get("user") or {}
    if request.method == "POST":
        action = request.form.get("action", "").strip()

        if action == "profile":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip()
            phone_number = request.form.get("phone_number", "").strip()
            current_email = (user.get("email") or "").strip().lower()
            requested_email = email.strip().lower()
            auth_update_token = user.get("access_token", "") if requested_email != current_email else ""
            success, message, profile_data = update_admin_account_profile(
                user.get("id", ""),
                auth_update_token,
                full_name,
                email,
                phone_number,
            )
            flash(message, "success" if success else "error")
            if success and profile_data:
                user.update(
                    {
                        "email": profile_data.get("email") or email,
                        "full_name": profile_data.get("full_name") or full_name,
                        "phone_number": profile_data.get("phone_number") or phone_number,
                        "role": profile_data.get("role") or user.get("role") or "admin",
                        "profile_image": profile_data.get("profile_image") or user.get("profile_image", ""),
                    }
                )
                session["user"] = user
                session["role"] = str(user.get("role", "admin")).strip().lower()
                session["user_email"] = (user.get("email") or email).strip().lower()
                session.modified = True
            return redirect(url_for("admin_settings"))

        if action == "password":
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")
            if password != confirm_password:
                flash("Passwords do not match.", "error")
                return redirect(url_for("admin_settings"))
            success, message = update_admin_password(user.get("access_token", ""), password)
            flash(message, "success" if success else "error")
            return redirect(url_for("admin_settings"))

        flash("Unknown settings action.", "error")
        return redirect(url_for("admin_settings"))

    profile_data, profile_message = refresh_session_profile()
    return render_template(
        "admin/settings.html",
        admin_section="settings",
        info_message=profile_message,
        profile=profile_data,
    )


@app.route("/upload-profile", methods=["GET", "POST"])
@login_required
def upload_profile():
    if request.method == "GET":
        flash("Please choose a profile picture from your profile or settings page.", "error")
        return safe_upload_redirect()

    user = session.get("user") or {}
    image_file = request.files.get("profile_image")
    next_target = request.form.get("next", "").strip()

    if not image_file or not image_file.filename:
        flash("Please choose an image to upload.", "error")
        return safe_upload_redirect(next_target)

    if not is_allowed_profile_image(image_file.filename):
        flash("Profile picture must be a JPG, JPEG, or PNG file.", "error")
        return safe_upload_redirect(next_target)

    original_name = secure_filename(image_file.filename)
    if not original_name:
        flash("The uploaded file name is not valid.", "error")
        return safe_upload_redirect(next_target)

    extension = original_name.rsplit(".", 1)[1].lower()
    owner_id = secure_filename(str(user.get("id") or "user"))
    filename = f"profile-{owner_id}-{uuid4().hex}.{extension}"
    content_type = profile_image_content_type(extension)

    if os.environ.get("PROFILE_UPLOAD_STORAGE", "supabase").strip().lower() == "local":
        upload_path = UPLOAD_DIR / filename
        try:
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            image_file.save(upload_path)
        except OSError:
            app.logger.exception("Unable to save uploaded profile picture to %s", upload_path)
            flash(
                "Unable to save the profile picture locally. Use Supabase Storage for deployed uploads.",
                "error",
            )
            return safe_upload_redirect(next_target)
        profile_image = f"uploads/{filename}"
    else:
        image_bytes = image_file.read()
        if len(image_bytes) > 5 * 1024 * 1024:
            flash("Profile picture must be 5 MB or smaller.", "error")
            return safe_upload_redirect(next_target)
        storage_success, storage_message, storage_url = upload_profile_image_to_storage(
            str(user.get("id") or ""),
            filename,
            content_type,
            image_bytes,
        )
        if not storage_success or not storage_url:
            app.logger.warning("Profile image storage upload failed for user_id=%s: %s", user.get("id"), storage_message)
            flash(storage_message, "error")
            return safe_upload_redirect(next_target)
        profile_image = storage_url

    success, message, profile_data = update_user_profile_image(user.get("id", ""), profile_image)
    flash(message, "success" if success else "error")
    if success:
        user["profile_image"] = (profile_data or {}).get("profile_image") or profile_image
        session["user"] = user
        session.modified = True
    elif not profile_image.startswith(("http://", "https://")):
        try:
            (UPLOAD_DIR / filename).unlink(missing_ok=True)
        except OSError:
            app.logger.warning("Could not remove unused uploaded profile picture: %s", UPLOAD_DIR / filename)

    return safe_upload_redirect(next_target)


@app.route("/debug/supabase-config")
def debug_supabase_config():
    supabase_url, supabase_api_key = current_supabase_config()
    _, supabase_service_key = current_supabase_service_config()
    key_type = detect_key_type(supabase_api_key) if supabase_api_key else "missing"
    service_key_type = detect_key_type(supabase_service_key) if supabase_service_key else "missing"
    masked_key = ""
    if supabase_api_key:
        masked_key = f"{supabase_api_key[:10]}...{supabase_api_key[-6:]}"
    masked_service_key = ""
    if supabase_service_key:
        masked_service_key = f"{supabase_service_key[:10]}...{supabase_service_key[-6:]}"

    return {
        "supabase_url": supabase_url,
        "supabase_url_has_spaces": supabase_url != supabase_url.strip(),
        "supabase_api_key_present": bool(supabase_api_key),
        "supabase_api_key_length": len(supabase_api_key),
        "supabase_api_key_type": key_type,
        "supabase_api_key_has_spaces": supabase_api_key != supabase_api_key.strip(),
        "supabase_api_key_preview": masked_key,
        "supabase_service_role_key_present": bool(supabase_service_key),
        "supabase_service_role_key_length": len(supabase_service_key),
        "supabase_service_role_key_type": service_key_type,
        "supabase_service_role_key_has_spaces": supabase_service_key != supabase_service_key.strip(),
        "supabase_service_role_key_preview": masked_service_key,
        "using_placeholder_url": "your-project" in supabase_url,
        "using_placeholder_key": "your-supabase" in supabase_api_key,
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET" and is_logged_in():
        return redirect_for_role(current_session_role())

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        email_message = valid_email_message(email) if email else "Please enter both email and password."

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return redirect(url_for("login"))
        if email_message:
            flash(email_message, "error")
            return redirect(url_for("login"))

        success, message, user_session = authenticate_user(email, password)
        if not success and message == verification_required_message():
            flash(message, "error")
            return render_template(
                "login.html",
                auth_page=True,
                show_resend_verification=True,
                verification_email=email,
            )

        flash(message, "success" if success else "error")
        if success:
            if user_session is None:
                flash("Login successful, but the app could not load your session details.", "error")
                return redirect(url_for("login"))
            user_role = store_authenticated_session(user_session, email)
            try:
                destination = destination_for_role(user_role)
            except Exception:
                app.logger.exception("Failed to build post-login destination for role %s.", user_role)
                destination = url_for("home")
            return redirect(destination)

    return render_template(
        "login.html",
        auth_page=True,
        show_resend_verification=False,
        verification_email="",
        login_email=session.pop("verified_email_hint", ""),
    )


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET" and is_logged_in():
        return redirect_for_role(current_session_role())

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Please enter your email address.", "error")
            return redirect(url_for("forgot_password"))

        success, message = send_password_reset(email)
        flash(message, "success" if success else "error")
        if success:
            return redirect(url_for("login"))
        return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html", auth_page=True)


@app.route("/resend-verification", methods=["POST"])
def resend_verification():
    email = request.form.get("email", "").strip().lower()
    if not email:
        flash("Enter your email address first so we can resend the verification link.", "error")
        return redirect(url_for("login"))

    email_message = valid_email_message(email)
    if email_message:
        flash(email_message, "error")
        return redirect(url_for("login"))

    seconds_left = current_verification_cooldown_seconds()
    if seconds_left > 0:
        cooldown_message = f"Please wait {seconds_left} seconds before requesting another verification link."
        flash(cooldown_message, "error")
        return redirect(url_for("login"))

    success, message = resend_verification_email(email)
    if success:
        start_verification_cooldown()
    elif message == verification_rate_limit_message():
        start_verification_cooldown()

    flash(message, "success" if success else "error")
    return redirect(url_for("login"))


@app.route("/verify-check", methods=["GET", "POST"])
def verify_check():
    email = request.values.get("email", "").strip().lower()
    if not email:
        flash("Enter an email address first.", "error")
        return redirect(url_for("login"))

    email_message = valid_email_message(email)
    if email_message:
        flash(email_message, "error")
        return redirect(url_for("login"))

    success, message, result = check_email_verification_status(email)
    if not success:
        flash(message, "error")
        return redirect(url_for("login"))

    if result and result.get("is_verified"):
        flash("Email is already verified. You can log in now.", "success")
    else:
        flash("Email is registered but not verified yet. Please check your inbox.", "error")
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if is_logged_in():
        return redirect(url_for("home"))

    # These values are passed back to the template whenever validation fails
    # so the user does not have to type everything again.
    form_data = {
        "full_name": "",
        "email": "",
        "phone_number": "",
        "address": "",
    }
    registration_success = False

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone_number = request.form.get("phone_number", "").strip()
        delivery_address = request.form.get("address", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        admin_code = request.form.get("admin_code", "").strip()
        configured_admin_code = os.environ.get("ADMIN_REGISTRATION_CODE", "").strip()
        form_data.update(
            {
                "full_name": full_name,
                "email": email,
                "phone_number": phone_number,
                "address": delivery_address,
            }
        )

        if not full_name or not email or not phone_number or not delivery_address or not password or not confirm_password:
            flash("Please fill in all registration fields.", "error")
            return render_template("register.html", auth_page=True, form_data=form_data)

        email_message = valid_email_message(email)
        if email_message:
            flash(email_message, "error")
            return render_template("register.html", auth_page=True, form_data=form_data)

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template("register.html", auth_page=True, form_data=form_data)

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html", auth_page=True, form_data=form_data)

        target_role = "customer"
        if admin_code:
            if configured_admin_code and hmac.compare_digest(admin_code, configured_admin_code):
                target_role = "admin"
            else:
                flash("Admin code not recognized. Account will be created as a customer.", "error")

        success, message = register_user(
            email,
            password,
            role=target_role,
            full_name=full_name,
            phone_number=phone_number,
            delivery_address=delivery_address,
        )
        if success:
            flash(message, "success")
            registration_success = True
            return render_template(
                "register.html",
                auth_page=True,
                form_data=form_data,
                registration_success=registration_success,
            )

        flash(message, "error")
        return render_template(
            "register.html",
            auth_page=True,
            form_data=form_data,
            registration_success=registration_success,
        )

    return render_template(
        "register.html",
        auth_page=True,
        form_data=form_data,
        registration_success=registration_success,
    )


@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("role", None)
    session.pop("user_email", None)
    session.pop("cart", None)
    session.pop("next_url", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/team")
def team():
    return render_template("team.html")


@app.route("/cart")
@login_required_for_order
def cart():
    cart_items = get_cart()
    total = cart_total(cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = session.get("user") or {}
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        delivery_address = request.form.get("delivery_address", "").strip()
        success, message, profile_data = update_user_profile(user.get("id"), full_name, delivery_address)
        flash(message, "success" if success else "error")
        if success and profile_data:
            user.update(
                {
                    "full_name": profile_data.get("full_name", full_name),
                    "delivery_address": profile_data.get("delivery_address", delivery_address),
                }
            )
            session["user"] = user
            session.modified = True
            return redirect(url_for("profile"))

    profile_data, profile_message = refresh_session_profile()
    if profile_message:
        flash(profile_message, "error")
    return render_template("profile.html", profile=profile_data)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
