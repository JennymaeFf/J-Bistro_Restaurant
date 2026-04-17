import os
import sys
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

load_env_file()

from supabase_client import (
    authenticate_user,
    current_supabase_config,
    create_order,
    detect_key_type,
    delete_order,
    fetch_menu_items,
    fetch_orders,
    fetch_user_profile,
    register_user,
    update_order_status,
    update_user_profile,
    valid_email_message,
)

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "jbistro-school-project-secret-key")

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


def get_cart() -> list[dict[str, Any]]:
    cart = session.get("cart")
    if isinstance(cart, list):
        return cart
    session["cart"] = []
    return session["cart"]


def cart_total(cart: list[dict[str, Any]]) -> float:
    return sum(float(item["price"]) * int(item["quantity"]) for item in cart)


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
                "phone_number": profile.get("phone_number") or "",
            }
        )
        session["user"] = user
        session.modified = True
    return current_user_profile(), message


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


@app.context_processor
def inject_layout_data() -> dict[str, Any]:
    cart = get_cart()
    return {
        "cart_count": sum(int(item["quantity"]) for item in cart),
        "current_user": session.get("user"),
        "is_logged_in": is_logged_in(),
        "get_cart": get_cart,
        "cart_total": cart_total,
    }



@app.route("/")
def index():
    return redirect(url_for("home"))


@app.route("/home")
def home():
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
        customer_phone = user.get("phone_number", "")
        payment_method = request.form.get("payment_method", "").strip()

        if not payment_method:
            flash("Payment method is required.", "error")
            return redirect(url_for("order"))
        if not customer_name:
            flash("Please complete your profile name before placing an order.", "error")
            return redirect(url_for("profile"))
        if not cart:
            flash("Add menu items before placing an order.", "error")
            return redirect(url_for("menu"))

        success, message = create_order(customer_name, cart, cart_total(cart), payment_method, customer_phone)
        flash(message, "success" if success else "error")
        if success:
            # Extract table number from the message
            table_number = "N/A"
            if "Your table number is" in message:
                try:
                    table_number = message.split("Your table number is ")[1].split(".")[0]
                    table_number = f"Table {table_number}"
                except:
                    table_number = "N/A"
            
            session["last_receipt"] = {
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "table_number": table_number,
                "items": [dict(item) for item in cart],
                "total_amount": cart_total(cart),
                "payment_method": payment_method,
            }
            session["cart"] = []
            session.modified = True
            return redirect(url_for("receipt"))

    return render_template("order.html", cart=cart, total_amount=cart_total(cart), user=user)


@app.route("/receipt")
@login_required_for_order
def receipt():
    receipt_data = session.get("last_receipt")
    if not receipt_data:
        flash("No recent receipt found. Please place an order first.", "error")
        return redirect(url_for("menu"))

    return render_template("receipt.html", receipt=receipt_data)


@app.route("/dashboard")
def dashboard():
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
    if is_logged_in():
        return redirect(url_for("home"))

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
            session["user"] = user_session
            session.modified = True
            return redirect(pop_valid_next_url())

    return render_template("login.html", auth_page=True)


@app.route("/register", methods=["GET", "POST"])
def register():
    if is_logged_in():
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

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

        success, message = register_user(email, password)
        flash(message, "success" if success else "error")
        if success:
            flash("Registration complete. Please log in to continue ordering.", "success")
            return redirect(url_for("login"))

    return render_template("register.html", auth_page=True)


@app.route("/logout")
def logout():
    session.pop("user", None)
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
        phone_number = request.form.get("phone_number", "").strip()
        success, message, profile_data = update_user_profile(user.get("id"), full_name, phone_number)
        flash(message, "success" if success else "error")
        if success and profile_data:
            user.update(
                {
                    "full_name": profile_data.get("full_name", full_name),
                    "phone_number": profile_data.get("phone_number", phone_number),
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
