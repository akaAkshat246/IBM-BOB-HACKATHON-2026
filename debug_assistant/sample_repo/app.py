"""
app.py — Sample web application entry point.
Bug: handle_request does not validate incoming order data before forwarding it
     to process_order, allowing items with missing 'price' keys through.
"""

from orders import process_order
from users import get_user


def handle_request(data: dict) -> dict:
    """Route incoming HTTP request data to the right handler."""
    if data.get("type") == "order":
        result = process_order(data)
        return {"status": "ok", "result": result}
    elif data.get("type") == "profile":
        user_id = data.get("user_id")
        user = get_user(user_id)
        return render_profile(user)
    return {"status": "unknown"}


def _build_order_from_raw(raw: dict) -> dict:
    """
    Build a normalised order dict from raw request data.
    BUG: Does not add a default 'price' key when the item schema
         comes from a legacy API that uses 'unit_cost' instead of 'price'.
    """
    items = []
    for item in raw.get("line_items", []):
        items.append({
            "name": item.get("name"),
            # Missing: if legacy API uses 'unit_cost', this will be absent
            "price": item.get("price"),      # may be None or absent
            "quantity": item.get("qty", 1),
        })
    return {"items": items, "customer": raw.get("customer")}


def render_profile(user) -> dict:
    """Render user profile data.
    BUG: user.profile can be None when the user was created via OAuth
         but never completed their profile setup.
    """
    # Line 55 — crash site for attributeerror_profile.txt
    name = user.profile.display_name
    return {"name": name, "email": user.email}
