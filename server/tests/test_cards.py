import responses

from app.models import Card

from .conftest import BOLT, SCRYFALL


def test_search_caches_cards_and_sends_required_headers(client, alice, mock_scryfall, app):
    res = client.get("/api/cards/search?q=bolt", headers=alice)
    body = res.get_json()
    assert res.status_code == 200
    assert [c["name"] for c in body["cards"]] == ["Lightning Bolt", "Monastery Swiftspear", "Shivan Dragon"]
    assert body["cards"][0]["owned"] == 0
    assert body["cards"][0]["price_usd"] == 1.5
    assert Card.query.count() == 3

    sent = mock_scryfall.calls[0].request.headers
    assert sent["User-Agent"].startswith("Deckforge")
    assert sent["Accept"] == "application/json"


def test_search_needs_two_characters(client, alice):
    assert client.get("/api/cards/search?q=a", headers=alice).status_code == 400


def test_search_with_no_results(client, alice):
    with responses.RequestsMock() as rsps:
        rsps.get(f"{SCRYFALL}/cards/search", status=404, json={"object": "error"})
        res = client.get("/api/cards/search?q=zzzz", headers=alice)
    assert res.status_code == 200
    assert res.get_json()["cards"] == []


def test_search_rate_limited_is_reported_not_ignored(client, alice):
    with responses.RequestsMock() as rsps:
        rsps.get(f"{SCRYFALL}/cards/search", status=429, json={"object": "error"})
        res = client.get("/api/cards/search?q=bolt", headers=alice)
    assert res.status_code == 503
    assert "busy" in res.get_json()["error"]


def test_double_faced_card_uses_front_face_image(client, alice):
    dfc = {**BOLT, "id": "dfc-0000", "name": "Delver of Secrets // Insectile Aberration"}
    del dfc["image_uris"]
    dfc["mana_cost"] = None
    dfc["card_faces"] = [
        {"image_uris": {"normal": "https://img.test/front.jpg", "small": "s"}, "mana_cost": "{U}"},
        {"image_uris": {"normal": "https://img.test/back.jpg", "small": "s"}, "mana_cost": ""},
    ]
    with responses.RequestsMock() as rsps:
        rsps.get(f"{SCRYFALL}/cards/search", json={"data": [dfc], "has_more": False, "total_cards": 1})
        card = client.get("/api/cards/search?q=delver", headers=alice).get_json()["cards"][0]
    assert card["image_url"] == "https://img.test/front.jpg"
    assert card["mana_cost"] == "{U}"


def test_show_uses_cache_without_calling_scryfall(client, alice, cached_cards):
    with responses.RequestsMock() as rsps:  # any HTTP call here would fail the test
        res = client.get(f"/api/cards/{cached_cards['Lightning Bolt']}", headers=alice)
        assert len(rsps.calls) == 0
    assert res.status_code == 200
    assert res.get_json()["name"] == "Lightning Bolt"


def test_search_reports_the_page_it_actually_used(client, alice, mock_scryfall):
    res = client.get("/api/cards/search?q=bolt&page=0", headers=alice)
    assert res.get_json()["page"] == 1
