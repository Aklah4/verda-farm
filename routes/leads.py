"""Lead capture: contact, wholesale quote, export inquiry.

All three are the same shape — validate required fields, otherwise re-render with
the values kept — so they share one handler.
"""

from flask import Blueprint, redirect, render_template, request, url_for

from data import EXPORT_STEPS, VOLUME_TIERS

bp = Blueprint("leads", __name__)


def _handle(template, fields, required, **context):
    form = {f: "" for f in fields}
    error = None

    if request.method == "POST":
        form = {f: request.form.get(f, "").strip() for f in fields}

        if not any(not form[f] for f in required):
            # Redirect on success so refreshing the thank-you panel cannot
            # re-submit the enquiry.
            return redirect(url_for(request.endpoint, sent=1))

        error = "Please complete the required fields."

    done = request.args.get("sent") == "1"
    return render_template(template, form=form, error=error, done=done, **context)


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    return _handle(
        "contact.html",
        fields=["name", "email", "subject", "message"],
        required=["name", "email", "message"],
    )


@bp.route("/wholesale", methods=["GET", "POST"])
def wholesale():
    return _handle(
        "wholesale.html",
        fields=["business", "contact", "region", "product", "qty", "email"],
        required=["business", "contact", "region", "product", "email"],
        tiers=VOLUME_TIERS,
    )


@bp.route("/export", methods=["GET", "POST"])
def export():
    return _handle(
        "export.html",
        fields=["company", "country", "product", "volume", "email", "message"],
        required=["company", "country", "product", "email"],
        steps=EXPORT_STEPS,
    )
