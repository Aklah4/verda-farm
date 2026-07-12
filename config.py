"""Configuration, read from the environment with sensible defaults.

The design exposes accent / hero layout / WhatsApp as component props; here they
become app config so the same knobs are available without touching templates.
"""

import os

from dotenv import load_dotenv

# Read .env before the class body evaluates os.environ. Real environment
# variables win over the file, so deployments can override without editing it.
load_dotenv()

DEV_SECRET_KEY = "verda-farm-dev-secret-change-me"


class Config:
    # A missing SECRET_KEY is fatal in production — see create_app.
    SECRET_KEY = os.environ.get("SECRET_KEY", DEV_SECRET_KEY)
    ENV = os.environ.get("VERDA_ENV", "development")

    # How many reverse proxies sit in front of this app (Nginx, Render, Fly,
    # Cloudflare...). 0 means we are serving directly.
    #
    # This is deliberately opt-in and deliberately a *count*, not a boolean.
    # X-Forwarded-For is just a header: any client can send one. Trusting it
    # when nothing is in front of us would let an attacker forge a new source
    # address on every request and walk straight through the rate limiter. So
    # the header is honoured only when you tell us a proxy is really there, and
    # only for as many hops as you say — anything beyond that is the client's
    # own invention and gets discarded.
    TRUST_PROXY = int(os.environ.get("TRUST_PROXY", "0"))

    # The session cookie is the signed-in visitor — and, for the admin, the keys
    # to the catalogue. Harden it.
    #
    # HttpOnly: script cannot read it, so an injected <script> cannot steal a
    #   session. (Flask's default, pinned here so it cannot drift.)
    # SameSite=Lax: it is not attached to cross-site POSTs, which blunts CSRF
    #   even where a token is somehow missed.
    # Secure: only ever sent over HTTPS. Off in development, where there is no
    #   TLS and setting it would stop sign-in working at all on localhost.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = ENV == "production"

    ACCENT = os.environ.get("VERDA_ACCENT", "#2E7D4E")
    HERO_LAYOUT = os.environ.get("VERDA_HERO", "split")  # "split" | "centered"
    SHOW_WHATSAPP = os.environ.get("VERDA_WHATSAPP", "1") != "0"

    # MongoDB Atlas. The full driver string from Atlas, password and all — paste
    # it into MONGO_URI in .env, which is gitignored precisely because of that.
    MONGO_URI = os.environ.get("MONGO_URI", "")
    MONGO_DB = os.environ.get("MONGO_DB", "verda")

    # Fail a dead connection fast instead of hanging a request for 30s.
    MONGO_TIMEOUT_MS = int(os.environ.get("MONGO_TIMEOUT_MS", "5000"))

    # The bootstrap superadmin, created by `flask seed-admin`.
    #
    # The admin signs in with a plain username ("admin"), not an email — staff do
    # not need a mailbox to manage a catalogue. It shares the accounts collection
    # with customers, and the same unique index, so the username can never
    # collide with a customer: registration demands a real email address, and
    # "admin" is not one.
    #
    # Read at this command and nowhere else: no view, template or request path
    # ever touches these, so the password cannot leak into a page. It is also
    # never used to *authenticate* — seeding hashes it into the account like any
    # other password, and sign-in checks the hash. Changing it in .env later does
    # not change the account's password (pass --reset-password to do that).
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
    ADMIN_FIRST_NAME = os.environ.get("ADMIN_FIRST_NAME", "Admin")
    ADMIN_LAST_NAME = os.environ.get("ADMIN_LAST_NAME", "User")

    # Cloudinary, for product images. Either paste the single CLOUDINARY_URL
    # from the dashboard ("cloudinary://key:secret@cloud"), or set the three
    # parts separately — media.py accepts whichever is present. The app runs
    # without these; only image upload is disabled until they are set.
    CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "")
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")

    # Reject an oversized upload at the door rather than streaming it to
    # Cloudinary. Flask raises 413 past this, which app.py turns into a message.
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "6")) * 1024 * 1024

    DELIVERY_FEE = 3500

    # Upper bound on a single cart line. Without it a hand-crafted POST can push
    # the quantity to nine digits and the order total into the trillions.
    MAX_LINE_QTY = 999
