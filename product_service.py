"""The `products` collection — the catalogue.

Products used to be a hard-coded list in `data.py`, which meant the only way to
change a price was to edit Python and redeploy. They are now documents in Mongo:
the admin dashboard writes them, the storefront reads them, and `data.py` keeps
the original twelve only as seed material for `flask seed-products`.

`id` is the human-readable slug ("plantain") that appears in URLs and in cart
entries — not Mongo's `_id`. It is unique, and it is what everything else in the
app refers to a product by, so it stays stable even as the document changes.
"""

import re
from datetime import datetime, timezone

from flask import current_app
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

import db

# Colour swatch drawn when a product has no photo yet — the storefront's look
# before images existed, kept as the fallback.
DEFAULT_TONE = "#E9DFA0"
DEFAULT_INK = "#524711"

# Fields the storefront reads. `_id` is deliberately not among them.
FIELDS = (
    "id", "name", "cat", "aud", "price", "unit",
    "tone", "ink", "tag", "blurb", "stock", "image_url", "image_id",
)


class SlugTaken(Exception):
    """Another product already uses that slug."""


def collection():
    products = db.get_db()["products"]

    if not current_app.extensions.get("products_indexed"):
        products.create_index("id", unique=True)
        products.create_index([("cat", ASCENDING)])
        current_app.extensions["products_indexed"] = True

    return products


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "product"


def _view(document):
    """A plain dict for the templates, without Mongo's ObjectId."""
    return {field: document.get(field) for field in FIELDS}


def all_products():
    return [_view(p) for p in collection().find().sort("name", ASCENDING)]


def find(product_id):
    document = collection().find_one({"id": product_id})
    return _view(document) if document else None


def filter_products(category="All", audience="All"):
    query = {}
    if category != "All":
        query["cat"] = category
    if audience != "All":
        query["aud"] = audience  # matches if the array contains it

    return [_view(p) for p in collection().find(query).sort("name", ASCENDING)]


def find_many(product_ids):
    """Every product in `product_ids`, keyed by slug.

    One query for the whole cart: looking each line up separately would put a
    round trip per item on the wire, on every single page render.
    """
    if not product_ids:
        return {}

    found = collection().find({"id": {"$in": list(product_ids)}})
    return {p["id"]: _view(p) for p in found}


def related(product, limit=3):
    others = collection().find(
        {"cat": product["cat"], "id": {"$ne": product["id"]}}
    ).limit(limit)
    return [_view(p) for p in others]


def create(fields):
    """Insert a product. `fields` comes from the admin form, already cleaned."""
    document = dict(fields)
    document["created_at"] = datetime.now(timezone.utc)
    document["updated_at"] = document["created_at"]

    try:
        collection().insert_one(document)
    except DuplicateKeyError:
        raise SlugTaken(document["id"])

    return _view(document)


def update(product_id, fields):
    """Apply `fields` to an existing product. Its slug never changes."""
    changes = {k: v for k, v in fields.items() if k != "id"}
    changes["updated_at"] = datetime.now(timezone.utc)

    collection().update_one({"id": product_id}, {"$set": changes})
    return find(product_id)


def delete(product_id):
    collection().delete_one({"id": product_id})


# Seeded products start stocked. Seeding them at zero would open the shop with
# "Out of stock" on every single item, which is worse than a rough number the
# admin corrects in a minute.
SEED_STOCK = 25


def seed(products):
    """Insert the starting catalogue, skipping any slug already present.

    Idempotent, so running it twice cannot duplicate the catalogue or overwrite
    a price the admin has since changed by hand.
    """
    added = 0
    for product in products:
        try:
            create({**product, "stock": product.get("stock", SEED_STOCK),
                    "image_url": None, "image_id": None})
            added += 1
        except SlugTaken:
            continue

    return added
