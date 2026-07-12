"""Dashboard endpoints. Sign-in and sign-out live in `routes/auth/`.

Everything here is behind `login_required`, so a signed-out visitor who lands on
/dashboard is sent to sign in and returned here afterwards.
"""

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from pymongo.errors import PyMongoError

from routes.auth.session import login_required
from routes.dashboard import service

bp = Blueprint("dashboard", __name__)

UNAVAILABLE = "We could not load your orders just now. Please refresh in a moment."


@bp.get("/dashboard")
@login_required
def index():
    # Sign-in, checkout and the admin all degrade politely when Atlas is
    # unreachable; the dashboard was the one page that threw a 500 at the
    # customer instead. It now renders empty with an explanation.
    try:
        history = service.orders()
        stats = service.stats(history)
        prefs = service.preferences()
        error = None
    except PyMongoError:
        current_app.logger.exception("could not load the dashboard")
        history, stats, prefs = [], service.stats([]), service.DEFAULT_PREFERENCES
        error = UNAVAILABLE

    # `account_name` comes from the global context — the header shows it on
    # every page, so it is injected once rather than passed view by view.
    return render_template(
        "dashboard/index.html",
        orders=history,
        stats=stats,
        prefs=prefs,
        toggles=service.TOGGLES,
        error=error,
    )


@bp.post("/dashboard/preferences")
@login_required
def preferences():
    try:
        service.save_preferences(request.form)
        flash("Preferences saved", "toast")
    except PyMongoError:
        current_app.logger.exception("could not save preferences")
        flash("Could not save your preferences. Please try again.", "toast")

    return redirect(url_for("dashboard.index"))
