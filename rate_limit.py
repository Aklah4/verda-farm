"""Login throttling — the thing that turns a guessable password into a slow one.

Failures are counted in Mongo, not in process memory. Memory would be wrong
twice over: the dev server's reloader wipes it on every edit, and a production
deployment runs several workers, so an attacker would simply get N attempts per
worker and the count would never add up.

Two independent limits, and either one trips:

  per account — 5 failures in 15 minutes locks *that username* out. This is the
      one that stops someone grinding a password list against a single account,
      however many machines they spread it across.

  per IP — 20 failures in 15 minutes locks *that address* out. This catches one
      machine spraying one password across many usernames, which the per-account
      limit alone would never see.

Only failures are counted, and a successful sign-in clears the counters, so a
legitimate person who fat-fingers their password twice and then gets it right is
never inconvenienced.
"""

from datetime import datetime, timedelta, timezone

from flask import current_app

import db

# How long a failure is remembered, and how many are tolerated inside it.
WINDOW = timedelta(minutes=15)
MAX_PER_ACCOUNT = 5
MAX_PER_IP = 20

# Mongo sweeps expired documents on a ~60s timer, so this is housekeeping, not
# the limit itself — the window above is enforced by the query.
_TTL_SECONDS = int(timedelta(hours=24).total_seconds())


def collection():
    attempts = db.get_db()["login_attempts"]

    if not current_app.extensions.get("attempts_indexed"):
        # Mongo deletes the documents itself; nothing has to sweep them.
        attempts.create_index("at", expireAfterSeconds=_TTL_SECONDS)
        attempts.create_index([("key", 1), ("at", 1)])
        current_app.extensions["attempts_indexed"] = True

    return attempts


def _account_key(username):
    return "account:{}".format((username or "").strip().lower())


def _ip_key(address):
    return "ip:{}".format(address or "unknown")


def _failures_since(key, since):
    return collection().count_documents({"key": key, "at": {"$gte": since}})


def _oldest_failure(key, since):
    doc = collection().find_one({"key": key, "at": {"$gte": since}}, sort=[("at", 1)])
    return doc["at"] if doc else None


def _locked_for(key, limit, since):
    """Seconds until `key` may try again, or 0 if it may try now."""
    if _failures_since(key, since) < limit:
        return 0

    # The lock lifts when the oldest failure in the window ages out of it.
    oldest = _oldest_failure(key, since)
    if oldest is None:
        return 0

    if oldest.tzinfo is None:  # Mongo hands datetimes back naive
        oldest = oldest.replace(tzinfo=timezone.utc)

    remaining = (oldest + WINDOW) - datetime.now(timezone.utc)
    return max(0, int(remaining.total_seconds()))


def locked_out(username, address):
    """Seconds this attempt must wait, or 0 if it may proceed."""
    since = datetime.now(timezone.utc) - WINDOW

    return max(
        _locked_for(_account_key(username), MAX_PER_ACCOUNT, since),
        _locked_for(_ip_key(address), MAX_PER_IP, since),
    )


def record_failure(username, address):
    """Count one failed sign-in against both the account and the address."""
    now = datetime.now(timezone.utc)
    collection().insert_many(
        [
            {"key": _account_key(username), "at": now},
            {"key": _ip_key(address), "at": now},
        ]
    )


def clear(username, address):
    """Forget this account's and address's failures — they just signed in."""
    collection().delete_many(
        {"key": {"$in": [_account_key(username), _ip_key(address)]}}
    )


def wait_message(seconds):
    """How long to wait, in words a person can act on."""
    if seconds >= 120:
        return "about {} minutes".format(round(seconds / 60))
    if seconds > 60:
        return "about a minute"
    return "{} seconds".format(max(1, seconds))
