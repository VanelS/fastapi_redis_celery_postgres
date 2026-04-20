"""
Schémas Pydantic : contrats d'entrée/sortie de l'API.
Séparés volontairement des modèles SQLAlchemy (models.py).
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.models import ReportStatus


# =========================================================
#  Base : champs communs à l'entrée et à la sortie
# =========================================================
class ReportBase(BaseModel):
    """Champs communs à la création et à la lecture."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Titre du rapport",
        examples=["Rapport des ventes Q4 2024"],
    )
    parameters: dict = Field(
        default_factory=dict,
        description="Paramètres libres pour la génération (année, filtres, etc.)",
        examples=[{"year": 2024, "department": "sales"}],
    )


# =========================================================
#  Entrée : ce que le client envoie pour créer un rapport
# =========================================================
class ReportCreate(ReportBase):
    """Payload d'entrée pour POST /reports."""
    pass  # Rien à ajouter pour l'instant, mais on garde la classe pour l'évolution


# =========================================================
#  Sortie : ce que l'API renvoie au client
# =========================================================
class ReportResponse(ReportBase):
    """Payload de sortie — représentation complète d'un rapport."""

    id: str = Field(..., description="Identifiant UUID du rapport")
    status: ReportStatus = Field(..., description="État actuel du rapport")
    file_path: str | None = Field(None, description="Chemin du fichier si COMPLETED")
    error_message: str | None = Field(None, description="Message d'erreur si FAILED")
    created_at: datetime
    completed_at: datetime | None = None

    # Permet de construire ce schema depuis un objet SQLAlchemy
    model_config = ConfigDict(from_attributes=True)


# =========================================================
#  Sortie légère : juste pour le polling du statut
# =========================================================
class ReportStatusResponse(BaseModel):
    """Payload léger pour GET /reports/{id}/status (polling fréquent)."""

    id: str
    status: ReportStatus
    file_path: str | None = None

    model_config = ConfigDict(from_attributes=True)