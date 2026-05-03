"""Tests des endpoints de lecture."""


def test_list_reports_empty(client):
    """Sans rapport en base, la liste est vide."""
    response = client.get("/reports")
    assert response.status_code == 200
    assert response.json() == []


def test_list_reports_after_create(client):
    """Après création, le rapport apparaît dans la liste."""
    client.post("/reports", json={"title": "R1"})
    client.post("/reports", json={"title": "R2"})

    response = client.get("/reports")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_report_by_id(client):
    """On peut récupérer un rapport par son id."""
    create_resp = client.post("/reports", json={"title": "Mon rapport"})
    report_id = create_resp.json()["id"]

    response = client.get(f"/reports/{report_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Mon rapport"


def test_get_report_not_found(client):
    """Un id inexistant retourne 404."""
    response = client.get("/reports/inexistant-id")
    assert response.status_code == 404


def test_get_report_status(client):
    """L'endpoint /status retourne juste id, status, file_path."""
    create_resp = client.post("/reports", json={"title": "Test"})
    report_id = create_resp.json()["id"]

    response = client.get(f"/reports/{report_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "status" in data
    # Pas de title dans la réponse status (schema léger)
    assert "title" not in data
