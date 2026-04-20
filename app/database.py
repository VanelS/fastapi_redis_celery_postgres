"""
Configuration de la connexion à la base de données.
Expose : engine, SessionLocal, Base, et la dépendance get_db.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

from app.config import settings

# --- 1. Engine : le gestionnaire de connexions ---
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,    # Vérifie que la connexion est vivante avant usage
    pool_size=5,           # 5 connexions persistantes
    max_overflow=10,       # Jusqu'à 10 de plus si pic de charge
    echo=settings.debug,   # En mode DEBUG, log toutes les requêtes SQL
)

# --- 2. SessionLocal : usine à sessions ---
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,   # On commite manuellement, jamais en auto
    autoflush=False,    # Pareil pour le flush, maîtrise totale
)

# --- 3. Base : classe parente de tous les modèles ---
class Base(DeclarativeBase):
    """Classe de base pour tous les modèles SQLAlchemy."""
    pass

# --- 4. Dépendance FastAPI : fournit une session par requête ---
def get_db() -> Generator[Session, None, None]:
    """
    Fournit une session SQLAlchemy à un endpoint FastAPI.
    Garantit fermeture propre même en cas d'exception.

    Usage dans un endpoint :
        @app.get("/reports")
        def list_reports(db: Session = Depends(get_db)):
            return db.query(Report).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()