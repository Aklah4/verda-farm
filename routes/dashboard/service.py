"""Dashboard data: orders, headline figures and saved preferences.

Nothing here is invented any more. Order history is the account's real orders
from Mongo, and preferences are read from and written to the account document —
so anything the customer changes on screen is what the database holds, and what
the dashboard shows on the next visit and on any other device.

This module owns the *shape* of preferences (which toggles exist, what they
default to); `routes.auth.users` owns storing them.
"""

import order_service
from routes.auth import users
from routes.auth.session import account_id

# Checkbox name -> label. Drives both the form and the save, so the two can't
# drift apart.
TOGGLES = (
    ("reorder_reminders", "Reorder reminders"),
    ("newsletter", "Harvest newsletter"),
    ("sms_updates", "SMS delivery updates"),
)

DEFAULT_ADDRESS = "Km 12 Ibadan–Oyo Road"

DEFAULT_PREFERENCES = {
    "reorder_reminders": True,
    "newsletter": True,
    "sms_updates": False,
    "delivery_address": DEFAULT_ADDRESS,
}


def orders():
    """This account's real order history, newest first."""
    return order_service.for_account(account_id())


def stats(history):
    """The three figures across the top of the dashboard."""
    return {
        "orders": len(history),
        "spent": sum(order["total"] for order in history),
        "in_progress": sum(
            1 for order in history if order["status"] == order_service.PROCESSING
        ),
    }


def preferences():
    """Saved preferences, with defaults filling any gap.

    A brand-new account has saved nothing, and an account saved before a toggle
    existed has no value for it; the defaults cover both without a migration.
    """
    return {**DEFAULT_PREFERENCES, **users.preferences(account_id())}


def save_preferences(form):
    """Read the whole preferences form back into the account document.

    An unticked checkbox is simply absent from the submission, so membership in
    the form *is* the new value — reading it any other way would make a toggle
    impossible to turn off.
    """
    address = form.get("delivery_address", "").strip()

    users.save_preferences(
        account_id(),
        {
            **{name: name in form for name, _ in TOGGLES},
            "delivery_address": address or DEFAULT_ADDRESS,
        },
    )
