"""Register, sign in, sign out.

Accounts live in Mongo (`routes/auth/users.py`); this module is only the HTTP
shape around them — read the form, hand it to `users`, turn the outcome into a
session and a redirect, or re-render the form with what went wrong.

Both forms re-render with the submitted values on failure, so a typo in one
field does not cost the visitor the other four.
"""

from flask import Blueprint, current_app, redirect, render_template, request, url_for
from pymongo.errors import PyMongoError

import rate_limit
from routes.auth import users
from routes.auth.session import end_session, start_session
from security import safe_redirect_target

bp = Blueprint("auth", __name__)

UNAVAILABLE = "We could not reach the account service. Please try again in a moment."


def _destination():
    """Where sign-in sends you: the page you were headed for, else the dashboard.

    `next` arrives from a query string or a hidden field, both attacker-supplied,
    so it is only honoured when it resolves back to this host.
    """
    return safe_redirect_target(
        request.values.get("next"), fallback="dashboard.index"
    )


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("auth/register.html", form={})

    form = {
        "first_name": request.form.get("first_name", "").strip(),
        "last_name": request.form.get("last_name", "").strip(),
        "email": request.form.get("email", "").strip(),
    }
    password = request.form.get("password", "")
    retype_password = request.form.get("retype_password", "")

    problem = users.problem_with(
        form["first_name"],
        form["last_name"],
        form["email"],
        password,
        retype_password,
    )
    if problem:
        return render_template("auth/register.html", form=form, error=problem), 400

    try:
        account = users.create(
            form["first_name"], form["last_name"], form["email"], password
        )
    except users.EmailTaken:
        return (
            render_template(
                "auth/register.html",
                form=form,
                error="That email already has an account — sign in instead.",
            ),
            409,
        )
    except PyMongoError:
        current_app.logger.exception("could not create account")
        return render_template("auth/register.html", form=form, error=UNAVAILABLE), 503

    # Registering signs you in; making someone type the same password again on
    # the very next screen buys nothing.
    start_session(account["_id"], account["first_name"], account.get("role"))
    return redirect(_destination())


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("auth/login.html", form={})

    form = {"email": request.form.get("email", "").strip()}
    password = request.form.get("password", "")

    if not form["email"] or not password:
        return (
            render_template(
                "auth/login.html",
                form=form,
                error="Enter your email and password to sign in.",
            ),
            400,
        )

    # Throttle before the password is even compared — see rate_limit.py.
    try:
        wait = rate_limit.locked_out(form["email"], request.remote_addr)
    except PyMongoError:
        current_app.logger.exception("could not check the rate limit")
        wait = 0  # a broken limiter must not lock real customers out

    if wait:
        return (
            render_template(
                "auth/login.html",
                form=form,
                error="Too many failed attempts. Try again in {}.".format(
                    rate_limit.wait_message(wait)
                ),
            ),
            429,
        )

    try:
        account = users.authenticate(form["email"], password)
    except PyMongoError:
        current_app.logger.exception("could not sign in")
        return render_template("auth/login.html", form=form, error=UNAVAILABLE), 503

    if account is None:
        rate_limit.record_failure(form["email"], request.remote_addr)
        # Deliberately vague: naming which half was wrong tells an attacker
        # whether the address has an account here.
        return (
            render_template(
                "auth/login.html",
                form=form,
                error="Those details do not match an account.",
            ),
            401,
        )

    rate_limit.clear(form["email"], request.remote_addr)
    start_session(account["_id"], account["first_name"], account.get("role"))
    return redirect(_destination())


@bp.post("/logout")
def logout():
    end_session()
    return redirect(url_for("main.home"))
