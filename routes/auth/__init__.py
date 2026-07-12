"""Login area — the endpoints that start and end a signed-in session.

Kept apart from the dashboard so the two can change independently: this package
is the only thing that will need rewriting when real credentials arrive.
"""

from routes.auth.routes import bp

__all__ = ["bp"]
