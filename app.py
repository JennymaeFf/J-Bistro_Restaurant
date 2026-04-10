import json
import os
from typing import Any

import requests
from flask import Flask, flash, redirect, render_template, request, session, url_for

app = Flask(__name__)

# Secret key is needed by Flask to keep cart data inside the session.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "jbistro-school-project-secret-key")

# Supabase project settings.
# These values can be replaced with environment variables later when deploying.
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://fvfvgqpeawafwyczpfbd.supabase.co",
)
SUPABASE_PUBLISHABLE_KEY = os.environ.get(
    "SUPABASE_PUBLISHABLE_KEY",
    "sb_publishable_smjBZes-7hchOjbX6cptSQ_RLGhfS9l",
)
SUPABASE_API_KEY = os.environ.get(
    "SUPABASE_API_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ2ZnZncXBlYXdhZnd5Y3pwZmJkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3OTI1NTYsImV4cCI6MjA5MTM2ODU1Nn0.SVlC6-W7ZMOpFnb5wgRYqW7cvXrTLGw4tocZm1SNdPk",
)

# Sample menu is used if the Supabase table has not been created yet.
SAMPLE_MENU = [
    {
        "id": 1,
        "name": "Cheeseburger",
        "description": "Juicy beef burger with melted cheese and fresh vegetables.",
        "category": "Main Course",
        "price": 60.0,
        "image": "cheeseburger.png",
    },
    {
        "id": 2,
        "name": "Cheese Sandwich",
        "description": "Toasted sandwich filled with cheese and a creamy spread.",
        "category": "Snack",
        "price": 50.0,
        "image": "cheesesandwich.png",
    },
    {
        "id": 3,
        "name": "Chicken Burger",
        "description": "Crispy chicken burger served with a soft toasted bun.",
        "category": "Main Course",
        "price": 60.0,
        "image": "chickenburger.png",
    },
    {
        "id": 4,
        "name": "Spicy Chicken",
        "description": "Flavorful chicken meal for customers who like some heat.",
        "category": "Main Course",
        "price": 99.0,
        "image": "spicychicken.png",
    },
    {
        "id": 5,
        "name": "Beef Steak",
        "description": "Classic beef steak cooked with a rich savory taste.",
        "category": "Main Course",
        "price": 99.0,
        "image": "beefsteak.png",
    },
    {
        "id": 6,
        "name": "Salmon Fillet",
        "description": "Tender salmon fillet with a clean and premium flavor.",
        "category": "Main Course",
        "price": 99.0,
        "image": "salmonfillet.png",
    },
]


def get_cart() -> list[dict[str, Any]]:
    """Return the shopping cart stored in the user's session."""
    return session.setdefault("cart", [])


def cart_total(cart: list[dict[str, Any]]) -> float:
    """Compute the total price of all items inside the cart."""
    return sum(item["price"] * item["quantity"] for item in cart)


def supabase_headers(include_json: bool = True) -> dict[str, str]:
    """Headers required by Supabase REST API requests."""
    # Supabase REST calls use the anon/public key as the request token.
    # The publishable key is kept above for reference because it was also provided in the project setup.
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
    }
    if include_json:
        headers["Content-Type"] = "application/json"
    return headers


def fetch_menu_items() -> tuple[list[dict[str, Any]], str | None]:
    """
    Read menu items from Supabase.
    If the table does not exist yet, return sample data so the app still works.
    """
    endpoint = f"{SUPABASE_URL}/rest/v1/menu_items"
    params = {"select": "*", "order": "id.asc"}

    try:
        response = requests.get(endpoint, headers=supabase_headers(False), params=params, timeout=15)
        response.raise_for_status()
        menu_items = response.json()

        if not menu_items:
            return SAMPLE_MENU, "Supabase menu table is empty, so sample menu items are being shown."

        return menu_items, None
    except requests.RequestException:
        return SAMPLE_MENU, "Supabase menu table is unavailable right now, so sample menu items are being shown."


def fetch_orders() -> tuple[list[dict[str, Any]], str | None]:
    """Read all orders from Supabase for the dashboard page."""
    endpoint = f"{SUPABASE_URL}/rest/v1/orders"
    params = {"select": "*", "order": "created_at.desc"}

    try:
        response = requests.get(endpoint, headers=supabase_headers(False), params=params, timeout=15)
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException:
        return [], "Orders could not be loaded from Supabase. Create the tables in Supabase first."


