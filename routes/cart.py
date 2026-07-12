"""Cart, checkout and order confirmation.

Every mutation is a POST that redirects, so a refresh never re-submits.
"""

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from pymongo.errors import PyMongoError

import cart_service
import order_service
import product_service
from routes.auth.session import account_id
from security import safe_redirect_target

bp = Blueprint("cart", __name__)

CHECKOUT_FIELDS = ["name", "email", "phone", "address", "city", "card", "exp", "cvc"]

# Checkout does not sign anyone in. The prototype used to start a session from
# the name typed here, which — now that accounts are real — would hand a
# signed-in session to anyone who filled in the checkout form. Guests check out
# as guests; their order is still recorded, just against no account.


def _back():
    """Return to the page the action was fired from, if it is really ours."""
    return safe_redirect_target(request.form.get("next"), request.referrer)


@bp.route("/cart")
def index():
    return render_template("cart.html", cart=cart_service.summary(), form={}, error=None)


@bp.post("/cart/add")
def add():
    product_id = request.form.get("product_id", "")
    if product_service.find(product_id) is None:
        abort(404)

    try:
        qty = int(request.form.get("qty", 1))
    except ValueError:
        qty = 1

    cart_service.add(product_id, qty)  # clamped to 1..MAX_LINE_QTY
    flash("Added to cart", "toast")

    if request.form.get("buy_now"):
        return redirect(url_for("cart.index"))
    return redirect(_back())


@bp.post("/cart/update")
def update():
    delta = 1 if request.form.get("delta") == "inc" else -1
    cart_service.change_qty(request.form.get("product_id", ""), delta)
    return redirect(url_for("cart.index"))


@bp.post("/cart/remove")
def remove():
    cart_service.remove(request.form.get("product_id", ""))
    return redirect(url_for("cart.index"))


@bp.post("/checkout")
def checkout():
    summary = cart_service.summary()
    if not summary["lines"]:
        return redirect(url_for("cart.index"))

    form = {f: request.form.get(f, "").strip() for f in CHECKOUT_FIELDS}

    if any(not form[f] for f in CHECKOUT_FIELDS):
        return render_template(
            "cart.html",
            cart=summary,
            form=form,
            error="Please complete all fields to place your order.",
        )

    lines = [
        {
            "title": line["product"]["name"],
            "qty": line["qty"],
            "line_total": line["line_total"],
        }
        for line in summary["lines"]
    ]

    try:
        order = order_service.place(
            account_id=account_id(),  # None for a guest
            name=form["name"],
            email=form["email"],
            lines=lines,
            total=summary["total"],
        )
    except (PyMongoError, RuntimeError):
        # The cart is deliberately left intact so the customer can simply retry.
        current_app.logger.exception("could not place order")
        return render_template(
            "cart.html",
            cart=summary,
            form=form,
            error="We could not place your order just now. Please try again.",
        ), 503

    # Only the number goes in the session: the receipt is read back from the
    # database, so it cannot drift from what was actually recorded, and a large
    # order cannot overflow the 4KB session cookie.
    session["last_order_number"] = order["number"]
    cart_service.clear()

    return redirect(url_for("cart.confirmation"))


@bp.route("/order/confirmation")
def confirmation():
    number = session.get("last_order_number")
    if not number:
        return redirect(url_for("shop.index"))

    try:
        order = order_service.by_number(number)
    except PyMongoError:
        current_app.logger.exception("could not load order %s", number)
        return redirect(url_for("shop.index"))

    if order is None:
        return redirect(url_for("shop.index"))

    return render_template("confirm.html", order=order)


@bp.post("/quote")
def quote():
    flash("Quote request sent — our team will confirm pricing by email.", "toast")
    return redirect(_back())
