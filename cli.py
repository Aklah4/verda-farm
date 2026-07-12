"""Shell commands: `flask seed-admin`, `flask make-admin`, `flask seed-products`.

Granting superadmin lives here, and only here. There is deliberately no route,
form or sign-up flag that can do it: becoming an admin requires shell access to
the server (or the .env it reads), so an attacker who owns nothing but a browser
cannot reach it.
"""

import click
from flask import current_app
from pymongo.errors import PyMongoError

import product_service
from data import SEED_PRODUCTS
from routes.auth import users


def register_cli(app):
    @app.cli.command("seed-admin")
    @click.option(
        "--reset-password",
        is_flag=True,
        help="Also reset an existing account's password to ADMIN_PASSWORD.",
    )
    def seed_admin(reset_password):
        """Create the superadmin described by ADMIN_USERNAME / ADMIN_PASSWORD in .env.

        Idempotent: run it on every deploy. An account that already exists is
        promoted, not recreated, and its password is left alone unless you ask
        for it to be reset — otherwise a stale .env would silently overwrite a
        password the admin had since changed.
        """
        config = current_app.config
        username = config["ADMIN_USERNAME"].strip()
        password = config["ADMIN_PASSWORD"]

        if not username:
            raise SystemExit(
                "ADMIN_USERNAME is not set. Add ADMIN_USERNAME and ADMIN_PASSWORD "
                "to .env (see .env.example), then run this again."
            )

        try:
            existing = users.collection().find_one(
                {"email": users.normalize_handle(username)}
            )

            if existing is None:
                # Only a brand-new account needs the password; promoting an
                # existing one does not, which is why this check lives here.
                if len(password) < users.MIN_PASSWORD_LENGTH:
                    raise SystemExit(
                        "ADMIN_PASSWORD must be at least {} characters to create "
                        "'{}'.".format(users.MIN_PASSWORD_LENGTH, username)
                    )

                users.create(
                    config["ADMIN_FIRST_NAME"],
                    config["ADMIN_LAST_NAME"],
                    username,
                    password,
                )
                users.set_role(username, users.SUPERADMIN)
                # The password is never echoed — it is in .env, and that is the
                # only place it should ever be readable.
                click.echo("created '{}' and granted superadmin.".format(username))
                return

            users.set_role(username, users.SUPERADMIN)
            click.echo("'{}' already existed - granted superadmin.".format(username))

            if reset_password:
                if len(password) < users.MIN_PASSWORD_LENGTH:
                    raise SystemExit(
                        "ADMIN_PASSWORD must be at least {} characters to reset "
                        "it.".format(users.MIN_PASSWORD_LENGTH)
                    )
                users.set_password(username, password)
                click.echo("password reset to ADMIN_PASSWORD.")
            elif password:
                click.echo(
                    "password left unchanged. Pass --reset-password to overwrite it "
                    "with ADMIN_PASSWORD."
                )

        except PyMongoError as exc:
            raise SystemExit("could not reach the database: {}".format(exc))

        click.echo("/admin/login is open to them.")
    @app.cli.command("make-admin")
    @click.argument("email")
    def make_admin(email):
        """Grant superadmin to the account with EMAIL."""
        try:
            users.set_role(email, users.SUPERADMIN)
        except users.NoSuchAccount:
            raise SystemExit(
                "no account for {}. They must register on the site first, "
                "then run this again.".format(email)
            )
        except PyMongoError as exc:
            raise SystemExit("could not reach the database: {}".format(exc))

        click.echo("{} is now a superadmin. /admin is open to them.".format(email))

    @app.cli.command("revoke-admin")
    @click.argument("email")
    def revoke_admin(email):
        """Return the account with EMAIL to an ordinary customer."""
        try:
            users.set_role(email, users.CUSTOMER)
        except users.NoSuchAccount:
            raise SystemExit("no account for {}.".format(email))
        except PyMongoError as exc:
            raise SystemExit("could not reach the database: {}".format(exc))

        click.echo("{} is now an ordinary customer.".format(email))

    @app.cli.command("seed-products")
    def seed_products():
        """Load the starting catalogue into an empty products collection."""
        try:
            added = product_service.seed(SEED_PRODUCTS)
            total = len(product_service.all_products())
        except PyMongoError as exc:
            raise SystemExit("could not reach the database: {}".format(exc))

        if added:
            click.echo("added {} product(s).".format(added))
        else:
            # ASCII only: the Windows console codepage mangles an em dash.
            click.echo("nothing to add - every seed product is already there.")

        click.echo("catalogue now holds {} product(s).".format(total))
