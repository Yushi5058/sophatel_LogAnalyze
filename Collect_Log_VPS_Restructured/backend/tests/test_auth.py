"""Tests d'authentification (RM-27)."""


def test_login_success(client):
    r = client.post("/api/auth/login", data={"username": "admin", "password": "admin-test-pw"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["username"] == "admin"
    assert body["role"] == "admin"
    assert body["access_token"]


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", data={"username": "admin", "password": "mauvais"})
    assert r.status_code == 401


def test_me_requires_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_token(client, admin_headers):
    r = client.get("/api/auth/me", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["username"] == "admin"
    assert r.json()["role"] == "admin"
