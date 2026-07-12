"""Product images, hosted on Cloudinary.

The credentials are read from config, never hard-coded: either the single
CLOUDINARY_URL from the dashboard, or the three parts separately.

Cloudinary is optional. Until the keys are in .env, `is_configured()` is False,
the admin form says so and hides the file input, and products save without an
image — the storefront falls back to the colour swatch it has always drawn. That
way the whole admin area is usable today and image upload lights up the moment
you paste the keys in.
"""

from urllib.parse import urlparse

import cloudinary
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from flask import current_app

# Uploads are filed by kind, so the Cloudinary media library stays sorted and a
# stray upload elsewhere is obvious.
FOLDER = "verda/products"
HERO_FOLDER = "verda/hero"

ALLOWED_EXTENSIONS = ("png", "jpg", "jpeg", "webp", "avif")


class NotConfigured(Exception):
    """Cloudinary credentials are absent."""


class UploadFailed(Exception):
    """Cloudinary rejected the file, or could not be reached."""


def _credentials():
    """Cloud name, key and secret — from CLOUDINARY_URL or the three vars."""
    config = current_app.config

    url = config["CLOUDINARY_URL"]
    if url:
        # cloudinary://<api_key>:<api_secret>@<cloud_name>
        parsed = urlparse(url)
        if parsed.username and parsed.password and parsed.hostname:
            return {
                "cloud_name": parsed.hostname,
                "api_key": parsed.username,
                "api_secret": parsed.password,
            }

    if config["CLOUDINARY_CLOUD_NAME"] and config["CLOUDINARY_API_SECRET"]:
        return {
            "cloud_name": config["CLOUDINARY_CLOUD_NAME"],
            "api_key": config["CLOUDINARY_API_KEY"],
            "api_secret": config["CLOUDINARY_API_SECRET"],
        }

    return None


def is_configured():
    return _credentials() is not None


def _connect():
    credentials = _credentials()
    if credentials is None:
        raise NotConfigured(
            "Cloudinary is not configured. Add CLOUDINARY_URL to .env "
            "(Cloudinary dashboard -> API Keys)."
        )

    # secure=True so the URLs we store and serve are https.
    cloudinary.config(secure=True, **credentials)


def has_allowed_extension(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def upload(file_storage, slug, folder=FOLDER):
    """Upload one image and return {"url", "id"}.

    `slug` becomes the public id, so re-uploading an image for the same product
    (or hero tile) replaces the old one instead of littering the account with
    orphans.
    """
    _connect()

    try:
        result = cloudinary.uploader.upload(
            file_storage,
            folder=folder,
            public_id=slug,
            overwrite=True,
            resource_type="image",
            # Cap the stored image: a 12MP phone photo would otherwise be served
            # to every shopper at full size.
            transformation=[{"width": 1400, "height": 1400, "crop": "limit"}],
        )
    except CloudinaryError as exc:
        raise UploadFailed(str(exc))

    return {"url": result["secure_url"], "id": result["public_id"]}


def delete(public_id):
    """Best-effort removal. A left-behind image must never block a delete."""
    if not public_id or not is_configured():
        return

    try:
        _connect()
        cloudinary.uploader.destroy(public_id, resource_type="image")
    except (CloudinaryError, NotConfigured):
        current_app.logger.exception("could not delete image %s", public_id)
