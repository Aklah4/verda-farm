"""Blueprint registry — one blueprint per area of the storefront.

`auth` (sign in / out), `dashboard` (the signed-in area) and `admin` (the
superadmin area) are packages of their own; the rest are single modules.
"""

from routes.admin import bp as admin_bp
from routes.auth import bp as auth_bp
from routes.cart import bp as cart_bp
from routes.dashboard import bp as dashboard_bp
from routes.leads import bp as leads_bp
from routes.main import bp as main_bp
from routes.shop import bp as shop_bp

ALL_BLUEPRINTS = (
    main_bp, shop_bp, cart_bp, leads_bp, auth_bp, dashboard_bp, admin_bp,
)


def register_blueprints(app):
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)