def create_order(customer_name: str, table_number: str, items: list[dict[str, Any]]) -> tuple[bool, str]:
    """Create a new order in Supabase."""
    endpoint = f"{SUPABASE_URL}/rest/v1/orders"
    payload = {
        "customer_name": customer_name,
        "table_number": table_number or None,
        "items": items,
        "total_amount": cart_total(items),
        "status": "Pending",
    }
    headers = supabase_headers()
    headers["Prefer"] = "return=representation"

    try:
        response = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=15)
        response.raise_for_status()
        return True, "Order created successfully."
    except requests.RequestException:
        return False, "Order could not be saved to Supabase. Please check your Supabase tables and API settings."


def update_order_status(order_id: str, new_status: str) -> tuple[bool, str]:
    """Update the status of one order record."""
    endpoint = f"{SUPABASE_URL}/rest/v1/orders"
    headers = supabase_headers()
    headers["Prefer"] = "return=representation"

    try:
        response = requests.patch(
            endpoint,
            headers=headers,
            params={"id": f"eq.{order_id}"},
            data=json.dumps({"status": new_status}),
            timeout=15,
        )
        response.raise_for_status()
        return True, "Order status updated."
    except requests.RequestException:
        return False, "Order status could not be updated."


def delete_order(order_id: str) -> tuple[bool, str]:
    """Delete an order from Supabase."""
    endpoint = f"{SUPABASE_URL}/rest/v1/orders"

    try:
        response = requests.delete(
            endpoint,
            headers=supabase_headers(False),
            params={"id": f"eq.{order_id}"},
            timeout=15,
        )
        response.raise_for_status()
        return True, "Order deleted."
    except requests.RequestException:
        return False, "Order could not be deleted."


@app.context_processor
def inject_layout_data() -> dict[str, Any]:
    """Values returned here are available in every template."""
    cart = get_cart()
    return {
        "cart_count": sum(item["quantity"] for item in cart),
        "cart_total_amount": cart_total(cart),
    }


@app.route("/")
def home() -> str:
    """Home page that introduces the restaurant project."""
    return render_template("home.html")


@app.route("/menu")
def menu() -> str:
    """Menu page that displays food items from Supabase."""
    menu_items, message = fetch_menu_items()
    return render_template("menu.html", menu_items=menu_items, info_message=message)


@app.route("/cart/add/<int:item_id>", methods=["POST"])
def add_to_cart(item_id: int):
    """Add a menu item to the cart stored in the session."""
    menu_items, _ = fetch_menu_items()
    selected_item = next((item for item in menu_items if int(item["id"]) == item_id), None)

    if not selected_item:
        flash("Menu item not found.", "error")
        return redirect(url_for("menu"))

    cart = get_cart()
    existing_item = next((item for item in cart if int(item["id"]) == item_id), None)

    if existing_item:
        existing_item["quantity"] += 1
    else:
        cart.append(
            {
                "id": int(selected_item["id"]),
                "name": selected_item["name"],
                "price": float(selected_item["price"]),
                "quantity": 1,
            }
        )

    session.modified = True
    flash(f"{selected_item['name']} added to cart.", "success")
    return redirect(url_for("menu"))


@app.route("/cart/remove/<int:item_id>", methods=["POST"])
def remove_from_cart(item_id: int):
    """Remove one menu item from the session cart."""
    cart = get_cart()
    session["cart"] = [item for item in cart if int(item["id"]) != item_id]
    session.modified = True
    flash("Item removed from cart.", "success")
    return redirect(url_for("order"))


@app.route("/order", methods=["GET", "POST"])
def order():
    """
    Order page that shows the cart and creates a new Supabase order.
    GET  -> display order form
    POST -> save the order into Supabase
    """
    cart = get_cart()

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        table_number = request.form.get("table_number", "").strip()

        if not customer_name:
            flash("Customer name is required.", "error")
            return redirect(url_for("order"))

        if not cart:
            flash("Add menu items before placing an order.", "error")
            return redirect(url_for("menu"))

        success, message = create_order(customer_name, table_number, cart)
        flash(message, "success" if success else "error")

        if success:
            session["cart"] = []
            session.modified = True
            return redirect(url_for("dashboard"))

    return render_template("order.html", cart=cart, total_amount=cart_total(cart))


@app.route("/dashboard")
def dashboard() -> str:
    """Dashboard page to monitor and manage orders."""
    orders, message = fetch_orders()
    return render_template("dashboard.html", orders=orders, info_message=message)


@app.route("/dashboard/update/<order_id>", methods=["POST"])
def dashboard_update(order_id: str):
    """Change the order status from the dashboard."""
    new_status = request.form.get("status", "Pending")
    success, message = update_order_status(order_id, new_status)
    flash(message, "success" if success else "error")
    return redirect(url_for("dashboard"))


@app.route("/dashboard/delete/<order_id>", methods=["POST"])
def dashboard_delete(order_id: str):
    """Delete an order from the dashboard."""
    success, message = delete_order(order_id)
    flash(message, "success" if success else "error")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
