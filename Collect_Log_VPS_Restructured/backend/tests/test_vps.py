"""Tests des endpoints VPS : CRUD, RBAC, pagination (RM-24), host (RM-25), soft delete (RM-23)."""


def _mk(name="vps-a", host="10.0.0.1", user="root"):
    return {"name": name, "host": host, "user": user}


def test_create_and_list_vps(client, admin_headers):
    r = client.post("/api/vps/", json=_mk(), headers=admin_headers)
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["name"] == "vps-a"
    assert "password" not in created  # secret jamais renvoyé

    r = client.get("/api/vps/", headers=admin_headers)
    assert r.status_code == 200
    assert r.headers.get("x-total-count") == "1"
    assert [v["name"] for v in r.json()] == ["vps-a"]


def test_create_vps_forbidden_for_viewer(client, viewer_headers):
    r = client.post("/api/vps/", json=_mk(), headers=viewer_headers)
    assert r.status_code == 403


def test_create_vps_requires_auth(client):
    r = client.post("/api/vps/", json=_mk())
    assert r.status_code == 401


def test_invalid_host_rejected(client, admin_headers):
    r = client.post("/api/vps/", json=_mk(host="bad host; rm -rf /"), headers=admin_headers)
    assert r.status_code == 422


def test_duplicate_name_conflict(client, admin_headers):
    assert client.post("/api/vps/", json=_mk(name="dup"), headers=admin_headers).status_code == 201
    r = client.post("/api/vps/", json=_mk(name="dup", host="10.0.0.2"), headers=admin_headers)
    assert r.status_code == 409


def test_get_vps_404(client, admin_headers):
    r = client.get("/api/vps/999999", headers=admin_headers)
    assert r.status_code == 404


def test_pagination(client, admin_headers):
    for i in range(3):
        client.post("/api/vps/", json=_mk(name=f"vps-{i}", host=f"10.0.0.{i+1}"), headers=admin_headers)

    r = client.get("/api/vps/?skip=0&limit=2", headers=admin_headers)
    assert r.status_code == 200
    assert r.headers["x-total-count"] == "3"
    page1 = [v["id"] for v in r.json()]
    assert len(page1) == 2

    r2 = client.get("/api/vps/?skip=2&limit=2", headers=admin_headers)
    page2 = [v["id"] for v in r2.json()]
    assert len(page2) == 1
    assert set(page1).isdisjoint(page2)  # pages disjointes


def test_soft_delete_and_restore(client, admin_headers):
    vid = client.post("/api/vps/", json=_mk(name="todelete"), headers=admin_headers).json()["id"]

    # suppression logique
    assert client.delete(f"/api/vps/{vid}", headers=admin_headers).status_code == 204
    # absent de la liste active
    names = [v["name"] for v in client.get("/api/vps/", headers=admin_headers).json()]
    assert "todelete" not in names
    # présent dans la corbeille
    trash = client.get("/api/vps/deleted", headers=admin_headers).json()
    assert "todelete" in [v["name"] for v in trash]
    # restauration
    assert client.post(f"/api/vps/{vid}/restore", headers=admin_headers).status_code == 200
    names = [v["name"] for v in client.get("/api/vps/", headers=admin_headers).json()]
    assert "todelete" in names
