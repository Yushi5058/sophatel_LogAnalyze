"""Tests de l'enrichissement des IP (RM-34) — sans réseau (fournisseurs mockés)."""
import pytest

from app.core.database import SessionLocal
from app.services import enrichment_service as es


def test_private_ip_no_external_call(client, admin_headers, monkeypatch):
    # Une IP privée ne doit JAMAIS déclencher d'appel externe.
    def boom(ip):
        raise AssertionError("appel externe interdit pour une IP privée")
    monkeypatch.setattr(es, "_geolocate", boom)
    monkeypatch.setattr(es, "_reputation", boom)

    r = client.get("/api/enrich/ip/127.0.0.1", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["is_private"] is True
    assert body["country"] is None
    assert body["providers"] is None


def test_enrich_requires_auth(client):
    assert client.get("/api/enrich/ip/8.8.8.8").status_code == 401


def test_graceful_degradation(monkeypatch):
    # Si le fournisseur externe plante, pas d'exception : champs à None, cache écrit.
    def boom(ip):
        raise RuntimeError("API externe indisponible")
    monkeypatch.setattr(es, "_geolocate", boom)
    monkeypatch.setattr(es, "_reputation", boom)

    db = SessionLocal()
    try:
        out = es.enrich_ip("8.8.8.8", db)   # IP publique réelle
    finally:
        db.close()
    assert out["is_private"] is False
    assert out["country"] is None
    assert out["providers"] is None  # aucun fournisseur n'a répondu


def test_cache_hit_avoids_second_call(monkeypatch):
    calls = {"n": 0}
    def fake_geo(ip):
        calls["n"] += 1
        return {"country_code": "US", "country": "United States", "isp": "Test", "_provider": "ip-api"}
    monkeypatch.setattr(es, "_geolocate", fake_geo)
    monkeypatch.setattr(es, "_reputation", lambda ip: {})

    db = SessionLocal()
    try:
        a = es.enrich_ip("8.8.8.8", db)
        b = es.enrich_ip("8.8.8.8", db)   # doit venir du cache
    finally:
        db.close()
    assert a["country"] == "United States"
    assert b["country"] == "United States"
    assert calls["n"] == 1  # un seul appel externe (2e = cache)
    assert "ip-api" in (a["providers"] or "")


def test_top_ips_enriched_empty(client, admin_headers):
    r = client.get("/api/enrich/top-ips", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == []
