# 🚀 Tutoriel : FastAPI + Celery + PostgreSQL + Redis avec Docker

Un guide pas à pas pour construire une API de **génération de rapports asynchrones** en Python, avec une stack de production moderne.

> 📖 Ce tutoriel est le résultat d'une session interactive. Les encadrés `💬 Q&A` reprennent les questions posées pendant la construction et leurs réponses détaillées — garde-les près de toi, elles clarifient beaucoup de points que les tutos classiques survolent.

---

## 📋 Table des matières

- [🎯 Ce que tu vas construire](#-ce-que-tu-vas-construire)
- [🏗️ Architecture](#️-architecture)
- [📦 Prérequis](#-prérequis)
- [📂 Structure finale du projet](#-structure-finale-du-projet)
- [Étape 1 — Préparation du projet](#étape-1--préparation-du-projet)
- [Étape 2 — Les dépendances Python](#étape-2--les-dépendances-python)
- [Étape 3 — Configuration avec `.env` et `config.py`](#étape-3--configuration-avec-env-et-configpy)
- [Étape 4 — Base de données : connexion + modèles](#étape-4--base-de-données--connexion--modèles)
- [Étape 5 — Schemas Pydantic : la frontière API ↔ BD](#étape-5--schemas-pydantic--la-frontière-api--bd)
- [Étape 6 — L'app FastAPI et ses endpoints](#étape-6--lapp-fastapi-et-ses-endpoints)
- [Étape 7 — Celery : le cerveau des tâches en arrière-plan](#étape-7--celery--le-cerveau-des-tâches-en-arrière-plan)
- [Étape 8 — Docker Compose : orchestrer l'écosystème](#étape-8--docker-compose--orchestrer-lécosystème)
- [Étape 9 — Alembic : les migrations de schéma](#étape-9--alembic--les-migrations-de-schéma)
- [🧪 Test de bout en bout](#-test-de-bout-en-bout)
- [📚 Récapitulatif des difficultés rencontrées](#-récapitulatif-des-difficultés-rencontrées)
- [🎓 Pour aller plus loin](#-pour-aller-plus-loin)

---

## 🎯 Ce que tu vas construire

Une API qui accepte des demandes de rapports, délègue leur génération à un **worker en arrière-plan**, et permet au client de suivre l'avancement. L'utilisateur reçoit immédiatement un `task_id` et peut poller le statut, plutôt que d'attendre 30 secondes sur un écran bloqué.

**Stack utilisée :**

- **FastAPI** — framework web moderne, rapide, auto-documenté
- **Celery** — système de tâches asynchrones
- **Redis** — broker entre FastAPI et Celery
- **PostgreSQL + SQLAlchemy** — base de données et ORM
- **Alembic** — migrations de schéma
- **Docker Compose** — orchestration de tous les services
- **Flower** — UI de monitoring Celery

---

## 🏗️ Architecture

```
┌────────┐    ┌──────────┐    ┌───────┐    ┌────────────────┐
│ Client │───▶│ FastAPI  │───▶│ Redis │───▶│ Celery Worker  │
└────────┘    └────┬─────┘    └───────┘    └────────┬───────┘
                   │                                │
                   ▼                                ▼
             ┌────────────────────────────────────────┐
             │            PostgreSQL                  │
             │   (statut + résultats des rapports)    │
             └────────────────────────────────────────┘
```

**Scénario type** : `POST /reports` crée une ligne en base (statut `PENDING`) et retourne immédiatement un `task_id`. FastAPI dépose la tâche dans Redis. Le Worker Celery la consomme, génère le PDF, met à jour la base en `COMPLETED`. Le client poll `GET /reports/{id}/status` jusqu'à voir `"completed"`.

---

## 📦 Prérequis

- **Python 3.11+**
- **Docker** et **Docker Compose** installés ([docs Docker](https://docs.docker.com/get-docker/))
- Un éditeur de code (VSCode, PyCharm…)
- Des bases en Python et en API REST

---

## 📂 Structure finale du projet

```
fastapi-celery/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── .env                  # secrets — jamais commité
├── .env.example          # template — commité
├── .gitignore
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI endpoints
│   ├── config.py         # Settings Pydantic depuis .env
│   ├── database.py       # Engine, Session, Base
│   ├── models.py         # Modèles SQLAlchemy
│   ├── schemas.py        # Schemas Pydantic (I/O API)
│   ├── tasks.py          # Tâches Celery
│   └── worker.py         # Instance Celery
└── alembic/
    ├── env.py
    ├── script.py.mako
    └── versions/
        └── xxx_create_reports_table.py
```

---

## Étape 1 — Préparation du projet

### Objectif
Créer la structure de dossiers et l'environnement Python.

### Action 1 · Créer la structure

```bash
mkdir fastapi-celery && cd fastapi-celery
mkdir app alembic

touch docker-compose.yml Dockerfile requirements.txt .env .gitignore
touch app/__init__.py app/main.py app/config.py app/database.py \
      app/models.py app/schemas.py app/tasks.py app/worker.py
```

### Action 2 · Créer et activer un environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate
```

Tu dois voir `(venv)` apparaître devant ton prompt.

> 💬 **Q&A : Pourquoi un venv puisqu'on va utiliser Docker ?**
>
> Le venv sert à ta **machine hôte** : ton IDE (VSCode, PyCharm) a besoin des paquets localement pour l'autocomplétion, le linting, la détection d'erreurs. Docker, lui, construira son propre environnement isolé pour **l'exécution**. Les deux coexistent pacifiquement.

### Action 3 · `.gitignore`

```gitignore
# Python
venv/
__pycache__/
*.pyc
.pytest_cache/

# Environnement (SECRET — jamais commiter)
.env

# IDE
.vscode/
.idea/

# OS
.DS_Store

# Rapports générés localement
reports/
```

### Action 4 · Init Git (optionnel)

```bash
git init
git add .
git commit -m "feat: initial project structure"
```

---

## Étape 2 — Les dépendances Python

### Action 1 · Remplir `requirements.txt`

```txt
# --- Web framework ---
fastapi==0.115.0
uvicorn[standard]==0.32.0

# --- Base de données ---
sqlalchemy==2.0.35
psycopg2-binary==2.9.10
alembic==1.13.3

# --- Celery + Redis ---
celery==5.4.0
redis==5.1.1
flower==2.0.1

# --- Configuration ---
pydantic==2.9.2
pydantic-settings==2.6.1

# --- Génération PDF ---
reportlab==4.2.5
```

### Action 2 · Installer

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Vérification

```bash
pip list | grep -E "fastapi|celery|sqlalchemy|alembic|redis"
python -c "import fastapi, celery, sqlalchemy, alembic; print('✅ Tout est importable')"
```

---

> 💬 **Q&A : Qu'est-ce qu'un serveur ASGI et pourquoi `uvicorn[standard]` ?**
>
> **ASGI (Asynchronous Server Gateway Interface)** est la norme moderne pour les serveurs web Python asynchrones. Elle remplace **WSGI** (synchrone, utilisée par Flask/Django classique) qui bloquait un worker pour chaque requête.
>
> Avec ASGI, un seul worker peut gérer des milliers de requêtes en parallèle : pendant qu'une requête attend la BD, le worker passe à la suivante.
>
> **Analogie du restaurant :**
> - **WSGI** : un serveur prend une commande, **attend** en cuisine, la ramène, passe au client suivant. Si la cuisine met 10 min, les autres clients poireautent.
> - **ASGI** : un serveur prend une commande, la passe en cuisine, **va tout de suite voir le client suivant**. Quand un plat est prêt, il vient le chercher.
>
> **Uvicorn** est un serveur ASGI (comme Hypercorn, Daphne). C'est lui qui écoute sur le port 8000, reçoit les requêtes HTTP et les passe à ton app FastAPI.
>
> **Pourquoi `[standard]` ?** Les crochets sont des **extras** pip qui installent des dépendances optionnelles utiles :
> - `httptools` : parser HTTP ultra-rapide (C)
> - `uvloop` : boucle d'événements async 2-4× plus rapide
> - `websockets` : support WebSockets
> - `watchfiles` : détection auto des changements pour `--reload`
> - `python-dotenv`, `PyYAML` : bonus
>
> **Bilan** : pour 5 MB supplémentaires, Uvicorn passe de ~15 000 req/s à ~40 000+ req/s.

---

## Étape 3 — Configuration avec `.env` et `config.py`

### Action 1 · Remplir `.env`

```dotenv
# === Application ===
APP_NAME=FastAPI Celery Reports
DEBUG=True

# === PostgreSQL ===
POSTGRES_USER=reports_user
POSTGRES_PASSWORD=reports_pass
POSTGRES_DB=reports_db
POSTGRES_HOST=db
POSTGRES_PORT=5432

# === Redis / Celery ===
REDIS_HOST=redis
REDIS_PORT=6379

# === Rapports ===
REPORTS_DIR=/app/reports
```

> 💡 Pourquoi `db` et `redis` comme hôtes au lieu de `localhost` ? Parce qu'on va tourner dans Docker Compose : chaque service est joignable par **son nom de service**.

### Action 2 · Créer `.env.example`

```bash
cp .env .env.example
```

Puis remplace les valeurs sensibles par des placeholders (`your_user`, `your_password`, etc.). Ce fichier **sera commité**, contrairement à `.env`.

### Action 3 · `app/config.py`

```python
"""
Configuration de l'application.
Charge les variables depuis .env et les expose via un objet typé.
"""
from functools import lru_cache
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application, chargés depuis .env."""

    # --- Application ---
    app_name: str = "FastAPI Celery Reports"
    debug: bool = False

    # --- PostgreSQL ---
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "db"
    postgres_port: int = 5432

    # --- Redis ---
    redis_host: str = "redis"
    redis_port: int = 6379

    # --- Rapports ---
    reports_dir: str = "/app/reports"

    # --- URLs calculées ---
    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Retourne un singleton des settings."""
    return Settings()


settings = get_settings()
```

### Vérification

```bash
python -c "from app.config import settings; print(settings.model_dump_json(indent=2))"
```

Tu dois voir un JSON avec toutes les valeurs + les URLs calculées.

---

> 💬 **Q&A : À quoi sert `@computed_field` ?**
>
> En une phrase : transformer une **méthode calculée** en "vrai" champ du modèle, **visible lors de la sérialisation** (JSON, `.model_dump()`, doc OpenAPI).
>
> **Sans `@computed_field`** (une `@property` classique) :
> - `settings.database_url` fonctionne ✅
> - Mais `settings.model_dump()` **NE contient PAS** `database_url` ❌
> - Pas visible dans Swagger, pas sérialisé en JSON
>
> **Avec `@computed_field`** :
> - Tout fonctionne comme avant ✅
> - Et `database_url` **apparaît** dans `model_dump()`, `model_dump_json()`, OpenAPI ✅
>
> **Ordre des décorateurs** : `@computed_field` externe, `@property` interne. Dans l'autre sens, ça ne marche pas.
>
> **Règle simple** :
> - Attribut calculé **seulement pour Python** → `@property`
> - Attribut calculé **visible dans le JSON / la doc** → `@computed_field` + `@property`

---

## Étape 4 — Base de données : connexion + modèles

### Concepts clés de SQLAlchemy

1. **Engine** : gestionnaire de connexions à la BD (créé une seule fois)
2. **Session** : espace de travail = une transaction (créée par requête)
3. **Base declarative** : classe parente de tous les modèles

### Action 1 · `app/database.py`

```python
"""
Configuration de la connexion à la base de données.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

from app.config import settings


# --- Engine : le gestionnaire de connexions ---
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.debug,
)


# --- SessionLocal : usine à sessions ---
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# --- Base : classe parente de tous les modèles ---
class Base(DeclarativeBase):
    pass


# --- Dépendance FastAPI : fournit une session par requête ---
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Action 2 · `app/models.py`

```python
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
    """États possibles d'un rapport."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"),
        default=ReportStatus.PENDING,
        nullable=False,
        index=True,
    )

    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Report id={self.id[:8]}... status={self.status.value}>"
```

### Action 3 · ⚠️ Brancher les modèles à la Base (crucial)

Ouvre `app/__init__.py` et ajoute :

```python
from app.models import Report  # noqa: F401
```

> 💡 **Pourquoi ?** SQLAlchemy ne connaît que les modèles **importés au moins une fois**. Sans cet import, Alembic ne verra pas la table `reports` et ne générera aucune migration.

### Vérification

```bash
python -c "
from app.database import Base, engine
from app.models import Report, ReportStatus
print('✅ Imports OK')
print(f'Tables détectées : {list(Base.metadata.tables.keys())}')
print(f'Colonnes de reports : {[c.name for c in Report.__table__.columns]}')
print(f'Statuts : {[s.value for s in ReportStatus]}')
"
```

---

## Étape 5 — Schemas Pydantic : la frontière API ↔ BD

### Pourquoi séparer modèles SQLAlchemy et schemas Pydantic ?

- 🔒 **Sécurité** : tu ne fuites pas accidentellement des champs internes
- 🎯 **Validation** : Pydantic valide vraiment les entrées/sorties
- 🔗 **Découplage** : changer le schéma BD ne casse pas l'API
- 📦 **Formes multiples** : `ReportCreate` ≠ `ReportResponse` ≠ `ReportStatusResponse`

### Action · `app/schemas.py`

```python
"""
Schémas Pydantic : contrats d'entrée/sortie de l'API.
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.models import ReportStatus


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
        description="Paramètres libres pour la génération",
        examples=[{"year": 2024, "department": "sales"}],
    )


class ReportCreate(ReportBase):
    """Payload d'entrée pour POST /reports."""
    pass


class ReportResponse(ReportBase):
    """Payload de sortie complet."""
    id: str
    status: ReportStatus
    file_path: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ReportStatusResponse(BaseModel):
    """Payload léger pour polling."""
    id: str
    status: ReportStatus
    file_path: str | None = None

    model_config = ConfigDict(from_attributes=True)
```

### Le point clé : `from_attributes=True`

Cette ligne permet à Pydantic d'accepter un **objet SQLAlchemy** (avec des attributs) et pas seulement un dict. Sans elle, FastAPI ne pourrait pas convertir automatiquement ta ligne de BD en réponse JSON.

---

## Étape 6 — L'app FastAPI et ses endpoints

### Les endpoints

| Méthode | Route | Rôle | Code HTTP |
|---|---|---|---|
| `GET` | `/` | Health check | 200 |
| `POST` | `/reports` | Créer un rapport | **202** Accepted |
| `GET` | `/reports` | Lister | 200 |
| `GET` | `/reports/{id}` | Détail | 200 ou 404 |
| `GET` | `/reports/{id}/status` | Statut léger (polling) | 200 ou 404 |

### Action · `app/main.py`

```python
"""
Application FastAPI — point d'entrée HTTP.
"""
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.config import settings
from app.database import get_db
from app.models import Report
from app.schemas import ReportCreate, ReportResponse, ReportStatusResponse

logger = logging.getLogger(__name__)


app = FastAPI(
    title=settings.app_name,
    description="API de génération de rapports asynchrones via Celery",
    version="0.1.0",
    debug=settings.debug,
)


@app.get("/", tags=["health"])
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "0.1.0",
    }


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
    report = Report(
        title=payload.title,
        parameters=payload.parameters,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Déclencher la tâche Celery
    from app.tasks import generate_report
    generate_report.delay(report.id)
    logger.info(f"📨 Tâche Celery envoyée pour le rapport {report.id}")

    return report


@app.get("/reports", response_model=List[ReportResponse], tags=["reports"])
def list_reports(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    return (
        db.query(Report)
        .order_by(Report.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@app.get(
    "/reports/{report_id}",
    response_model=ReportResponse,
    tags=["reports"],
    responses={404: {"description": "Rapport introuvable"}},
)
def get_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if report is None:
        raise HTTPException(status_code=404, detail=f"Rapport {report_id} introuvable")
    return report


@app.get(
    "/reports/{report_id}/status",
    response_model=ReportStatusResponse,
    tags=["reports"],
    responses={404: {"description": "Rapport introuvable"}},
)
def get_report_status(report_id: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    return report
```

---

> 💬 **Q&A : Quand utiliser 200 vs 201 vs 202 ?**
>
> | Code | Sémantique | Quand l'utiliser |
> |---|---|---|
> | **200 OK** | "Tout s'est bien passé" | Lectures, updates synchrones, actions sync |
> | **201 Created** | "La ressource est créée, prête, utilisable" | Créations **synchrones** complètes |
> | **202 Accepted** | "J'ai accepté, je traiterai plus tard" | Créations **asynchrones** ⭐ notre cas |
> | **204 No Content** | "Succès, rien à renvoyer" | Delete sans corps |
>
> **Règle mnémotechnique** :
> - 200 = "voici ta donnée"
> - 201 = "ta chose **existe** maintenant"
> - 202 = "je m'en **occupe**"
> - 204 = "c'est fait, rien à dire"

---

> 💬 **Q&A : `response_model`, c'est juste le type de retour ?**
>
> Oui mais **bien plus** ! C'est un paramètre qui fait **5 choses** :
>
> 1. **Filtrage** 🔒 — FastAPI ne renvoie QUE les champs déclarés dans `response_model`, peu importe ce que ta fonction retourne. Protection contre les fuites de données.
> 2. **Validation de sortie** ✅ — Si ta fonction retourne un objet mal formé, erreur 500 côté serveur.
> 3. **Documentation Swagger** 📖 — La doc affiche la forme exacte de la réponse.
> 4. **Conversion automatique** 🔄 — Via `from_attributes=True`, un objet SQLAlchemy est converti en schema Pydantic.
> 5. **Génération de SDK client** 🛠️ — Les types TypeScript générés depuis OpenAPI en dépendent.
>
> **`response_model=X` vs `-> X`** : les deux fonctionnent, mais `response_model=X` est **plus flexible** car ta fonction peut retourner un type différent (ex: objet SQLAlchemy) et FastAPI fait la conversion.

---

> 💬 **Q&A : À quoi sert `status_code` ?**
>
> C'est le **code HTTP par défaut renvoyé en cas de succès**. Par défaut, 200. Si tu veux autre chose (201, 202, 204), tu le précises.
>
> ```python
> @app.post("/reports", status_code=status.HTTP_202_ACCEPTED)
> ```
>
> Deux façons d'écrire :
> - `status_code=202` (nombre brut)
> - `status_code=status.HTTP_202_ACCEPTED` (constante lisible, **préférée en pro**)
>
> ⚠️ `status_code` c'est le **chemin heureux**. Les `HTTPException(status_code=404, ...)` **overrident** ce code pour les cas d'erreur.

---

> 💬 **Q&A : Différence entre `status_code` et `responses` ?**
>
> | | `status_code` | `responses` |
> |---|---|---|
> | Nature | Paramètre **comportemental** | Paramètre **documentaire** |
> | Effet sur l'exécution | ✅ Change le code réel renvoyé | ❌ Aucun |
> | Effet sur Swagger | ✅ Affiche ce code comme "succès" | ✅ Affiche d'autres codes possibles |
> | Accepte combien de codes ? | **1 seul** (le succès) | **Plusieurs** (dict) |
> | Quand on le met | Chemin heureux | Erreurs possibles |
>
> **En clair** : `status_code` définit ce que fait ton endpoint, `responses` documente ce qu'il peut retourner d'autre. L'un agit, l'autre raconte.
>
> **Cohérence** : si deux endpoints ont la même logique d'erreur (ex: lookup par ID qui peut 404), ils doivent documenter ça de la même façon dans `responses`.

---

### Test en local (avant Docker)

```bash
POSTGRES_USER=dev POSTGRES_PASSWORD=dev POSTGRES_DB=dev \
POSTGRES_HOST=localhost POSTGRES_PORT=5432 \
REDIS_HOST=localhost REDIS_PORT=6379 \
python -m uvicorn app.main:app --reload
```

> 💡 **Utilise `python -m uvicorn`** plutôt que `uvicorn` direct pour éviter les conflits entre installations Python (voir [Récapitulatif des difficultés](#-récapitulatif-des-difficultés-rencontrées), difficulté #2).

Puis ouvre :
- http://localhost:8000/ → health check
- http://localhost:8000/docs → **Swagger UI** 🎨
- http://localhost:8000/redoc → doc alternative

Les endpoints qui touchent la BD planteront avec une erreur 500 (normal, la BD arrive à l'étape 8).

---

## Étape 7 — Celery : le cerveau des tâches en arrière-plan

### Les 3 rôles dans Celery

```
Producer (FastAPI) ──push──▶ Broker (Redis) ──pull──▶ Worker (Celery)
                                                           │
                                                           ▼
                                                   generate_report()
```

### Action 1 · `app/worker.py`

```python
"""
Instance Celery — le "moteur" des tâches asynchrones.
"""
from celery import Celery

from app.config import settings


celery_app = Celery(
    "reports_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)


celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Paris",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,          # Tue une tâche > 5 min
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)
```

### Action 2 · `app/tasks.py`

```python
"""
Tâches Celery.
"""
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


@celery_app.task(
    name="app.tasks.generate_report",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def generate_report(self, report_id: str) -> dict:
    """
    Génère un PDF en arrière-plan.
    Cycle : PENDING → PROCESSING → COMPLETED (ou FAILED)
    """
    logger.info(f"🏁 Démarrage de la génération du rapport {report_id}")
    db = SessionLocal()

    try:
        # 1. Marquer PROCESSING
        report = db.query(Report).filter(Report.id == report_id).first()
        if report is None:
            logger.error(f"❌ Rapport {report_id} introuvable")
            return {"status": "failed", "reason": "not_found"}

        report.status = ReportStatus.PROCESSING
        db.commit()

        # 2. Faire le boulot
        logger.info(f"📊 Traitement de '{report.title}'...")
        time.sleep(30)   # simule une opération lourde

        reports_dir = Path(settings.reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)

        file_path = reports_dir / f"report_{report.id}.pdf"
        _generate_pdf(file_path, report)

        # 3. Marquer COMPLETED
        report.status = ReportStatus.COMPLETED
        report.file_path = str(file_path)
        report.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"✅ Rapport {report_id} généré : {file_path}")
        return {"status": "completed", "file_path": str(file_path)}

    except Exception as exc:
        logger.exception(f"💥 Erreur rapport {report_id}")
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.status = ReportStatus.FAILED
            report.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc, countdown=10)

    finally:
        db.close()


def _generate_pdf(file_path: Path, report: Report) -> None:
    """Génère un PDF simple."""
    c = canvas.Canvas(str(file_path), pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 80, report.title)

    c.setFont("Helvetica", 11)
    c.drawString(50, height - 120, f"ID : {report.id}")
    c.drawString(50, height - 140, f"Généré le : {datetime.utcnow().isoformat()}")

    c.drawString(50, height - 180, "Paramètres :")
    y = height - 200
    for key, value in report.parameters.items():
        c.drawString(70, y, f"• {key} : {value}")
        y -= 20

    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y - 40, "Résumé exécutif")
    c.setFont("Helvetica", 10)
    c.drawString(50, y - 60, "Rapport de démonstration FastAPI + Celery.")

    c.showPage()
    c.save()
```

### Points clés

- **`bind=True`** : accès à `self` (retries, task_id)
- **Session dédiée au worker** : on utilise `SessionLocal()` directement, pas `get_db()` (qui est pour FastAPI)
- **Cycle explicite** : statut mis à jour à chaque étape → le client voit la progression
- **Retry automatique** : en cas d'erreur, 3 tentatives espacées de 10 secondes

---

## Étape 8 — Docker Compose : orchestrer l'écosystème

### Action 1 · `Dockerfile`

```dockerfile
# syntax=docker/dockerfile:1.6
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc \
      libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini* ./

RUN mkdir -p /app/reports

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Action 2 · `docker-compose.yml`

```yaml
services:
  db:
    image: postgres:16-alpine
    container_name: reports_db
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: reports_redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build: .
    container_name: reports_api
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    env_file: .env
    volumes:
      - ./app:/app/app
      - ./alembic:/app/alembic
      - ./alembic.ini:/app/alembic.ini
      - reports_data:/app/reports
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    build: .
    container_name: reports_worker
    command: celery -A app.worker.celery_app worker --loglevel=info --concurrency=2
    env_file: .env
    volumes:
      - ./app:/app/app
      - ./alembic.ini:/app/alembic.ini
      - reports_data:/app/reports
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  flower:
    build: .
    container_name: reports_flower
    command: celery -A app.worker.celery_app flower --port=5555
    env_file: .env
    ports:
      - "5555:5555"
    depends_on:
      - redis
      - worker

volumes:
  postgres_data:
  reports_data:
```

### Action 3 · Lancer l'écosystème

```bash
docker compose up --build -d
docker compose ps
```

Tu dois voir 5 services `Up` ou `Up (healthy)`.

---

> 💬 **Q&A : Pourquoi `environment` pour `db` et `env_file` pour `api` ?**
>
> Le fichier `.env` sert **deux fois**, à **deux niveaux différents** :
>
> | Emplacement | Qui le lit ? | Ce qu'il fait |
> |---|---|---|
> | `.env` à côté de `docker-compose.yml` | Docker Compose | Remplit les `${VARIABLES}` dans le YAML |
> | `env_file: .env` sous un service | Le conteneur | Injecte TOUTES les variables à l'intérieur |
>
> **Pour `db`** : on utilise `environment` avec `${POSTGRES_USER}`. Compose résout les 3 variables **pour son propre YAML**, puis elles sont passées au conteneur postgres qui n'a besoin que de celles-là.
>
> **Pour `api`** : on utilise `env_file: .env`. Toutes les variables du `.env` sont injectées d'un coup dans le conteneur — plus concis que lister 10 lignes.
>
> **Test de vérification** :
> ```bash
> docker compose exec api env | grep -E "POSTGRES|REDIS"  # nombreuses
> docker compose exec db env | grep -i postgres            # juste 3
> ```

---

### Les 3 URLs utiles

| URL | Quoi |
|---|---|
| http://localhost:8000/docs | Swagger UI de l'API |
| http://localhost:5555/ | Flower (monitoring Celery) |
| http://localhost:8000/ | Health check |

---

## Étape 9 — Alembic : les migrations de schéma

### Pourquoi Alembic ?

C'est le **Git de ton schéma de base**. Chaque modification est un fichier Python versionné, réversible (`upgrade` / `downgrade`), et chaîné avec les précédents.

### Action 1 · Initialiser Alembic

```bash
# Avant toute chose, s'assurer que ./alembic existe côté host
mkdir -p alembic

# Lancer init dans le conteneur
docker compose exec api alembic init alembic
```

> ⚠️ **Piège potentiel** : si tu as supprimé `./alembic` sur ton host avant cette commande, elle plante. Le bind mount rend invisible le dossier côté conteneur. **Crée toujours le dossier host d'abord** (voir [difficulté #4](#-récapitulatif-des-difficultés-rencontrées)).

### Action 2 · Récupérer `alembic.ini` si besoin

Si `alembic.ini` apparaît seulement dans le conteneur mais pas côté host :

```bash
docker compose cp api:/app/alembic.ini ./alembic.ini
```

Et vérifie que le `docker-compose.yml` contient bien le bind mount `./alembic.ini:/app/alembic.ini` pour les services `api` et `worker` (voir [difficulté #5](#-récapitulatif-des-difficultés-rencontrées)).

### Action 3 · Configurer `alembic.ini`

Commente la ligne :

```ini
# sqlalchemy.url = driver://user:pass@localhost/dbname
```

On injectera l'URL dynamiquement depuis `config.py`.

### Action 4 · Configurer `alembic/env.py`

Ouvre le fichier et apporte **3 modifications** :

**1. Ajouter les imports** (après `from alembic import context`) :

```python
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.database import Base
from app import models  # noqa: F401
```

**2. Injecter l'URL dynamique** (après `config = context.config`) :

```python
config.set_main_option("sqlalchemy.url", settings.database_url)
```

**3. Brancher `target_metadata`** (remplace `target_metadata = None`) :

```python
target_metadata = Base.metadata
```

### Action 5 · Générer la première migration

```bash
docker compose exec api alembic revision --autogenerate -m "create reports table"
```

Tu verras :
```
INFO  [alembic.autogenerate.compare] Detected added table 'reports'
  Generating /app/alembic/versions/xxxx_create_reports_table.py ...  done
```

**Ouvre le fichier généré dans `alembic/versions/`** pour vérifier que la migration est correcte avant de l'appliquer.

### Action 6 · Appliquer la migration

```bash
docker compose exec api alembic upgrade head
```

### Vérification en BD

```bash
docker compose exec db psql -U reports_user -d reports_db -c "\dt"
```

Tu dois voir les tables `reports` et `alembic_version`.

### Commandes Alembic utiles

| Commande | Quand l'utiliser |
|---|---|
| `alembic revision --autogenerate -m "msg"` | Modèle changé → générer la migration |
| `alembic upgrade head` | Appliquer les migrations en attente |
| `alembic downgrade -1` | Annuler la dernière migration |
| `alembic current` | Voir la migration actuelle |
| `alembic history` | Liste toutes les migrations |

---

## 🧪 Test de bout en bout

### 1. Créer un rapport

```bash
curl -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -d '{"title": "Mon premier rapport", "parameters": {"year": 2026}}'
```

Réponse : code **202** avec un `id`. Copie-le.

### 2. Suivre le worker en direct

```bash
docker compose logs -f worker
```

Tu verras :
```
🏁 Démarrage de la génération du rapport xxx
📊 Traitement du rapport 'Mon premier rapport'...
(30 secondes)
✅ Rapport xxx généré : /app/reports/report_xxx.pdf
```

### 3. Poller le statut

```bash
curl http://localhost:8000/reports/{id}/status
```

Progression : `pending` → `processing` → `completed`.

### 4. Récupérer le PDF

```bash
docker compose cp api:/app/reports/report_xxx.pdf ./
```

### 5. Monitoring dans Flower

Ouvre http://localhost:5555/ → onglet "Tasks" → tu vois ta tâche, son statut, sa durée, ses arguments. 🌸

---

## 📚 Récapitulatif des difficultés rencontrées

### 🐛 Difficulté #1 — `ModuleNotFoundError: No module named 'sqlalchemy'`

**Symptôme** : erreur à l'import alors que `pip install` a marché.

**Cause** : venv non activé dans le terminal.

**Solution** :
```bash
source venv/bin/activate
which python  # doit pointer vers venv/bin/python
```

**Leçon** : les venvs sont locaux au shell courant. Réflexe : `source venv/bin/activate` à chaque nouveau terminal.

---

### 🐛 Difficulté #2 — Uvicorn utilisait le mauvais Python

**Symptôme** : même erreur `ModuleNotFoundError` malgré venv actif et paquet installé.

**Cause** : `uvicorn` installé dans le venv de Poetry via pipx, trouvé en premier dans le `PATH`. Le sous-processus utilisait donc un Python qui n'avait pas SQLAlchemy.

**Solution** :
```bash
python -m uvicorn app.main:app --reload
```

**Leçon** : sur Mac avec plusieurs Python (système, Homebrew, pyenv, pipx, venv), `python -m <module>` force l'utilisation du Python courant. **Toujours préférer `python -m`** pour les modules.

---

### 🐛 Difficulté #3 — Flower : `No such command 'flower'`

**Symptôme** : au démarrage Docker, le service `flower` plante.

**Cause** : Flower est une lib séparée de Celery, oubliée dans `requirements.txt`.

**Solution** :
```txt
# Ajouter dans requirements.txt
flower==2.0.1
```
Puis :
```bash
docker compose down
docker compose up --build -d
```

**Leçon** : modifier `requirements.txt` → toujours **rebuild** (`--build`). Docker cache agressivement.

---

### 🐛 Difficulté #4 — `alembic init` plante sur `versions/`

**Symptôme** :
```
FileNotFoundError: [Errno 2] No such file or directory: 'alembic/versions'
```

**Cause** : `rm -rf alembic` côté host a supprimé le dossier que le bind mount remontait dans le conteneur. Alembic ne pouvait pas créer `versions/` dans un dossier inexistant.

**Solution** :
```bash
mkdir -p alembic
docker compose exec api alembic init alembic
```

**Leçon** : **les bind mounts sont bidirectionnels**. Supprimer côté host = supprimer côté conteneur.

---

### 🐛 Difficulté #5 — `alembic.ini` dans le conteneur mais pas sur le host

**Symptôme** :
```bash
docker compose exec api ls    # alembic.ini présent
ls                             # alembic.ini absent
```

**Cause** : les bind mounts configurés couvraient `./app` et `./alembic`, mais pas le fichier `/app/alembic.ini` à la racine du conteneur.

**Solution** :
1. Récupérer le fichier :
   ```bash
   docker compose cp api:/app/alembic.ini ./alembic.ini
   ```
2. Ajouter un bind mount pour le fichier dans `docker-compose.yml` :
   ```yaml
   volumes:
     - ./alembic.ini:/app/alembic.ini
   ```
3. Redémarrer :
   ```bash
   docker compose down && docker compose up -d
   ```

**Leçon** : **les bind mounts sont sélectifs**. Seul ce qui est explicitement monté est synchronisé.

---

### 🎯 Les 3 méta-leçons

1. **L'environnement Python sur Mac est souvent brouillé.** Entre Python système, Homebrew, pyenv, pipx et les venvs, ton shell peut piocher le mauvais interpréteur. Réflexes : `which python` avant de douter, `python -m <module>`, `source venv/bin/activate` systématique.

2. **Les bind mounts Docker = miroir bidirectionnel ET sélectif.** Bidirectionnel : ce qui se passe d'un côté se reflète de l'autre. Sélectif : seul ce que tu montes est synchronisé, le reste est volatile.

3. **Modifier une dépendance ≠ modifier du code.** Changer `requirements.txt`, `Dockerfile` ou la structure d'une image nécessite un **rebuild** (`--build`). En cas de doute : `docker compose up --build`.

---

## 🎓 Pour aller plus loin

Quelques pistes naturelles pour enrichir le projet :

- **Endpoint de téléchargement** : `GET /reports/{id}/download` qui retourne le PDF via `FileResponse`
- **Endpoint de retry** : `POST /reports/{id}/retry` pour relancer un rapport `FAILED`
- **Tests** : pytest + httpx + fixtures Docker (voir `pytest-docker`)
- **Authentification** : ajouter JWT ou OAuth2 via `fastapi-users`
- **Websockets** : notifier le client en temps réel quand le rapport est prêt
- **Celery Beat** : planifier des rapports récurrents (cron)
- **Plusieurs queues** : prioriser certaines tâches (urgent/normal/batch)
- **Observabilité** : Prometheus + Grafana, ou Sentry pour les erreurs
- **Dockerfile multi-stage** : builder une image plus petite pour la prod
- **User non-root** dans le `Dockerfile` pour la sécurité
- **CI/CD** : GitHub Actions qui lance les tests à chaque push

---

## 📝 Licence

Ce tutoriel est partagé sous licence MIT. Utilise-le, modifie-le, partage-le librement.

---

**Fait avec ❤️ et beaucoup de questions pertinentes 🤔**
