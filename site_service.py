"""Editable site content — currently the home page hero collage.

The hero was three colour tiles hardcoded into home.html, so changing the shop
window meant editing a template. The tiles now live in a single `settings`
document that the admin edits and the home page reads.

There are exactly three slots because the collage's layout is three: one tall
tile beside two stacked ones. Adding a fourth is a CSS change, not a data one,
so the count is fixed here rather than left open.

Each tile keeps its swatch colour even once it has a photo — the colour is what
shows while the image loads, and what it falls back to if the tile is cleared.
"""

from flask import current_app

import db

SETTINGS_ID = "site"
HERO_SLOTS = 3

# The collage exactly as the design shipped it. A tile the admin has never
# touched renders from this, so a fresh database still looks like the design.
DEFAULT_HERO = [
    {"label": "Herbanero", "tone": "#3e9c5f", "ink": "#0e2e18",
     "image_url": None, "image_id": None},
    {"label": "Tomatoes", "tone": "#d8583f", "ink": "#3f120a",
     "image_url": None, "image_id": None},
    {"label": "Plantain", "tone": "#e9dfa0", "ink": "#524711",
     "image_url": None, "image_id": None},
]


def collection():
    return db.get_db()["settings"]


def _document():
    return collection().find_one({"_id": SETTINGS_ID}) or {}


def hero_tiles():
    """The three tiles, defaults filling anything never saved.

    Read on every home-page render, so it is one query and no joins.
    """
    saved = _document().get("hero") or []

    tiles = []
    for slot in range(HERO_SLOTS):
        default = DEFAULT_HERO[slot]
        tile = saved[slot] if slot < len(saved) else {}
        tiles.append({**default, **tile, "slot": slot})

    return tiles


def save_hero(tiles):
    """Replace the whole collage. `tiles` is a list of HERO_SLOTS dicts."""
    collection().update_one(
        {"_id": SETTINGS_ID},
        {"$set": {"hero": tiles}},
        upsert=True,  # the settings document is created on first save
    )


def hero_public_id(slot):
    """Stable Cloudinary id per slot, so re-uploading a tile replaces its image
    rather than accumulating one file per edit."""
    return "hero-{}".format(slot + 1)
