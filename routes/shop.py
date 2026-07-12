"""Product catalogue: listing with filters, and the product detail page."""

from flask import Blueprint, abort, render_template, request

import product_service
from data import AUDIENCES, CATEGORIES

bp = Blueprint("shop", __name__)

_AUDIENCE_VALUES = {value for value, _ in AUDIENCES}


@bp.route("/shop")
def index():
    category = request.args.get("cat", "All")
    audience = request.args.get("aud", "All")

    if category not in CATEGORIES:
        category = "All"
    if audience not in _AUDIENCE_VALUES:
        audience = "All"

    return render_template(
        "shop.html",
        categories=CATEGORIES,
        audiences=AUDIENCES,
        category=category,
        audience=audience,
        products=product_service.filter_products(category, audience),
    )


@bp.route("/product/<product_id>")
def product(product_id):
    item = product_service.find(product_id)
    if item is None:
        abort(404)

    return render_template(
        "product.html",
        product=item,
        related=product_service.related(item),
    )
