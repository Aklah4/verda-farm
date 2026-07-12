"""The `orders` collection — written at checkout, read by the dashboard.

Orders used to live in the session cookie, which meant a customer's history
vanished when the cookie did and never existed for anyone else. They are now
documents in Mongo: checkout writes one, the dashboard reads them back, and the
confirmation page looks up the one just placed rather than re-rendering a copy
carried in the session.

A signed-in customer's orders carry their `account_id`, which is what ties the
storefront to their dashboard. Guests check out without an account, so theirs
are stored with `account_id: None` — kept for the business, but belonging to no
dashboard.
"""

import random
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import current_app
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

import db

PROCESSING = "Processing"

# Enough attempts that a collision on the random order number is a non-event;
# the unique index is what guarantees two customers never share one.
_NUMBER_ATTEMPTS = 5


def collection():
    """The `orders` collection, with the indexes its two queries need."""
    orders = db.get_db()["orders"]

    if not current_app.extensions.get("orders_indexed"):
        # The dashboard's query: this account's orders, newest first.
        orders.create_index([("account_id", ASCENDING), ("placed_at", DESCENDING)])
        # The confirmation lookup, and the guarantee behind _new_number.
        orders.create_index("number", unique=True)
        current_app.extensions["orders_indexed"] = True

    return orders


def _object_id(value):
    """Session values are strings; Mongo matches on ObjectId or not at all."""
    if not value:
        return None
    try:
        return ObjectId(value)
    except InvalidId:
        return None


def _new_number():
    return "VF-{}".format(random.randint(100000, 999999))


def _view(order):
    """The shape the templates read. Both the dashboard and the receipt use this."""
    placed = order["placed_at"]

    return {
        "number": order["number"],
        # strftime("%-d") is not portable to Windows, so the day is formatted by hand.
        "date": "{} {} {}".format(placed.day, placed.strftime("%b"), placed.year),
        "name": order["name"],
        "email": order["email"],
        "total": order["total"],
        "status": order["status"],
        "lines": order["lines"],
        # Not "items": Jinja resolves `order.items` to dict.items — the method,
        # not the key — and the template would print <built-in method items ...>.
        "contents": ", ".join(line["title"] for line in order["lines"]),
    }


def place(account_id, name, email, lines, total):
    """Write a new order and return it in template shape."""
    order = {
        "account_id": _object_id(account_id),
        "name": name,
        "email": email,
        "lines": lines,
        "total": total,
        "status": PROCESSING,
        "placed_at": datetime.now(timezone.utc),
    }

    orders = collection()
    for _ in range(_NUMBER_ATTEMPTS):
        order["number"] = _new_number()
        try:
            orders.insert_one(order)
        except DuplicateKeyError:
            continue  # that number is taken — draw another
        return _view(order)

    raise RuntimeError("could not allocate an unused order number")


def for_account(account_id):
    """This account's orders, newest first. Empty for a guest."""
    owner = _object_id(account_id)
    if owner is None:
        return []

    cursor = collection().find({"account_id": owner}).sort("placed_at", DESCENDING)
    return [_view(order) for order in cursor]


def by_number(number):
    """One order, for the confirmation page. None if it does not exist."""
    order = collection().find_one({"number": number})
    return _view(order) if order else None
