import os
import sys
import hmac
from uuid import uuid4
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
    admin_update_order_status,
    authenticate_user,
    create_admin_menu_item,
    current_supabase_config,
    create_order,
    delete_admin_menu_item,
    delete_admin_user,
    detect_key_type,
    delete_order,
    fetch_admin_dashboard_stats,
    fetch_admin_menu_items,
    fetch_admin_users,
    fetch_menu_items,
    fetch_latest_order,
    fetch_orders,
    fetch_user_profile,
    register_user,
    update_admin_account_profile,
    update_admin_password,
    update_admin_menu_item,
    update_admin_user,
    update_order_status,
    upload_profile_image_to_storage,
    update_user_profile,
    update_user_profile_image,
    valid_email_message,
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

# SESSION COOKIE SETTINGS - Vercel uses HTTPS, local dev usually uses HTTP.
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("VERCEL") == "1"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"] = "jbistro_session"

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
        return normalized if normalized in {"admin", "user"} else "user"

    user = session.get("user") or {}
    inferred = user.get("role")
    if isinstance(inferred, str) and inferred.strip():
        normalized = inferred.strip().lower()
        if normalized not in {"admin", "user"}:
            normalized = "user"
        session["role"] = normalized
        session.modified = True
        return normalized
    return "user"


def redirect_for_role(role: str):
    normalized_role = role.strip().lower() if isinstance(role, str) else "user"
    if normalized_role == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("dashboard"))


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


