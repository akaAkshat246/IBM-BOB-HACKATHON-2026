"""
orders.py — Order processing logic.
"""

from pricing import calculate_total


def process_order(data: dict) -> dict:
    """
    Validate and process an order.
    BUG: Passes raw items directly to calculate_total without checking
         that each item has a 'price' key.  Items from the legacy API
         carry 'unit_cost' instead, so 'price' is absent.
    """
    order = data  # no normalisation step
    # Line 18 — second frame in keyerror_price.txt
    total = calculate_total(order["items"])
    return {"total": total, "item_count": len(order["items"])}


def create_order(customer_id: str, line_items: list) -> dict:
    """Create a new order from validated line items."""
    if not line_items:
        raise ValueError("Cannot create an order with no items")
    return {
        "customer_id": customer_id,
        "items": line_items,
        "status": "pending",
    }
