"""
Tâches Celery — fonctions exécutées en arrière-plan par le worker.
"""
import os
import time
from datetime import datetime
from pathlib import Path

from celery.utils.log import get_task_logger
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.config import settings
from app.database import SessionLocal
from app.models import Report, ReportStatus
from app.worker import celery_app


logger = get_task_logger(__name__)


# =========================================================
#  Tâche : génération d'un rapport
# =========================================================
@celery_app.task(
    name="app.tasks.generate_report",
    bind=True,                         # Donne accès à self (retries, task_id, etc.)
    max_retries=3,
    default_retry_delay=10,            # 10 sec entre chaque retry
)
def generate_report(self, report_id: str) -> dict:
    """
    Génère un PDF de rapport en arrière-plan.

    Étapes :
      1. PENDING → PROCESSING
      2. Faire le boulot (simulation + PDF)
      3. PROCESSING → COMPLETED (ou FAILED si exception)
    """
    logger.info(f"🏁 Démarrage de la génération du rapport {report_id}")

    # On utilise une session SQLAlchemy dédiée au worker
    # (contrairement à get_db qui est pour les endpoints FastAPI)
    db = SessionLocal()

    try:
        # --- 1. Marquer PROCESSING ---
        report = db.query(Report).filter(Report.id == report_id).first()
        if report is None:
            logger.error(f"❌ Rapport {report_id} introuvable en base")
            return {"status": "failed", "reason": "not_found"}

        report.status = ReportStatus.PROCESSING
        db.commit()

        # --- 2. Faire le boulot ---
        # On simule une opération lourde (30 sec) + génération PDF
        logger.info(f"📊 Traitement du rapport '{report.title}'...")
        time.sleep(30)   # ← simule une grosse requête SQL / agrégation

        # Créer le dossier de sortie
        reports_dir = Path(settings.reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Générer un vrai PDF avec reportlab
        file_path = reports_dir / f"report_{report.id}.pdf"
        _generate_pdf(file_path, report)

        # --- 3. Marquer COMPLETED ---
        report.status = ReportStatus.COMPLETED
        report.file_path = str(file_path)
        report.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"✅ Rapport {report_id} généré : {file_path}")
        return {"status": "completed", "file_path": str(file_path)}

    except Exception as exc:
        # --- Gestion d'erreur : marquer FAILED + retry ---
        logger.exception(f"💥 Erreur lors de la génération du rapport {report_id}")

        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.status = ReportStatus.FAILED
            report.error_message = str(exc)
            db.commit()

        # Retry si on n'a pas épuisé les tentatives
        raise self.retry(exc=exc, countdown=10)

    finally:
        db.close()


# =========================================================
#  Helper : génération du PDF avec reportlab
# =========================================================
def _generate_pdf(file_path: Path, report: Report) -> None:
    """Génère un PDF simple à partir d'un objet Report."""
    c = canvas.Canvas(str(file_path), pagesize=A4)
    width, height = A4

    # Titre
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 80, report.title)

    # Métadonnées
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 120, f"ID : {report.id}")
    c.drawString(50, height - 140, f"Généré le : {datetime.utcnow().isoformat()}")

    # Paramètres
    c.drawString(50, height - 180, "Paramètres :")
    y = height - 200
    for key, value in report.parameters.items():
        c.drawString(70, y, f"• {key} : {value}")
        y -= 20

    # Faux contenu (à remplacer par de vraies requêtes en vrai projet)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y - 40, "Résumé exécutif")
    c.setFont("Helvetica", 10)
    c.drawString(50, y - 60, "Ceci est un rapport de démonstration pour le projet FastAPI + Celery.")

    c.showPage()
    c.save()