"""Superadmin area — the catalogue and its inventory.

Kept as its own package, and its own blueprint, so that everything a superadmin
can do is reachable from exactly one place in the source: if it is not under
`routes/admin/`, it is not privileged.

Membership is granted from the shell (`flask make-admin <email>`), never through
a form.
"""

from routes.admin.routes import bp

__all__ = ["bp"]
