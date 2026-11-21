"""Thin client for the Scryfall API.

Scryfall rules we follow (https://scryfall.com/docs/api):
- Send a User-Agent and an Accept header on every request.
- /cards/search is limited to 2 requests per second, so calls are throttled.
- Never ignore HTTP 429: surface it so the UI can ask the user to try again.
"""

import json
import threading
import time
import uuid
from datetime import timedelta

import requests
from flask import current_app

from .extensions import db
from .models import Card, utcnow

_lock = threading.Lock()
_last_call = 0.0
SEARCH_INTERVAL = 0.5  # seconds between search calls (2/sec limit)


class ScryfallError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def _throttle(interval):
    global _last_call
    with _lock:
        wait = interval - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def _get(path, params=None, interval=0.1):
    cfg = current_app.config
    if not cfg.get("TESTING"):
        _throttle(interval)
    try:
        resp = requests.get(
            f"{cfg['SCRYFALL_BASE_URL']}{path}",
            params=params,
            headers={"User-Agent": cfg["SCRYFALL_USER_AGENT"], "Accept": "application/json"},
            timeout=8,
        )
    except requests.RequestException as exc:
        raise ScryfallError(502, "Could not reach Scryfall. Try again in a moment.") from exc

    if resp.status_code == 429:
        raise ScryfallError(503, "Scryfall is busy right now. Wait a few seconds and try again.")
    if resp.status_code == 404:
        return None
    if resp.status_code >= 400:
        raise ScryfallError(502, "Scryfall returned an error. Try a different search.")
    return resp.json()


def normalize(raw):
    """Turn a Scryfall card object into the fields we store."""
    images = raw.get("image_uris")
    if not images and raw.get("card_faces"):
        images = raw["card_faces"][0].get("image_uris")  # double-faced cards
    images = images or {}

    mana_cost = raw.get("mana_cost")
    if mana_cost is None and raw.get("card_faces"):
        mana_cost = raw["card_faces"][0].get("mana_cost")

    colors = raw.get("colors")
    if colors is None:
        colors = raw.get("color_identity", [])

    price = (raw.get("prices") or {}).get("usd")
    return {
        "id": raw["id"],
        "name": raw["name"],
        "set_code": raw.get("set"),
        "set_name": raw.get("set_name"),
        "collector_number": raw.get("collector_number"),
        "rarity": raw.get("rarity"),
        "type_line": raw.get("type_line"),
        "mana_cost": mana_cost or "",
        "cmc": raw.get("cmc"),
        "colors": json.dumps(colors),
        "image_url": images.get("normal"),
        "image_small": images.get("small"),
        "price_usd": float(price) if price else None,
        "scryfall_uri": raw.get("scryfall_uri"),
    }


def upsert_cards(card_dicts):
    """Insert new cards or refresh cached ones. Returns Card rows in the same order."""
    ids = [c["id"] for c in card_dicts]
    existing = {c.id: c for c in Card.query.filter(Card.id.in_(ids)).all()} if ids else {}
    rows = []
    for data in card_dicts:
        card = existing.get(data["id"])
        if card is None:
            card = Card(**data)
            db.session.add(card)
        else:
            for key, value in data.items():
                setattr(card, key, value)
            card.updated_at = utcnow()
        rows.append(card)
    db.session.commit()
    return rows


def search_cards(query, page=1):
    if current_app.config["SCRYFALL_MODE"] == "fake":
        return _fake_search(query)
    data = _get(
        "/cards/search",
        {"q": query, "page": page, "unique": "cards", "order": "name"},
        interval=SEARCH_INTERVAL,
    )
    if data is None:  # Scryfall answers 404 when nothing matches
        return [], False, 0
    cards = upsert_cards([normalize(c) for c in data.get("data", [])])
    return cards, data.get("has_more", False), data.get("total_cards", len(cards))


def get_card(card_id):
    """Return a cached card, fetching or refreshing it from Scryfall when needed."""
    card = db.session.get(Card, card_id)
    max_age = timedelta(hours=current_app.config["CARD_CACHE_HOURS"])
    if card and (utcnow() - card.updated_at) < max_age:
        return card
    if current_app.config["SCRYFALL_MODE"] == "fake":
        return card
    try:
        raw = _get(f"/cards/{card_id}")
    except ScryfallError:
        if card:  # stale is better than nothing
            return card
        raise
    if raw is None:
        return card
    return upsert_cards([normalize(raw)])[0]


# ---------------------------------------------------------------------------
# Offline mode (SCRYFALL_MODE=fake): a few well-known cards, no images.
# ---------------------------------------------------------------------------
_FAKE = [
    ("Lightning Bolt", "R", "Instant", ["R"], 1, "common", 1.50),
    ("Counterspell", "UU", "Instant", ["U"], 2, "common", 1.25),
    ("Llanowar Elves", "G", "Creature — Elf Druid", ["G"], 1, "common", 0.30),
    ("Swords to Plowshares", "W", "Instant", ["W"], 1, "uncommon", 2.10),
    ("Dark Ritual", "B", "Instant", ["B"], 1, "common", 0.75),
    ("Sol Ring", "1", "Artifact", [], 1, "uncommon", 1.80),
    ("Serra Angel", "3WW", "Creature — Angel", ["W"], 5, "uncommon", 0.25),
    ("Shivan Dragon", "4RR", "Creature — Dragon", ["R"], 6, "rare", 0.90),
    ("Giant Growth", "G", "Instant", ["G"], 1, "common", 0.20),
    ("Brainstorm", "U", "Instant", ["U"], 1, "common", 1.10),
    ("Thoughtseize", "B", "Sorcery", ["B"], 1, "rare", 12.40),
    ("Goblin Guide", "R", "Creature — Goblin Scout", ["R"], 1, "rare", 3.20),
    ("Monastery Swiftspear", "R", "Creature — Human Monk", ["R"], 1, "uncommon", 0.60),
    ("Mountain", "", "Basic Land — Mountain", [], 0, "common", 0.05),
    ("Island", "", "Basic Land — Island", [], 0, "common", 0.05),
    ("Forest", "", "Basic Land — Forest", [], 0, "common", 0.05),
]


def _fake_raw(name, cost, type_line, colors, cmc, rarity, price):
    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"deckforge-fake/{name}")),
        "name": name,
        "set": "dfk",
        "set_name": "Deckforge Offline Set",
        "collector_number": "1",
        "rarity": rarity,
        "type_line": type_line,
        "mana_cost": "".join(f"{{{c}}}" for c in cost),
        "cmc": cmc,
        "colors": colors,
        "prices": {"usd": f"{price:.2f}"},
        "scryfall_uri": None,
    }


def _fake_search(query):
    q = query.lower()
    matches = [_fake_raw(*row) for row in _FAKE if q in row[0].lower() or q in row[2].lower()]
    cards = upsert_cards([normalize(m) for m in matches])
    return cards, False, len(cards)
