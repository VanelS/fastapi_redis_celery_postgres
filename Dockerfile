# syntax=docker/dockerfile:1.6

# =========================================================
#  Image de base : Python 3.11 slim (Debian minimal)
# =========================================================
FROM python:3.11-slim

# --- Variables d'environnement Python ---
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# --- Dossier de travail dans le conteneur ---
WORKDIR /app

# --- Dépendances système nécessaires à psycopg2 + reportlab ---
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc \
      libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# --- Copier et installer les deps Python (couche cachée si inchangé) ---
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# --- Copier le code de l'app ---
COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini* ./

# --- Créer le dossier de sortie des rapports ---
RUN mkdir -p /app/reports

# --- Exposer le port FastAPI (documentation, ne publie pas) ---
EXPOSE 8000

# --- Commande par défaut (sera overridée par docker-compose pour Celery/Flower) ---
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]