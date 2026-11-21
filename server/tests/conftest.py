import pytest
import responses

from app import create_app
from app.config import TestConfig
from app.extensions import db

SCRYFALL = "https://api.scryfall.com"


def make_card(card_id, name, price="1.00", **extra):
    """A minimal Scryfall card object."""
    card = {
        "id": card_id,
        "name": name,
        "set": "tst",
        "set_name": "Test Set",
        "collector_number": "1",
        "rarity": "common",
        "type_line": "Instant",
        "mana_cost": "{R}",
        "cmc": 1,
        "colors": ["R"],
        "image_uris": {"normal": f"https://img.test/{card_id}.jpg", "small": f"https://img.test/{card_id}-s.jpg"},
        "prices": {"usd": price},
        "scryfall_uri": f"https://scryfall.com/card/tst/{card_id}",
    }
    card.update(extra)
    return card


BOLT = make_card("bolt-0000-0000-0000-000000000001", "Lightning Bolt", "1.50")
SPEAR = make_card("spear-000-0000-0000-000000000002", "Monastery Swiftspear", "0.60")
DRAGON = make_card("dragon-00-0000-0000-000000000003", "Shivan Dragon", "0.90")


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def mock_scryfall():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.get(
            f"{SCRYFALL}/cards/search",
            json={"object": "list", "total_cards": 3, "has_more": False, "data": [BOLT, SPEAR, DRAGON]},
        )
        for card in (BOLT, SPEAR, DRAGON):
            rsps.get(f"{SCRYFALL}/cards/{card['id']}", json=card)
        yield rsps


def signup(client, username="alice", email=None, password="password123"):
    res = client.post(
        "/api/signup",
        json={"username": username, "email": email or f"{username}@test.dev", "password": password},
    )
    assert res.status_code == 201, res.get_json()
    return res.get_json()["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def alice(client):
    return auth(signup(client, "alice"))


@pytest.fixture
def bob(client):
    return auth(signup(client, "bob"))


@pytest.fixture
def cached_cards(client, alice, mock_scryfall):
    """Run one search so the three test cards are in the local cache."""
    res = client.get("/api/cards/search?q=red", headers=alice)
    assert res.status_code == 200
    return {c["name"]: c["id"] for c in res.get_json()["cards"]}
