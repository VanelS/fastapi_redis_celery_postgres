"""Tests de POST /reports/{id}/retry."""
from app.models import Report, ReportStatus


def test_retry_failed_report(client, db_session):
    """Un rapport FAILED peut être retry."""
    # Setup : créer un rapport et le forcer en FAILED
    create_resp = client.post("/reports", json={"title": "Test"})
    report_id = create_resp.json()["id"]

    report = db_session.query(Report).filter(Report.id == report_id).first()
    report.status = ReportStatus.FAILED
    report.error_message = "Erreur précédente"
    db_session.commit()

    # Action : retry
    response = client.post(f"/reports/{report_id}/retry")

    # Assertions
    assert response.status_code == 202
    data = response.json()
    assert data["error_message"] is None  # effacé !


def test_retry_completed_report_rejected(client, db_session):
    """Un rapport COMPLETED ne peut pas être retry → 409."""
    create_resp = client.post("/reports", json={"title": "Test"})
    report_id = create_resp.json()["id"]

    report = db_session.query(Report).filter(Report.id == report_id).first()
    report.status = ReportStatus.COMPLETED
    db_session.commit()

    response = client.post(f"/reports/{report_id}/retry")
    assert response.status_code == 409


def test_retry_pending_report_rejected(client, db_session):
    """Un rapport PENDING ne peut pas être retry → 409."""
    create_resp = client.post("/reports", json={"title": "Test"})
    report_id = create_resp.json()["id"]

    report = db_session.query(Report).filter(Report.id == report_id).first()
    report.status = ReportStatus.PENDING
    db_session.commit()

    response = client.post(f"/reports/{report_id}/retry")
    assert response.status_code == 409


def test_retry_unknown_report(client):
    """Un id inexistant retourne 404."""
    response = client.post("/reports/unknown/retry")
    assert response.status_code == 404