"""Tests de GET /reports/{id}/download."""

from app.models import Report, ReportStatus


def test_download_completed_report(client, db_session, tmp_path):
    """Un rapport COMPLETED avec un fichier existant peut être téléchargé."""
    # Setup : créer un faux PDF
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake content")

    create_resp = client.post("/reports", json={"title": "Test"})
    report_id = create_resp.json()["id"]

    report = db_session.query(Report).filter(Report.id == report_id).first()
    report.status = ReportStatus.COMPLETED
    report.file_path = str(fake_pdf)
    db_session.commit()

    # Action
    response = client.get(f"/reports/{report_id}/download")

    # Assertions
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]


def test_download_pending_report_rejected(client, db_session):
    """Un rapport PENDING ne peut pas être téléchargé → 409."""
    create_resp = client.post("/reports", json={"title": "Test"})
    report_id = create_resp.json()["id"]

    report = db_session.query(Report).filter(Report.id == report_id).first()
    report.status = ReportStatus.PENDING
    db_session.commit()

    response = client.get(f"/reports/{report_id}/download")
    assert response.status_code == 409


def test_download_completed_but_file_missing(client, db_session):
    """Si le fichier a disparu du disque → 410 Gone."""
    create_resp = client.post("/reports", json={"title": "Test"})
    report_id = create_resp.json()["id"]

    report = db_session.query(Report).filter(Report.id == report_id).first()
    report.status = ReportStatus.COMPLETED
    report.file_path = "/path/qui/n/existe/pas.pdf"
    db_session.commit()

    response = client.get(f"/reports/{report_id}/download")
    assert response.status_code == 410


def test_download_unknown_report(client):
    """Un id inexistant retourne 404."""
    response = client.get("/reports/unknown/download")
    assert response.status_code == 404
