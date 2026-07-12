"""Session-backed shopping cart.

Kept out of the route modules so the cart rules live in one place — the routes
just call in and render whatever comes back.
"""

from flask import current_app, session

import product_service


def _entries():
    """Cart is an ordered list of {id, qty} so line order stays stable.

    Deliberately a plain read: `setdefault` here would mark the session dirty on
    every page render, handing a cookie to visitors who never touched the cart.
    """
    return session.get("cart", [])


def _save(entries):
    session["cart"] = entries
    session.modified = True


def _clamp(qty):
    return max(1, min(int(qty), current_app.config["MAX_LINE_QTY"]))


def add(product_id, qty=1):
    entries = _entries()
    for entry in entries:
        if entry["id"] == product_id:
            entry["qty"] = _clamp(entry["qty"] + qty)
            break
    else:
        entries.append({"id": product_id, "qty": _clamp(qty)})
    _save(entries)


def change_qty(product_id, delta):
    entries = _entries()
    for entry in entries:
        if entry["id"] == product_id:
            entry["qty"] = _clamp(entry["qty"] + delta)
            break
    _save(entries)


def remove(product_id):
    _save([e for e in _entries() if e["id"] != product_id])


def clear():
    _save([])


def lines():
    entries = _entries()
    if not entries:
        return []

    # One query for the whole cart. The catalogue lives in Mongo now, so a
    # lookup per line would mean a round trip per item — and `summary()` runs on
    # every page render to draw the header badge.
    products = product_service.find_many(entry["id"] for entry in entries)

    out = []
    for entry in entries:
        product = products.get(entry["id"])
        if product is None:  # product retired since the item was added
            continue
        out.append(
            {
                "product": product,
                "qty": entry["qty"],
                "line_total": product["price"] * entry["qty"],
            }
        )
    return out


def summary():
    items = lines()
    subtotal = sum(line["line_total"] for line in items)
    delivery = current_app.config["DELIVERY_FEE"] if subtotal > 0 else 0
    return {
        "lines": items,
        "count": sum(line["qty"] for line in items),
        "subtotal": subtotal,
        "delivery": delivery,
        "total": subtotal + delivery,
    }
