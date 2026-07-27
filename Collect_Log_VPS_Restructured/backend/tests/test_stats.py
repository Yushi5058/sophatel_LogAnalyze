"""Tests des statistiques globales (RM-27)."""


def test_global_stats_requires_auth(client):
    assert client.get("/api/stats/global").status_code == 401


def test_global_stats_empty(client, admin_headers):
    r = client.get("/api/stats/global", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    # Base vide : compteurs à zéro, structure présente.
    assert body["total_requests"] == 0
    assert body["total_errors"] == 0
    assert body["vps_count"] == 0
    assert body["error_rate"] == 0.0


def test_global_stats_excludes_data_of_deleted_vps(client, admin_headers):
    # Un VPS actif compte dans vps_count ; après soft delete, il n'y est plus (RM-23).
    vid = client.post(
        "/api/vps/", json={"name": "s1", "host": "10.0.0.9", "user": "root"}, headers=admin_headers
    ).json()["id"]
    assert client.get("/api/stats/global", headers=admin_headers).json()["vps_count"] == 1

    client.delete(f"/api/vps/{vid}", headers=admin_headers)
    assert client.get("/api/stats/global", headers=admin_headers).json()["vps_count"] == 0
