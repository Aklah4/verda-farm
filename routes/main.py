"""Landing page, story page, and the WhatsApp call-to-action."""

from flask import Blueprint, current_app, flash, redirect, render_template, request

import product_service
import site_service
from data import CATEGORY_CARDS
from security import safe_redirect_target

bp = Blueprint("main", __name__)

FEATURED_COUNT = 8


@bp.route("/")
def home():
    return render_template(
        "home.html",
        hero_layout=current_app.config["HERO_LAYOUT"],
        hero_tiles=site_service.hero_tiles(),  # editable from /admin/hero
        category_cards=CATEGORY_CARDS,
        featured=product_service.all_products()[:FEATURED_COUNT],
    )


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.post("/whatsapp")
def whatsapp():
    flash("Opening WhatsApp chat with our team…", "toast")
    return redirect(safe_redirect_target(request.referrer, fallback="main.home"))
