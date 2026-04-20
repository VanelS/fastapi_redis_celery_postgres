"""
Application FastAPI — point d'entrée HTTP du service.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.config import settings
from app.database import get_db
from app.models import Report
from app.schemas import ReportCreate, ReportResponse, ReportStatusResponse

import logging
logger = logging.getLogger(__name__)


# =========================================================
#  Instance FastAPI
# =========================================================
app = FastAPI(
    title=settings.app_name,
    description="API de génération de rapports asynchrones via Celery",
    version="0.1.0",
    debug=settings.debug,
)


# =========================================================
#  Health check
# =========================================================
@app.get("/", tags=["health"])
def health_check():
    """Vérifie que l'API est vivante."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "0.1.0",
    }


# =========================================================
#  Créer un rapport (async)
# =========================================================
@app.post(
    "/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["reports"],
    summary="Demander la génération d'un rapport",
)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
):
    """
    Crée un rapport en statut PENDING et retourne immédiatement.
    La génération effective sera déclenchée via Celery (étape 7).
    """
    # 1. Construire l'objet SQLAlchemy depuis le schema d'entrée
    report = Report(
        title=payload.title,
        parameters=payload.parameters,
    )

    # 2. Persister en base
    db.add(report)
    db.commit()
    db.refresh(report)  # Recharge pour avoir l'id, created_at, status, etc.

    # 3. Déclencher la tâche Celery
    from app.tasks import generate_report
    generate_report.delay(report.id)
    logger.info(f"📨 Tâche Celery envoyée pour le rapport {report.id}")

    # 4. Retourner — FastAPI convertit en ReportResponse via from_attributes
    return report


# =========================================================
#  Lister tous les rapports
# =========================================================
@app.get(
    "/reports",
    response_model=List[ReportResponse],
    tags=["reports"],
    summary="Lister tous les rapports",
)
def list_reports(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Liste paginée des rapports, plus récents en premier."""
    reports = (
        db.query(Report)
        .order_by(Report.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return reports


# =========================================================
#  Détail d'un rapport
# =========================================================
@app.get(
    "/reports/{report_id}",
    response_model=ReportResponse,
    tags=["reports"],
    summary="Récupérer un rapport par son ID",
    responses={404: {"description": "Rapport introuvable"}},
)
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
):
    """Récupère un rapport spécifique."""
    report = db.query(Report).filter(Report.id == report_id).first()

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rapport {report_id} introuvable",
        )

    return report


# =========================================================
#  Statut léger (pour polling)
# =========================================================
@app.get(
    "/reports/{report_id}/status",
    response_model=ReportStatusResponse,
    tags=["reports"],
    summary="Statut léger pour polling fréquent",
    responses={404: {"description": "Rapport introuvable"}},
)
def get_report_status(
    report_id: str,
    db: Session = Depends(get_db),
):
    """Endpoint léger à poller côté client pour savoir si le rapport est prêt."""
    report = db.query(Report).filter(Report.id == report_id).first()

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Rapport {report_id} introuvable",
    )

    return report