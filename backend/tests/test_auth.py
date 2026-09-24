from app.deps import limiter
from tests.conftest import register


def test_register_login_and_me(client):
    headers = register(client, "Bob_1")
    assert client.get("/auth/me", headers=headers).json() == {"username": "bob_1", "timezone": "Asia/Karachi"}

    res = client.post("/auth/login", json={"username": "BOB_1", "password": "password123"})
    assert res.status_code == 200
    assert res.json()["access_token"]


def test_duplicate_username_is_rejected(client):
    register(client, "carol")
    res = client.post("/auth/register", json={"username": "Carol", "password": "password123"})
    assert res.status_code == 409


def test_wrong_password_and_unknown_user_look_the_same(client):
    register(client, "dave")
    wrong = client.post("/auth/login", json={"username": "dave", "password": "nope-nope"})
    missing = client.post("/auth/login", json={"username": "nobody", "password": "nope-nope"})
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()


def test_weak_input_is_rejected(client):
    assert client.post("/auth/register", json={"username": "ed", "password": "password123"}).status_code == 422
    assert client.post("/auth/register", json={"username": "eddie", "password": "short"}).status_code == 422
    bad_tz = {"username": "eddie", "password": "password123", "timezone": "Mars/Base"}
    assert client.post("/auth/register", json=bad_tz).status_code == 422


def test_protected_routes_need_a_valid_token(client):
    assert client.post("/chat", json={"message": "hi"}).status_code == 401
    assert client.get("/chat/history", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_login_is_rate_limited(client):
    limiter.enabled = True
    codes = [client.post("/auth/login", json={"username": "x", "password": "y"}).status_code for _ in range(7)]
    assert codes[:5] == [401] * 5
    assert codes[-1] == 429


def test_health_endpoints(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}