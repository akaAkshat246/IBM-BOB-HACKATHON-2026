"""
pricing.py — Price calculation utilities.
"""

TAX_RATE = 0.08


def calculate_total(items: list) -> float:
    """
    Sum the total price for a list of order items.

    Each item is expected to have:
      - 'price'    (float)  — unit price
      - 'quantity' (int)    — number of units

    BUG: No validation that 'price' exists.  Items from the legacy API
         carry 'unit_cost' instead, which causes a KeyError here.
    """
    subtotal = 0.0
    for item in items:
        # Line 31 — crash site in keyerror_price.txt
        unit_price = item["price"]          # KeyError if legacy item
        subtotal += unit_price * item["quantity"]
    tax = subtotal * TAX_RATE
    return round(subtotal + tax, 2)


def apply_discount(total: float, discount_pct: float) -> float:
    """Apply a percentage discount to a total."""
    if not 0 <= discount_pct <= 100:
        raise ValueError(f"discount_pct must be 0–100, got {discount_pct}")
    return round(total * (1 - discount_pct / 100), 2)
