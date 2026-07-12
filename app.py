"""Verda Farm — Flask storefront.

Application factory. Routes live in `routes/` (one blueprint per area), cart
rules in `cart_service.py`, catalogue content in `data.py`.
"""

import os
import warnings

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

import cart_service
import db
from cli import register_cli
from config import DEV_SECRET_KEY, Config
from routes import register_blueprints
from routes.auth.session import account_name, is_logged_in, looks_like_admin

csrf = CSRFProtect()


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    check_secret_key(app)
    trust_proxy(app)

    # Every state-changing POST (checkout, sign-in, cart mutations) carries a
    # token; without this a third-party page can drive them on a signed-in user.
    csrf.init_app(app)

    # Registers the client holder and `flask db-ping`; does not connect.
    db.init_app(app)

    register_blueprints(app)
    register_cli(app)  # flask make-admin / seed-products
    register_filters(app)
    register_context(app)
    register_headers(app)
    register_errors(app)

    return app


def check_secret_key(app):
    if app.config["SECRET_KEY"] != DEV_SECRET_KEY:
        return

    if app.config["ENV"] == "production":
        raise RuntimeError(
            "SECRET_KEY is still the development default. Session cookies would "
            "be forgeable — set SECRET_KEY in the environment before deploying."
        )

    warnings.warn(
        "Using the development SECRET_KEY. Set SECRET_KEY before deploying.",
        stacklevel=2,
    )


def trust_proxy(app):
    """Read the real client IP from X-Forwarded-For — but only behind a proxy.

    Without this, everything behind Nginx/Render/Cloudflare sees the proxy's own
    address as `remote_addr`, so every visitor on earth shares one bucket in the
    rate limiter: five wrong passwords from anyone would lock out everyone.

    With it applied when *no* proxy exists, the opposite hole opens — the header
    is client-supplied, so an attacker forges a fresh IP per request and the
    per-IP limit never trips. Hence TRUST_PROXY: off unless you say otherwise.
    """
    hops = app.config["TRUST_PROXY"]
    if not hops:
        return

    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops, x_port=hops
    )


def register_filters(app):
    @app.template_filter("naira")
    def naira(amount):
        return "₦{:,}".format(int(amount))


def register_context(app):
    @app.context_processor
    def inject_globals():
        """Values the base layout needs on every page."""
        return {
            "accent": app.config["ACCENT"],
            "show_whatsapp": app.config["SHOW_WHATSAPP"],
            "cart_count": cart_service.summary()["count"],
            "logged_in": is_logged_in(),
            "account_name": account_name(),
            # Draws the Admin link. The /admin guard does its own database
            # check — this only decides what the template shows.
            "is_admin": looks_like_admin(),
            "active": request.endpoint,
        }


# What the browser is allowed to load, and from where. Everything this app needs
# is either same-origin or one of these two hosts, so anything else — an injected
# script tag pointing at an attacker's domain, a beacon exfiltrating a session —
# is refused by the browser even if it somehow got onto the page.
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        # Product and hero photos come from Cloudinary; data: covers inline SVG.
        "img-src 'self' https://res.cloudinary.com data:",
        # The design leans on style="..." attributes throughout, which need
        # 'unsafe-inline'. That is a real (if minor) loosening: it is why no
        # *script* is allowed inline — see the note below.
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        # No 'unsafe-inline' here, which is the setting that actually matters:
        # even if a payload were somehow injected into a page, the browser will
        # not run it. It also means no onclick="" handlers anywhere — the delete
        # confirmation lives in main.js for exactly this reason.
        "script-src 'self'",
        "form-action 'self'",      # a form on this page cannot post elsewhere
        "frame-ancestors 'none'",  # nobody may frame us — no clickjacking
        "base-uri 'self'",
    ]
)


def register_headers(app):
    @app.after_request
    def security_headers(response):
        """Headers every response carries.

        Cache-Control: never let a browser reuse a rendered page. Every HTML page
            here is either personal (cart, dashboard) or carries a one-use CSRF
            token; a cached copy posts a stale token and fails for reasons the
            visitor cannot possibly diagnose. Static files still cache normally.

        The rest are cheap, standard, and were simply absent.
        """
        if response.mimetype == "text/html":
            response.headers["Cache-Control"] = "no-store"
            response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY

        # Belt and braces with frame-ancestors, for browsers that predate CSP.
        response.headers["X-Frame-Options"] = "DENY"
        # Stop the browser second-guessing our Content-Type and running an
        # uploaded file as script.
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Do not leak the page a customer came from (which may name a product,
        # or carry a `next` param) to third-party hosts.
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        if app.config["ENV"] == "production":
            # Only meaningful over TLS, and only set there: sending it in dev
            # would pin localhost to https and break the site for a year.
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


def register_errors(app):
    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404

    @app.errorhandler(CSRFError)
    def csrf_expired(_error):
        """A stale token is a usability problem, not an attack to shout about.

        It happens when a form has sat open long enough for the token to expire.
        Bounce the visitor back to the same page with a fresh one and say so,
        rather than showing Flask's bare 400 page.
        """
        flash("That page had gone stale. Please try again.", "toast")
        return redirect(request.full_path.rstrip("?") or url_for("main.home"))

    @app.errorhandler(413)
    def too_large(_error):
        """Flask aborts an over-MAX_CONTENT_LENGTH upload before any view runs,
        so the admin form never gets the chance to report this itself."""
        limit_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        flash("That image is too large — keep it under {}MB.".format(limit_mb), "toast")
        return redirect(url_for("admin.index"))


app = create_app()


if __name__ == "__main__":
    # HOST=0.0.0.0 serves the app to the whole local network, so a phone on the
    # same wifi can reach it at http://<this-machine's-ip>:5000.
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))

    # Werkzeug's interactive debugger runs arbitrary Python typed into the
    # browser. Bound to localhost that is a convenience; reachable from the
    # network it is a shell for anyone on the wifi. So the reloader stays on
    # (that is what makes editing pleasant) and the debugger goes off the moment
    # we are not strictly local.
    local_only = host in ("127.0.0.1", "localhost")
    if not local_only:
        print("serving on the local network at http://{}:{}".format(host, port))

    app.run(host=host, port=port, debug=True, use_debugger=local_only)
