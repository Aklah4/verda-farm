"""Who the visitor is, and how the rest of the app asks.

The auth package owns every session key that identifies a signed-in visitor. No
other blueprint reads or writes those keys directly — they call these helpers —
so swapping the session for a real user table touches this file and nothing else.
"""

from functools import wraps

from flask import redirect, request, session, url_for

LOGGED_IN = "logged_in"
ACCOUNT_ID = "account_id"
ACCOUNT_NAME = "account_name"
ACCOUNT_ROLE = "account_role"


def start_session(user_id, name, role=None):
    # Only the account keys are touched: a cart built while signed out belongs
    # to the same person, and clearing the session would throw it away at the
    # exact moment they signed in to check out.
    session[LOGGED_IN] = True
    # The session is a signed JSON cookie and cannot carry an ObjectId, so the
    # id goes in as a string; callers that query Mongo with it re-wrap it.
    session[ACCOUNT_ID] = str(user_id)
    session[ACCOUNT_NAME] = name
    session[ACCOUNT_ROLE] = role


def end_session():
    session.pop(LOGGED_IN, None)
    session.pop(ACCOUNT_ID, None)
    session.pop(ACCOUNT_NAME, None)
    session.pop(ACCOUNT_ROLE, None)


def is_logged_in():
    return session.get(LOGGED_IN, False)


def account_id():
    return session.get(ACCOUNT_ID)


def account_name(default="friend"):
    return session.get(ACCOUNT_NAME) or default


def looks_like_admin():
    """Whether to *show* admin links. Never whether to *allow* an admin action.

    This reads the session, which is a hint the user's own cookie carries. The
    guard that actually protects /admin re-checks the role in the database —
    see `routes.admin.routes.admin_required`.
    """
    return session.get(ACCOUNT_ROLE) == "superadmin"


def login_required(view):
    """Bounce anonymous visitors to sign-in, then return them to where they aimed."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_logged_in():
            # full_path keeps any query string, but leaves a bare "?" without one.
            target = request.full_path.rstrip("?")
            return redirect(url_for("auth.login", next=target))
        return view(*args, **kwargs)

    return wrapped
