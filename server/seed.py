"""Create a demo user with a small collection and two decks.

Usage:  python3 seed.py
Login:  demo / password123

Safe to re-run: it replaces only the demo account. Other users are untouched.

With SCRYFALL_MODE=fake this runs offline. With the live API it makes a few
throttled Scryfall searches to fill the card cache.
"""

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import CollectionItem, Deck, DeckCard, User  # noqa: E402
from app.scryfall import search_cards  # noqa: E402


def find(name):
    cards, _, _ = search_cards(f'!"{name}"') if _live() else search_cards(name)
    exact = [c for c in cards if c.name.lower() == name.lower()]
    if not exact:
        raise SystemExit(f"Could not find {name!r} on Scryfall")
    return exact[0]


def _live():
    from flask import current_app

    return current_app.config["SCRYFALL_MODE"] != "fake"


DEMO_USERNAME = "demo"
DEMO_EMAIL = "demo@deckforge.dev"


def _remove_old_demo():
    old = User.query.filter((User.username == DEMO_USERNAME) | (User.email == DEMO_EMAIL)).all()
    for user in old:
        db.session.delete(user)  # cascades to the demo's collection and decks
    db.session.commit()


def seed(app):
    with app.app_context():
        db.create_all()  # no-op when `flask db upgrade` already made the tables
        _remove_old_demo()

        demo = User(username=DEMO_USERNAME, email=DEMO_EMAIL)
        demo.set_password("password123")
        db.session.add(demo)
        db.session.flush()

        owned = {
            "Lightning Bolt": 4,
            "Monastery Swiftspear": 2,
            "Goblin Guide": 1,
            "Mountain": 20,
            "Counterspell": 2,
            "Brainstorm": 3,
            "Island": 12,
            "Sol Ring": 1,
        }
        for name, qty in owned.items():
            db.session.add(CollectionItem(user=demo, card=find(name), quantity=qty))

        burn = Deck(user=demo, name="Mono-Red Burn", format="casual",
                    description="Fast red aggro: creatures early, bolts to finish.")
        db.session.add(burn)
        for name, qty, board in [
            ("Lightning Bolt", 4, "main"),
            ("Monastery Swiftspear", 4, "main"),
            ("Goblin Guide", 4, "main"),
            ("Shivan Dragon", 2, "main"),
            ("Mountain", 20, "main"),
            ("Thoughtseize", 2, "side"),
        ]:
            db.session.add(DeckCard(deck=burn, card=find(name), quantity=qty, board=board))

        tempo = Deck(user=demo, name="Blue Tempo", format="casual",
                     description="Counter what matters, draw the rest.")
        db.session.add(tempo)
        for name, qty in [("Counterspell", 4), ("Brainstorm", 4), ("Island", 16)]:
            db.session.add(DeckCard(deck=tempo, card=find(name), quantity=qty, board="main"))

        db.session.commit()
        print("Seeded demo user (demo / password123) with 8 collection entries and 2 decks.")


if __name__ == "__main__":
    seed(create_app())
