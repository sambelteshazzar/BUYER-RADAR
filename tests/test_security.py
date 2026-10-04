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