def build_receipt_payload(source: Any, fallback_customer_name: str = "Customer") -> dict[str, Any]:
    data = source if isinstance(source, dict) else {}
    customer_name = (data.get("customer_name") or fallback_customer_name or "Customer").strip()
    order_type = (data.get("order_type") or "Dine-in").strip()
    if order_type not in {"Dine-in", "Take-out"}:
        order_type = "Dine-in"
    table_number = data.get("table_number")
    if not table_number:
        table_number = "Take-out" if order_type == "Take-out" else "N/A"
    payment_method = (data.get("payment_method") or "Cash").strip() or "Cash"
    items = normalize_receipt_items(data.get("items"))

    total_amount = coerce_float(data.get("total_amount"), 0.0)
    if total_amount <= 0 and items:
        total_amount = sum(item["price"] * item["quantity"] for item in items)

    return {
        "id": data.get("id"),
        "customer_name": customer_name,
        "order_type": order_type,
        "table_number": table_number,
        "payment_method": payment_method,
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
    menu_items, _ = fetch_menu_items()
    # Select some popular items as best sellers
    best_sellers = menu_items[:6]  # First 6 items as best sellers
    return render_template("home.html", best_sellers=best_sellers)


@app.route("/best-sellers")
def best_sellers():
    return redirect(url_for("home", _anchor="best-sellers"))


@app.route("/menu")
def menu():
    category = request.args.get('category')
    menu_items, message = fetch_menu_items()
    if category:
        # Filter items by category
        menu_items = [item for item in menu_items if item.get('category', '').lower() == category.lower()]
    return render_template("menu.html", menu_items=menu_items, info_message=message, selected_category=category)


@app.route("/cart/add/<int:item_id>", methods=["POST"])
@login_required_for_order
def add_to_cart(item_id: int):
    menu_items, _ = fetch_menu_items()
    selected_item = next((item for item in menu_items if int(item["id"]) == item_id), None)
    if not selected_item:
        flash("Menu item not found.", "error")
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
    return redirect(url_for("order"))


@app.route("/order", methods=["GET", "POST"])
@login_required_for_order
def order():
    cart = get_cart()
    user, profile_message = refresh_session_profile()
    if profile_message:
        flash(profile_message, "error")
    if request.method == "POST":
        customer_name = user.get("full_name") or fallback_full_name(user.get("email", ""))
        order_type = request.form.get("order_type", "").strip()
        payment_method = request.form.get("payment_method", "").strip()

        app.logger.info(
            "Submitting order: order_type=%s payment_method=%s cart_items=%s",
            order_type or "missing",
            payment_method or "missing",
            len(cart),
        )

        if order_type not in {"Dine-in", "Take-out"}:
            flash("Please choose dine-in or take-out.", "error")
            return redirect(url_for("order"))
        if payment_method not in {"Cash", "GCash", "Card"}:
            flash("Please choose a valid payment method.", "error")
            return redirect(url_for("order"))
        if not customer_name:
            flash("Please complete your profile name before placing an order.", "error")
            return redirect(url_for("profile"))
        if not cart:
            flash("Add menu items before placing an order.", "error")
            return redirect(url_for("menu"))

        try:
            success, message = create_order(customer_name, cart, cart_total(cart), payment_method, order_type)
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
                service_label = "Take-out" if order_type == "Take-out" else "N/A"
                if "Your table number is" in message:
                    try:
                        service_label = message.split("Your table number is ")[1].split(".")[0]
                    except IndexError:
                        service_label = "N/A"
                receipt_payload = build_receipt_payload(
                    {
                        "customer_name": customer_name,
                        "order_type": order_type,
                        "table_number": service_label,
                        "items": [dict(item) for item in cart],
                        "total_amount": cart_total(cart),
                        "payment_method": payment_method,
                    },
                    customer_name,
                )

            session["last_receipt"] = receipt_payload
            session["cart"] = []
            session.modified = True
            return redirect(url_for("receipt"))

    return render_template("order.html", cart=cart, total_amount=cart_total(cart), user=user)


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
def dashboard():
    if current_session_role() == "admin":
        return redirect(url_for("admin_dashboard"))
    orders, message = fetch_orders()
    return render_template("dashboard.html", orders=orders, info_message=message)


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
    return render_template(
        "admin/orders.html",
        orders=orders,
        info_message=info_message,
        admin_section="orders",
    )


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def admin_orders_update_status(order_id: int):
    status = request.form.get("status", "").strip()
    success, message = admin_update_order_status(order_id, status)
    flash(message, "success" if success else "error")
    return redirect(url_for("admin_orders"))


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
            if not name.strip() or not description.strip() or not category.strip() or price <= 0:
                flash("Name, description, category, and a valid price are required.", "error")
                return redirect(url_for("admin_menu"))
            success, message = create_admin_menu_item(name, description, category, price, image)
            flash(message, "success" if success else "error")
            return redirect(url_for("admin_menu"))

        if action == "update":
            item_id = coerce_int(request.form.get("item_id"), 0)
            name = request.form.get("name", "")
            description = request.form.get("description", "")
            category = request.form.get("category", "")
            image = request.form.get("image", "")
            price = coerce_float(request.form.get("price"), 0.0)
            if item_id <= 0:
                flash("Invalid menu item id.", "error")
                return redirect(url_for("admin_menu"))
            if not name.strip() or not description.strip() or not category.strip() or price <= 0:
                flash("Name, description, category, and a valid price are required.", "error")
                return redirect(url_for("admin_menu"))
            success, message = update_admin_menu_item(item_id, name, description, category, price, image)
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
            success, message, profile_data = update_admin_account_profile(
                user.get("id", ""),
                user.get("access_token", ""),
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
    key_type = detect_key_type(supabase_api_key) if supabase_api_key else "missing"
    masked_key = ""
    if supabase_api_key:
        masked_key = f"{supabase_api_key[:10]}...{supabase_api_key[-6:]}"

    return {
        "supabase_url": supabase_url,
        "supabase_url_has_spaces": supabase_url != supabase_url.strip(),
        "supabase_api_key_present": bool(supabase_api_key),
        "supabase_api_key_length": len(supabase_api_key),
        "supabase_api_key_type": key_type,
        "supabase_api_key_has_spaces": supabase_api_key != supabase_api_key.strip(),
        "supabase_api_key_preview": masked_key,
        "using_placeholder_url": "your-project" in supabase_url,
        "using_placeholder_key": "your-supabase" in supabase_api_key,
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET" and is_logged_in():
        return redirect_for_role(current_session_role())

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        email_message = valid_email_message(email) if email else "Please enter both email and password."

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return redirect(url_for("login"))
        if email_message:
            flash(email_message, "error")
            return redirect(url_for("login"))

        success, message, user_session = authenticate_user(email, password)
        flash(message, "success" if success else "error")
        if success:
            if user_session is None:
                flash("Login successful, but the app could not load your session details.", "error")
                return redirect(url_for("login"))
            # Replace any previous session identity (e.g., switching user -> admin).
            session.pop("user", None)
            session.pop("role", None)
            session.pop("user_email", None)
            user_role = str((user_session or {}).get("role", "user")).strip().lower()
            if user_role not in {"admin", "user"}:
                user_role = "user"
            user_session["role"] = user_role
            session["user"] = user_session
            session["role"] = user_role
            session["user_email"] = (user_session.get("email") or email).strip().lower()
            session.modified = True
            return redirect_for_role(user_role)

    return render_template("login.html", auth_page=True)


@app.route("/register", methods=["GET", "POST"])
def register():
    if is_logged_in():
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        admin_code = request.form.get("admin_code", "").strip()
        configured_admin_code = os.environ.get("ADMIN_REGISTRATION_CODE", "").strip()

        if not email or not password:
            flash("Please fill in all registration fields.", "error")
            return redirect(url_for("register"))

        email_message = valid_email_message(email)
        if email_message:
            flash(email_message, "error")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return redirect(url_for("register"))

        target_role = "user"
        if admin_code:
            if configured_admin_code and hmac.compare_digest(admin_code, configured_admin_code):
                target_role = "admin"
            else:
                flash("Admin code not recognized. Account will be created as a user.", "error")

        success, message = register_user(email, password, role=target_role)
        flash(message, "success" if success else "error")
        if success:
            if target_role == "admin":
                flash("Admin account created. Please log in.", "success")
            else:
                flash("Registration complete. Please log in to continue ordering.", "success")
            return redirect(url_for("login"))

    return render_template("register.html", auth_page=True)


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
        success, message, profile_data = update_user_profile(user.get("id"), full_name)
        flash(message, "success" if success else "error")
        if success and profile_data:
            user.update(
                {
                    "full_name": profile_data.get("full_name", full_name),
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
    app.run(debug=True)
