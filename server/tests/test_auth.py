from .conftest import auth, signup


def test_signup_returns_token_and_user(client):
    res = client.post("/api/signup", json={"username": "larry", "email": "L@Test.dev", "password": "password123"})
    body = res.get_json()
    assert res.status_code == 201
    assert body["token"]
    assert body["user"] == {"id": 1, "username": "larry", "email": "l@test.dev"}
    assert "password" not in str(body)


def test_signup_validates_fields(client):
    res = client.post("/api/signup", json={"username": "x", "email": "nope", "password": "short"})
    fields = res.get_json()["fields"]
    assert res.status_code == 400
    assert set(fields) == {"username", "email", "password"}


def test_signup_rejects_duplicates_case_insensitively(client):
    signup(client, "alice")
    res = client.post("/api/signup", json={"username": "ALICE", "email": "alice@test.dev", "password": "password123"})
    assert res.status_code == 409
    assert set(res.get_json()["fields"]) == {"username", "email"}


def test_login_with_username_or_email(client):
    signup(client, "alice")
    for ident in ("alice", "Alice", "alice@test.dev"):
        res = client.post("/api/login", json={"username": ident, "password": "password123"})
        assert res.status_code == 200, ident
        assert res.get_json()["user"]["username"] == "alice"


def test_login_wrong_password_gives_generic_error(client):
    signup(client, "alice")
    wrong = client.post("/api/login", json={"username": "alice", "password": "nope-nope"})
    missing = client.post("/api/login", json={"username": "ghost", "password": "nope-nope"})
    assert wrong.status_code == missing.status_code == 401
    assert wrong.get_json() == missing.get_json()


def test_me_requires_token(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers=auth("garbage")).status_code == 401


def test_me_returns_user_and_stats(client, alice):
    res = client.get("/api/me", headers=alice)
    assert res.status_code == 200
    assert res.get_json()["user"]["username"] == "alice"
    assert res.get_json()["stats"] == {"unique_cards": 0, "total_cards": 0, "decks": 0}


def test_protected_routes_reject_anonymous(client):
    for method, url in [
        ("get", "/api/cards/search?q=bolt"),
        ("get", "/api/collection"),
        ("post", "/api/collection"),
        ("get", "/api/decks"),
        ("post", "/api/decks"),
    ]:
        assert getattr(client, method)(url).status_code == 401, url


def test_app_refuses_to_start_without_a_strong_secret():
    import pytest

    from app import create_app
    from app.config import TestConfig

    class NoSecret(TestConfig):
        JWT_SECRET_KEY = "short"

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        create_app(NoSecret)


def test_password_over_72_bytes_is_a_field_error_not_a_crash(client):
    # bcrypt only reads 72 bytes and bcrypt 5 raises on longer input.
    res = client.post("/api/signup", json={"username": "longpw", "email": "l@test.dev", "password": "a" * 73})
    assert res.status_code == 400
    assert "password" in res.get_json()["fields"]

    multibyte = client.post("/api/signup", json={"username": "emoji", "email": "e@test.dev", "password": "é" * 40})
    assert multibyte.status_code == 400  # 40 characters, 80 bytes


def test_login_with_very_long_password_is_a_normal_401(client):
    signup(client, "alice")
    res = client.post("/api/login", json={"username": "alice", "password": "a" * 200})
    assert res.status_code == 401


def test_login_is_rate_limited():
    from app import create_app
    from app.config import TestConfig
    from app.extensions import db

    class Limited(TestConfig):
        RATELIMIT_ENABLED = True

    app = create_app(Limited)
    with app.app_context():
        db.create_all()
        client = app.test_client()
        codes = [
            client.post("/api/login", json={"username": "ghost", "password": "wrong-pass"}).status_code
            for _ in range(11)
        ]
        assert codes[:10] == [401] * 10
        assert codes[10] == 429
        assert "error" in client.post("/api/login", json={"username": "g", "password": "p"}).get_json()
        db.drop_all()
