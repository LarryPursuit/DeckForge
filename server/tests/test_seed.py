from app.models import Deck, User

import seed

from .conftest import signup


def test_seed_replaces_only_the_demo_account(app, client, monkeypatch):
    monkeypatch.setitem(app.config, "SCRYFALL_MODE", "fake")
    signup(client, "alice")

    seed.seed(app)
    seed.seed(app)  # running twice must not duplicate the demo data

    assert User.query.filter_by(username="alice").one()
    demo = User.query.filter_by(username="demo").one()
    assert len(demo.collection_items) == 8
    assert Deck.query.filter_by(user_id=demo.id).count() == 2
