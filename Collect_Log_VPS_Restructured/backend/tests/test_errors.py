"""Tests des handlers d'exception globaux (RM-35)."""
from fastapi.testclient import TestClient

from app.main import app

# Route de test qui lève une exception NON gérée, pour exercer le filet global.
@app.get("/_test_boom")
def _test_boom():
    raise RuntimeError("kaboom")


def test_unhandled_exception_returns_generic_500():
    # raise_server_exceptions=False : on veut la réponse 500, pas la ré-levée.
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get("/_test_boom")
    assert r.status_code == 500
    # DEBUG=false en test -> message générique, pas de fuite de l'exception.
    assert r.json() == {"detail": "Erreur interne du serveur."}


def test_http_exception_preserves_detail(client, admin_headers):
    # Le handler HTTPException délègue au défaut -> `detail` conservé.
    r = client.get("/api/vps/999999", headers=admin_headers)
    assert r.status_code == 404
    assert r.json()["detail"] == "VPS introuvable"


def test_validation_error_still_422_with_detail(client, admin_headers):
    r = client.post(
        "/api/vps/", json={"name": "x", "host": "bad host", "user": "root"}, headers=admin_headers
    )
    assert r.status_code == 422
    assert "detail" in r.json()


def test_unauthorized_preserves_www_authenticate_header(client):
    # Le 401 du login (mauvais mot de passe) conserve son en-tête WWW-Authenticate.
    r = client.post("/api/auth/login", data={"username": "admin", "password": "faux"})
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == "Bearer"
