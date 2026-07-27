"""Tests des bornes de pagination des logs (RM-29)."""


def test_entries_size_zero_rejected(client, admin_headers):
    r = client.get("/api/logs/collections/1/entries?size=0", headers=admin_headers)
    assert r.status_code == 422


def test_entries_size_negative_rejected(client, admin_headers):
    r = client.get("/api/logs/collections/1/entries?size=-5", headers=admin_headers)
    assert r.status_code == 422


def test_entries_valid_size_ok(client, admin_headers):
    r = client.get("/api/logs/collections/1/entries?size=10", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["items"] == []  # collection inexistante → page vide


def test_collections_limit_zero_rejected(client, admin_headers):
    r = client.get("/api/logs/collections?limit=0", headers=admin_headers)
    assert r.status_code == 422
