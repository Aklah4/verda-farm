"""Superadmin dashboard: sign-in, products, inventory and product images.

The admin area has its own front door at /admin/login. It is the same account
and the same password as the storefront — there is no second set of credentials
to steal — but it is a separate page that checks the role *before* opening a
session, so a customer who wanders in is turned away at the door rather than
signed in and then 404'd.

Every view except `login` is behind `admin_required`, which re-reads the role
from the database on each request rather than trusting the session cookie.

Stock is a number the admin keeps and the storefront displays. It does not gate
add-to-cart or move at checkout — that was the deliberate choice; making it
authoritative later means changing `cart` and `order_service`, not this file.
"""

from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from pymongo.errors import PyMongoError

import media
import product_service
import rate_limit
import site_service
from data import CATEGORIES
from routes.auth import users
from routes.auth.session import account_id, is_logged_in, start_session
from security import safe_redirect_target

bp = Blueprint("admin", __name__, url_prefix="/admin")

# "All" is the storefront's filter pill, not a category a product can be in.
PRODUCT_CATEGORIES = [c for c in CATEGORIES if c != "All"]
AUDIENCE_VALUES = ("retail", "wholesale", "export")

# One message for every way a sign-in can fail: wrong password, no such account,
# or a real customer who simply is not an admin. Saying which would tell whoever
# is guessing that the address exists, or that it is worth targeting.
BAD_CREDENTIALS = "Those details do not match an admin account."


