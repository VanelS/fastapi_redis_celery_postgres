"""
Modèles SQLAlchemy : tables de la base de données.
"""
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, DateTime, Enum, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from app.database import Base

class ReportStatus(str, PyEnum):
    """États possibles d'un rapport dans son cycle de vie."""
    PENDING = "pending"        # Créé, en attente du worker
    PROCESSING = "processing"  # Worker est dessus
    COMPLETED = "completed"    # Rapport prêt, file_path rempli
    FAILED = "failed"          # Erreur, voir error_message


class Report(Base):
    """
    Représente un rapport demandé par un utilisateur.
    Cycle de vie : PENDING → PROCESSING → COMPLETED (ou FAILED)
    """
    __tablename__ = "reports"

    # --- Identifiant ---
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # --- Données d'entrée (ce que le client a demandé) ---
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)

    # --- État ---
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"),
        default=ReportStatus.PENDING,
        nullable=False,
        index=True,  # On fera souvent des queries filtrant par statut
    )

    # --- Résultats (remplis par le worker) ---
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Horodatage ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Report id={self.id[:8]}... status={self.status.value}>"