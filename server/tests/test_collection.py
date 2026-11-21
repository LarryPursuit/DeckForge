def test_add_card_then_add_again_increases_quantity(client, alice, cached_cards):
    bolt = cached_cards["Lightning Bolt"]
    first = client.post("/api/collection", json={"card_id": bolt, "quantity": 2}, headers=alice)
    again = client.post("/api/collection", json={"card_id": bolt}, headers=alice)
    assert first.status_code == 201
    assert again.status_code == 200
    assert again.get_json()["quantity"] == 3

    listing = client.get("/api/collection", headers=alice).get_json()
    assert listing["unique_cards"] == 1
    assert listing["total_cards"] == 3
    assert listing["estimated_value"] == 4.5


def test_add_unknown_card_is_404(client, alice, mock_scryfall):
    mock_scryfall.get("https://api.scryfall.com/cards/00000000-0000-4000-8000-00000000dead", status=404, json={"object": "error"})
    res = client.post("/api/collection", json={"card_id": "00000000-0000-4000-8000-00000000dead"}, headers=alice)
    assert res.status_code == 404


def test_update_and_delete_item(client, alice, cached_cards):
    item = client.post("/api/collection", json={"card_id": cached_cards["Shivan Dragon"]}, headers=alice).get_json()
    res = client.patch(f"/api/collection/{item['id']}", json={"quantity": 4}, headers=alice)
    assert res.get_json()["quantity"] == 4
    assert client.patch(f"/api/collection/{item['id']}", json={"quantity": 0}, headers=alice).status_code == 400
    assert client.delete(f"/api/collection/{item['id']}", headers=alice).status_code == 204
    assert client.get("/api/collection", headers=alice).get_json()["items"] == []


def test_users_cannot_see_or_change_each_others_collection(client, alice, bob, cached_cards):
    item = client.post("/api/collection", json={"card_id": cached_cards["Lightning Bolt"]}, headers=alice).get_json()

    assert client.get("/api/collection", headers=bob).get_json()["items"] == []
    assert client.patch(f"/api/collection/{item['id']}", json={"quantity": 9}, headers=bob).status_code == 403
    assert client.delete(f"/api/collection/{item['id']}", headers=bob).status_code == 403
    assert client.get("/api/collection", headers=alice).get_json()["items"][0]["quantity"] == 1


def test_search_shows_how_many_you_own(client, alice, cached_cards):
    client.post("/api/collection", json={"card_id": cached_cards["Lightning Bolt"], "quantity": 3}, headers=alice)
    cards = client.get("/api/cards/search?q=bolt", headers=alice).get_json()["cards"]
    assert {c["name"]: c["owned"] for c in cards}["Lightning Bolt"] == 3


def _fill(client, headers, cached_cards):
    quantities = {"Lightning Bolt": 4, "Monastery Swiftspear": 1, "Shivan Dragon": 2}
    for name, qty in quantities.items():
        client.post("/api/collection", json={"card_id": cached_cards[name], "quantity": qty}, headers=headers)


def test_filter_by_name_keeps_whole_collection_stats(client, alice, cached_cards):
    _fill(client, alice, cached_cards)
    body = client.get("/api/collection?q=bolt", headers=alice).get_json()
    assert [i["card"]["name"] for i in body["items"]] == ["Lightning Bolt"]
    assert body["pagination"]["total_items"] == 1
    assert (body["unique_cards"], body["total_cards"]) == (3, 7)


def test_sort_and_paginate(client, alice, cached_cards):
    _fill(client, alice, cached_cards)
    first = client.get("/api/collection?sort=quantity&per_page=2", headers=alice).get_json()
    second = client.get("/api/collection?sort=quantity&per_page=2&page=2", headers=alice).get_json()
    assert [i["quantity"] for i in first["items"]] == [4, 2]
    assert [i["quantity"] for i in second["items"]] == [1]
    assert first["pagination"] == {"page": 1, "per_page": 2, "pages": 2, "total_items": 3}

    by_price = client.get("/api/collection?sort=price", headers=alice).get_json()
    assert by_price["items"][0]["card"]["name"] == "Lightning Bolt"


def test_color_filter_and_bad_params(client, alice, cached_cards):
    _fill(client, alice, cached_cards)
    assert len(client.get("/api/collection?color=R", headers=alice).get_json()["items"]) == 3
    assert client.get("/api/collection?color=U", headers=alice).get_json()["items"] == []
    res = client.get("/api/collection?sort=random&per_page=500", headers=alice)
    assert res.status_code == 400
    assert set(res.get_json()["fields"]) == {"sort", "per_page"}


def test_card_id_must_be_a_scryfall_uuid(client, alice):
    import responses

    with responses.RequestsMock() as rsps:  # no request may reach Scryfall
        for bad in ("random", "named?exact=Sol Ring", "../sets/abc"):
            res = client.post("/api/collection", json={"card_id": bad}, headers=alice)
            assert res.status_code == 400, bad
            assert "card_id" in res.get_json()["fields"]
        assert client.get("/api/cards/random", headers=alice).status_code == 404
        assert len(rsps.calls) == 0
