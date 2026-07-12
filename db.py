"""MongoDB Atlas connection.

`MONGO_URI` is the driver string exactly as Atlas gives it to you, password
included, so nothing here assembles credentials — it just hands the string to
the driver. Keep it in .env (gitignored); it is the whole secret.

One `MongoClient` per process, created on first use and reused for the life of
the app — the client owns a connection pool, so building a fresh one per request
would throw the pool away and re-do the TLS and SRV handshakes every time.

Nothing connects at import or at boot. The storefront still runs with Mongo
unconfigured; the first call to `get_db()` is what reaches out to the cluster.
"""

import certifi
from flask import current_app
from pymongo import MongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError


def get_client():
    """The process-wide client, built on first use."""
    client = current_app.extensions.get("mongo")
    if client is not None:
        return client

    uri = current_app.config["MONGO_URI"]
    if not uri:
        raise RuntimeError(
            "MONGO_URI is not set. Copy the driver connection string from Atlas "
            "(Connect -> Drivers) into .env."
        )

    client = MongoClient(
        uri,
        serverSelectionTimeoutMS=current_app.config["MONGO_TIMEOUT_MS"],
        # Atlas is TLS-only. Point at certifi's bundle rather than the system
        # store, which on Windows and macOS often lacks the CA Atlas presents.
        tlsCAFile=certifi.where(),
    )

    current_app.extensions["mongo"] = client
    return client


def get_db():
    """The `verda` database (name from MONGO_DB)."""
    return get_client()[current_app.config["MONGO_DB"]]


def ping():
    """Round-trip the cluster. Raises if it is unreachable or auth fails."""
    get_client().admin.command("ping")


def init_app(app):
    app.extensions.setdefault("mongo", None)

    @app.cli.command("db-ping")
    def db_ping():
        """Check the Atlas connection and list collections."""
        try:
            ping()
            database = get_db()
            names = database.list_collection_names()
        except RuntimeError as exc:  # not configured — the message says what to fix
            raise SystemExit("not connected: {}".format(exc))
        except OperationFailure as exc:  # reached Atlas, but it said no
            raise SystemExit(
                "not connected: authentication failed ({}). Check the username and "
                "password in MONGO_URI against Atlas -> Database Access.".format(
                    exc.details.get("errmsg", exc)
                )
            )
        except ServerSelectionTimeoutError as exc:  # never reached Atlas
            raise SystemExit(
                "not connected: could not reach the cluster within {}ms. The usual "
                "cause is this machine's IP missing from Atlas -> Network Access.\n"
                "{}".format(app.config["MONGO_TIMEOUT_MS"], exc)
            )

        print("connected to '{}'".format(database.name))
        print("collections: {}".format(", ".join(names) if names else "(none yet)"))
