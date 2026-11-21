import pytest


@pytest.fixture
def deck(client, alice):
    res = client.post("/api/decks", json={"name": "Burn", "format": "modern"}, headers=alice)
    assert res.status_code == 201
    return res.get_json()


def add(client, headers, deck_id, card_id, quantity=1, board="main"):
    return client.post(
        f"/api/decks/{deck_id}/cards",
        json={"card_id": card_id, "quantity": quantity, "board": board},
        headers=headers,
    )


def test_create_validates(client, alice):
    res = client.post("/api/decks", json={"name": "", "format": "vintage-ish"}, headers=alice)
    assert res.status_code == 400
    assert set(res.get_json()["fields"]) == {"name", "format"}


def test_crud(client, alice, deck):
    assert client.get("/api/decks", headers=alice).get_json()["decks"][0]["name"] == "Burn"
    res = client.patch(f"/api/decks/{deck['id']}", json={"name": "Big Burn"}, headers=alice)
    assert res.get_json()["name"] == "Big Burn"
    assert res.get_json()["format"] == "modern"
    assert client.delete(f"/api/decks/{deck['id']}", headers=alice).status_code == 204
    assert client.get(f"/api/decks/{deck['id']}", headers=alice).status_code == 404


def test_owned_vs_missing(client, alice, deck, cached_cards):
    bolt, spear, dragon = (cached_cards[n] for n in ("Lightning Bolt", "Monastery Swiftspear", "Shivan Dragon"))
    client.post("/api/collection", json={"card_id": bolt, "quantity": 4}, headers=alice)
    client.post("/api/collection", json={"card_id": spear, "quantity": 1}, headers=alice)

    add(client, alice, deck["id"], bolt, 4)
    add(client, alice, deck["id"], spear, 4)
    body = add(client, alice, deck["id"], dragon, 2).get_json()

    rows = {r["card"]["name"]: r for r in body["cards"]}
    assert rows["Lightning Bolt"]["status"] == "owned"
    assert (rows["Monastery Swiftspear"]["have"], rows["Monastery Swiftspear"]["missing"]) == (1, 3)
    assert rows["Monastery Swiftspear"]["status"] == "partial"
    assert rows["Shivan Dragon"]["status"] == "missing"
    # 3 x 0.60 + 2 x 0.90
    assert body["totals"] == {"cards": 10, "owned": 5, "missing": 5, "percent_owned": 50, "missing_cost": 3.6}


def test_owned_copies_are_shared_between_main_and_sideboard(client, alice, deck, cached_cards):
    bolt = cached_cards["Lightning Bolt"]
    client.post("/api/collection", json={"card_id": bolt, "quantity": 3}, headers=alice)
    add(client, alice, deck["id"], bolt, 2, "main")
    body = add(client, alice, deck["id"], bolt, 2, "side").get_json()
    main, side = body["cards"]
    assert (main["board"], main["have"]) == ("main", 2)
    assert (side["board"], side["have"], side["missing"]) == ("side", 1, 1)


def test_adding_same_card_merges_and_moving_boards_merges(client, alice, deck, cached_cards):
    bolt = cached_cards["Lightning Bolt"]
    add(client, alice, deck["id"], bolt, 2)
    body = add(client, alice, deck["id"], bolt, 1).get_json()
    assert len(body["cards"]) == 1 and body["cards"][0]["need"] == 3

    side = add(client, alice, deck["id"], bolt, 1, "side").get_json()["cards"][1]
    body = client.patch(f"/api/decks/{deck['id']}/cards/{side['id']}", json={"board": "main"}, headers=alice).get_json()
    assert len(body["cards"]) == 1 and body["cards"][0]["need"] == 4


def test_update_and_remove_deck_card(client, alice, deck, cached_cards):
    row = add(client, alice, deck["id"], cached_cards["Shivan Dragon"]).get_json()["cards"][0]
    body = client.patch(f"/api/decks/{deck['id']}/cards/{row['id']}", json={"quantity": 3}, headers=alice).get_json()
    assert body["main_count"] == 3
    body = client.delete(f"/api/decks/{deck['id']}/cards/{row['id']}", headers=alice).get_json()
    assert body["cards"] == []


def test_other_users_cannot_touch_my_deck(client, alice, bob, deck, cached_cards):
    row = add(client, alice, deck["id"], cached_cards["Lightning Bolt"]).get_json()["cards"][0]
    url = f"/api/decks/{deck['id']}"
    assert client.get("/api/decks", headers=bob).get_json()["decks"] == []
    assert client.get(url, headers=bob).status_code == 403
    assert client.patch(url, json={"name": "mine now"}, headers=bob).status_code == 403
    assert client.delete(url, headers=bob).status_code == 403
    assert add(client, bob, deck["id"], cached_cards["Lightning Bolt"]).status_code == 403
    assert client.delete(f"{url}/cards/{row['id']}", headers=bob).status_code == 403


def test_deck_card_must_belong_to_the_deck_in_the_url(client, alice, deck, cached_cards):
    other = client.post("/api/decks", json={"name": "Other"}, headers=alice).get_json()
    row = add(client, alice, other["id"], cached_cards["Lightning Bolt"]).get_json()["cards"][0]
    res = client.delete(f"/api/decks/{deck['id']}/cards/{row['id']}", headers=alice)
    assert res.status_code == 404
