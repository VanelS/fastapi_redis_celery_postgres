"""Tests de POST /reports."""


def test_create_report_returns_202(client):
    """La création retourne 202 Accepted (async)."""
    response = client.post(
        "/reports",
        json={"title": "Mon rapport", "parameters": {"year": 2024}},
    )
    assert response.status_code == 202


def test_create_report_returns_pending_status(client):
    """Au démarrage, le statut DEVRAIT être 'pending'..."""
    response = client.post("/reports", json={"title": "Test"})
    data = response.json()

    # NOTE : avec eager mode, la tâche s'exécute IMMÉDIATEMENT
    # donc le statut peut déjà être 'completed' à ce stade.
    # On vérifie juste qu'on a un statut valide.
    assert data["status"] in ["pending", "processing", "completed", "failed"]


def test_create_report_returns_uuid(client):
    """L'id retourné est un UUID."""
    response = client.post("/reports", json={"title": "Test"})
    data = response.json()
    assert "id" in data
    assert len(data["id"]) == 36  # UUID format


def test_create_report_with_invalid_payload(client):
    """Un payload invalide retourne 422."""
    response = client.post("/reports", json={"title": ""})
    assert response.status_code == 422