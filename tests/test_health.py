"""Tests du endpoint health check."""


def test_health_check(client):
    """Le endpoint racine doit répondre OK."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "version" in data