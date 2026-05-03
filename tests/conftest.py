"""
Fixtures partagées pour tous les tests.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db


# =========================================================
#  Fixture 1 : Mock generate_report.delay (Celery isolé)
# =========================================================
@pytest.fixture(autouse=True)
def mock_celery_delay():
    """
    Mock la tâche Celery pour qu'elle ne s'exécute pas pendant les tests.
    On teste l'API, pas le worker.
    """
    with patch("app.tasks.generate_report.delay") as mock_delay:
        mock_delay.return_value = None
        yield mock_delay


# =========================================================
#  Fixture 2 : BD SQLite en mémoire (jetable, ultra-rapide)
# =========================================================
@pytest.fixture
def db_session():
    """Session SQLite en mémoire, recréée pour chaque test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# =========================================================
#  Fixture 3 : TestClient avec BD overridée
# =========================================================
@pytest.fixture
def client(db_session):
    """TestClient FastAPI avec BD SQLite à la place de PostgreSQL."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()