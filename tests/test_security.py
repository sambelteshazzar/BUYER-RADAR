from fastapi.testclient import TestClient


def test_post_blocked_without_token(monkeypatch, tmp_path):
    monkeypatch.setenv("SELLER_API_TOKEN", "s3cret-token")
    monkeypatch.setenv("BUYERADAR_DB", str(tmp_path / "sec.db"))
    from buyerradar.api.app import create_app
    client = TestClient(create_app())
    res = client.post("/api/sellers", json={"name": "Shop", "city": "Accra"})
    assert res.status_code == 401


def test_post_passes_with_bearer(monkeypatch, tmp_path):
    monkeypatch.setenv("SELLER_API_TOKEN", "s3cret-token")
    monkeypatch.setenv("BUYERADAR_DB", str(tmp_path / "sec2.db"))
    from buyerradar.api.app import create_app
    client = TestClient(create_app())
    res = client.post("/api/sellers", json={"name": "Shop", "city": "Accra"}, headers={"Authorization": "Bearer s3cret-token"})
    assert res.status_code == 201

def test_rejects_oversize_and_bad_source(monkeypatch, tmp_path):
    monkeypatch.delenv("SELLER_API_TOKEN", raising=False)
    monkeypatch.setenv("BUYERADAR_DB", str(tmp_path / "sec3.db"))
    from buyerradar.api.app import create_app
    client = TestClient(create_app())
    res = client.post("/api/sellers", json={"name": "x" * 200, "city": "Accra"})
    assert res.status_code == 422
    res2 = client.post("/api/scan?source=nope&query=hi")
    assert res2.status_code in (400, 422)
