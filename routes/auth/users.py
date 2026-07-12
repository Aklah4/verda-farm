"""The `users` collection — the only place account documents are read or written.

Passwords are never stored, only a salted scrypt hash of them (Werkzeug ships
with Flask, so this costs no new dependency). A stolen dump of this collection
therefore does not hand the attacker anyone's password.
"""

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import current_app
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

import db

MIN_PASSWORD_LENGTH = 8

# Roles. There is no self-service route to SUPERADMIN — it is granted from the
# shell with `flask make-admin <email>`, so nobody can promote themselves
# through the web app however the forms are abused.
CUSTOMER = "customer"
SUPERADMIN = "superadmin"


class EmailTaken(Exception):
    """An account already exists for that address."""


class NoSuchAccount(Exception):
    """No account for that address."""


def collection():
    """The `users` collection, with its unique email index in place."""
    users = db.get_db()["users"]

    # Two registrations for the same address can both pass the "is it taken?"
    # read before either writes; the unique index is what actually stops the
    # second insert. create_index is idempotent but still a round trip, so only
    # the first call in this process pays for it.
    if not current_app.extensions.get("users_indexed"):
        users.create_index("email", unique=True)
        current_app.extensions["users_indexed"] = True

    return users


def normalize_email(email):
    """Addresses are matched case-insensitively, so they are stored folded."""
    return email.strip().lower()


# The login handle lives in the `email` field for every account: customers sign
# in with their address, staff with a plain username. One field means one unique
# index, so a customer can never register a handle that shadows a staff account —
# and registration requires a real email address, which a bare username is not.
normalize_handle = normalize_email


def problem_with(first_name, last_name, email, password, retype_password):
    """The first thing wrong with these details, or None if they are usable."""
    if not (first_name and last_name and email and password):
        return "Fill in every field to create your account."

    if "@" not in email or "." not in email.split("@")[-1]:
        return "That does not look like an email address."

    if len(password) < MIN_PASSWORD_LENGTH:
        return "Use at least {} characters for your password.".format(
            MIN_PASSWORD_LENGTH
        )

    if password != retype_password:
        return "The two passwords do not match."

    return None


def create(first_name, last_name, email, password):
    """Insert a new account and return it. Raises EmailTaken if the address is."""
    account = {
        "first_name": first_name,
        "last_name": last_name,
        "email": normalize_email(email),
        "password_hash": generate_password_hash(password),
        "role": CUSTOMER,  # never SUPERADMIN — see the note on the constants
        "created_at": datetime.now(timezone.utc),
    }

    try:
        result = collection().insert_one(account)
    except DuplicateKeyError:
        raise EmailTaken(email)

    account["_id"] = result.inserted_id
    return account


def _object_id(account_id):
    """The session carries the id as a string; Mongo matches on ObjectId."""
    if not account_id:
        return None
    try:
        return ObjectId(account_id)
    except InvalidId:
        return None


def set_role(email, role):
    """Grant or revoke a role by email. Used by the CLI, never by a view."""
    result = collection().update_one(
        {"email": normalize_email(email)}, {"$set": {"role": role}}
    )
    if result.matched_count == 0:
        raise NoSuchAccount(email)


def set_password(email, password):
    """Replace an account's password. Used by the CLI, never by a view.

    There is no web route to this: password *reset* by email is a flow this app
    does not have yet, and exposing a bare "set this password" endpoint would be
    an account-takeover hole waiting to be found.
    """
    result = collection().update_one(
        {"email": normalize_email(email)},
        {"$set": {"password_hash": generate_password_hash(password)}},
    )
    if result.matched_count == 0:
        raise NoSuchAccount(email)


def is_superadmin(account_id):
    """Ask the database, not the session.

    The session's copy of the role is a cosmetic hint for the templates; a
    cookie is the wrong thing to trust when deciding who may edit the catalogue,
    and it also goes stale the moment a role changes.
    """
    owner = _object_id(account_id)
    if owner is None:
        return False

    account = collection().find_one({"_id": owner}, {"role": 1})
    return bool(account) and account.get("role") == SUPERADMIN


def preferences(account_id):
    """The account's saved preferences, or {} if it has never saved any.

    Storage only — the dashboard owns which keys exist and what they default to.
    """
    owner = _object_id(account_id)
    if owner is None:
        return {}

    account = collection().find_one({"_id": owner}, {"preferences": 1})
    return (account or {}).get("preferences") or {}


def save_preferences(account_id, prefs):
    """Replace the account's preferences with `prefs`."""
    owner = _object_id(account_id)
    if owner is None:
        return

    collection().update_one({"_id": owner}, {"$set": {"preferences": prefs}})


def authenticate(email, password):
    """The account these credentials belong to, or None.

    An unknown address and a wrong password are indistinguishable to the caller,
    and take about the same time — otherwise the response time alone tells an
    attacker which addresses have accounts.
    """
    account = collection().find_one({"email": normalize_email(email)})

    if account is None:
        generate_password_hash(password)  # pay the hashing cost anyway
        return None

    if not check_password_hash(account["password_hash"], password):
        return None

    return account