def admin_required(view):
    """Only a superadmin gets in. Everyone else is told the page is not there.

    A 404 rather than a 403: a stranger poking at /admin learns nothing about
    whether the page exists. Signed-out visitors get the admin sign-in page,
    because being asked to log in is not itself a disclosure.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for("admin.login", next=request.full_path.rstrip("?")))

        if not users.is_superadmin(account_id()):
            abort(404)

        return view(*args, **kwargs)

    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    """The admin front door. Deliberately not behind `admin_required`."""
    # Already an admin? Skip the form. A signed-in customer is *not* bounced on
    # to the catalogue — they get the form, and their credentials still have to
    # clear the role check below.
    if is_logged_in() and users.is_superadmin(account_id()):
        return redirect(_destination())

    if request.method == "GET":
        return render_template("admin/login.html", form={})

    # Staff sign in with a username ("admin"). It is matched against the same
    # login-handle field customers use for their email, so there is one unique
    # index and no way for the two to collide.
    form = {"username": request.form.get("username", "").strip()}
    password = request.form.get("password", "")

    if not form["username"] or not password:
        return render_template(
            "admin/login.html", form=form,
            error="Enter your username and password.",
        ), 400

    # Throttle before touching the database: a locked-out attacker should not
    # even get a password comparison out of us, let alone its timing.
    try:
        wait = rate_limit.locked_out(form["username"], request.remote_addr)
    except PyMongoError:
        current_app.logger.exception("could not check the rate limit")
        wait = 0  # a broken limiter must not lock the real admin out

    if wait:
        current_app.logger.warning(
            "throttled admin sign-in for %r from %s", form["username"], request.remote_addr
        )
        return render_template(
            "admin/login.html", form=form,
            error="Too many failed attempts. Try again in {}.".format(
                rate_limit.wait_message(wait)
            ),
        ), 429

    try:
        account = users.authenticate(form["username"], password)
    except PyMongoError:
        current_app.logger.exception("admin sign-in failed")
        return render_template(
            "admin/login.html", form=form,
            error="We could not reach the account service. Try again in a moment.",
        ), 503

    # The role is checked before any session is started, so signing in here can
    # never hand out a session to someone who is not an admin.
    if account is None or account.get("role") != users.SUPERADMIN:
        # A customer's correct password counts as a failure here too: this door
        # is not theirs, and guessing at it should cost the same.
        rate_limit.record_failure(form["username"], request.remote_addr)
        current_app.logger.warning(
            "rejected admin sign-in for %r from %s", form["username"], request.remote_addr
        )
        return render_template("admin/login.html", form=form, error=BAD_CREDENTIALS), 401

    rate_limit.clear(form["username"], request.remote_addr)
    start_session(account["_id"], account["first_name"], account["role"])
    return redirect(_destination())


def _destination():
    """Where sign-in lands: the admin page they were headed for, else the list.

    `next` is attacker-supplied, so it is only honoured when it resolves back to
    this host — and, here, only when it stays inside /admin.
    """
    target = request.values.get("next")
    if target and target.startswith(bp.url_prefix):
        return safe_redirect_target(target, fallback="admin.index")

    return url_for("admin.index")


def _form_fields():
    """The product form, cleaned. Returns (fields, problem)."""
    form = request.form

    name = form.get("name", "").strip()
    blurb = form.get("blurb", "").strip()
    unit = form.get("unit", "").strip()
    category = form.get("cat", "").strip()
    audiences = [a for a in form.getlist("aud") if a in AUDIENCE_VALUES]

    fields = {
        "name": name,
        "blurb": blurb,
        "unit": unit or "per unit",
        "cat": category,
        "aud": audiences,
        "tag": form.get("tag", "").strip() or "Fresh",
        "tone": form.get("tone", "").strip() or product_service.DEFAULT_TONE,
        "ink": form.get("ink", "").strip() or product_service.DEFAULT_INK,
    }

    if not name:
        return fields, "Give the product a name."

    if category not in PRODUCT_CATEGORIES:
        return fields, "Choose a category."

    if not audiences:
        return fields, "Pick at least one buyer type."

    # Price and stock are the two that a typo turns into a wrong shop, so they
    # are parsed strictly rather than coerced.
    for key, label in (("price", "price"), ("stock", "stock level")):
        raw = form.get(key, "").strip()
        try:
            value = int(raw)
        except ValueError:
            return fields, "Enter a whole number for the {}.".format(label)

        if value < 0:
            return fields, "The {} cannot be negative.".format(label)

        fields[key] = value

    return fields, None


def _attach_image(fields, slug):
    """Upload the posted file, if any, onto `fields`. Returns a problem or None."""
    upload = request.files.get("image")
    if upload is None or not upload.filename:
        return None  # no new image on this submit — keep whatever is there

    if not media.has_allowed_extension(upload.filename):
        return "Images must be one of: {}.".format(
            ", ".join(media.ALLOWED_EXTENSIONS)
        )

    try:
        image = media.upload(upload, slug)
    except media.NotConfigured as exc:
        return str(exc)
    except media.UploadFailed:
        current_app.logger.exception("image upload failed")
        return "Cloudinary rejected that image. Try another file."

    fields["image_url"] = image["url"]
    fields["image_id"] = image["id"]
    return None


def _render_form(product, error=None, status=200):
    return (
        render_template(
            "admin/form.html",
            product=product,
            categories=PRODUCT_CATEGORIES,
            audiences=AUDIENCE_VALUES,
            uploads_enabled=media.is_configured(),
            error=error,
        ),
        status,
    )


@bp.get("/")
@admin_required
def index():
    products = product_service.all_products()

    return render_template(
        "admin/index.html",
        products=products,
        uploads_enabled=media.is_configured(),
        stats={
            "products": len(products),
            "out_of_stock": sum(1 for p in products if not p["stock"]),
            "units": sum(p["stock"] or 0 for p in products),
        },
    )


@bp.get("/products/new")
@admin_required
def new():
    return _render_form({"aud": [], "stock": 0})


@bp.post("/products")
@admin_required
def create():
    fields, problem = _form_fields()
    if problem:
        return _render_form(fields, problem, 400)

    fields["id"] = product_service.slugify(fields["name"])
    fields.setdefault("image_url", None)
    fields.setdefault("image_id", None)

    problem = _attach_image(fields, fields["id"])
    if problem:
        return _render_form(fields, problem, 400)

    try:
        product_service.create(fields)
    except product_service.SlugTaken:
        return _render_form(
            fields, "A product with a name that close already exists.", 409
        )
    except PyMongoError:
        current_app.logger.exception("could not create product")
        return _render_form(fields, "Could not save. Try again in a moment.", 503)

    flash("{} added".format(fields["name"]), "toast")
    return redirect(url_for("admin.index"))


@bp.get("/products/<product_id>/edit")
@admin_required
def edit(product_id):
    product = product_service.find(product_id)
    if product is None:
        abort(404)

    return _render_form(product)


@bp.post("/products/<product_id>")
@admin_required
def save(product_id):
    product = product_service.find(product_id)
    if product is None:
        abort(404)

    fields, problem = _form_fields()
    if problem:
        return _render_form({**product, **fields}, problem, 400)

    problem = _attach_image(fields, product_id)
    if problem:
        return _render_form({**product, **fields}, problem, 400)

    try:
        product_service.update(product_id, fields)
    except PyMongoError:
        current_app.logger.exception("could not update product")
        return _render_form(
            {**product, **fields}, "Could not save. Try again in a moment.", 503
        )

    flash("{} updated".format(fields["name"]), "toast")
    return redirect(url_for("admin.index"))


@bp.get("/hero")
@admin_required
def hero():
    return render_template(
        "admin/hero.html",
        tiles=site_service.hero_tiles(),
        uploads_enabled=media.is_configured(),
    )


@bp.post("/hero")
@admin_required
def save_hero():
    """Save all three tiles at once — the collage is one thing, not three."""
    tiles = site_service.hero_tiles()
    saved = []

    for tile in tiles:
        slot = tile["slot"]
        # Per-slot field names: label-0, tone-0, image-0, and so on.
        suffix = "-{}".format(slot)

        updated = {
            "label": request.form.get("label" + suffix, "").strip() or tile["label"],
            "tone": request.form.get("tone" + suffix, "").strip() or tile["tone"],
            "ink": request.form.get("ink" + suffix, "").strip() or tile["ink"],
            "image_url": tile["image_url"],
            "image_id": tile["image_id"],
        }

        # "Remove photo" wins over an upload in the same submit: the admin who
        # ticks it and also picks a file most likely changed their mind.
        if request.form.get("clear" + suffix):
            media.delete(tile["image_id"])
            updated["image_url"] = None
            updated["image_id"] = None
        else:
            upload = request.files.get("image" + suffix)
            if upload is not None and upload.filename:
                if not media.has_allowed_extension(upload.filename):
                    return _hero_error(
                        "Images must be one of: {}.".format(
                            ", ".join(media.ALLOWED_EXTENSIONS)
                        )
                    )

                try:
                    image = media.upload(
                        upload,
                        site_service.hero_public_id(slot),
                        folder=media.HERO_FOLDER,
                    )
                except media.NotConfigured as exc:
                    return _hero_error(str(exc))
                except media.UploadFailed:
                    current_app.logger.exception("hero upload failed")
                    return _hero_error("Cloudinary rejected that image. Try another.")

                updated["image_url"] = image["url"]
                updated["image_id"] = image["id"]

        saved.append(updated)

    try:
        site_service.save_hero(saved)
    except PyMongoError:
        current_app.logger.exception("could not save the hero")
        return _hero_error("Could not save. Try again in a moment.")

    flash("Home page hero updated", "toast")
    return redirect(url_for("admin.hero"))


def _hero_error(message):
    return (
        render_template(
            "admin/hero.html",
            tiles=site_service.hero_tiles(),
            uploads_enabled=media.is_configured(),
            error=message,
        ),
        400,
    )


@bp.post("/products/<product_id>/delete")
@admin_required
def delete(product_id):
    product = product_service.find(product_id)
    if product is None:
        abort(404)

    product_service.delete(product_id)
    # The row is already gone; a failure to remove the hosted image must not
    # resurrect it, so this is best-effort inside media.delete.
    media.delete(product.get("image_id"))

    flash("{} deleted".format(product["name"]), "toast")
    return redirect(url_for("admin.index"))
