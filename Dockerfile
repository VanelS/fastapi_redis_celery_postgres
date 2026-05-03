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

# --- Dépendances système (en root) ---
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc \
      libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# --- Créer un utilisateur non-root ---
RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --create-home --shell /bin/bash appuser

# --- Créer le dossier reports MAINTENANT, en root ---
RUN mkdir -p /app/reports

# --- Installation des deps Python (en root, dans /usr/local) ---
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# --- Copier le code (toujours en root, sans --chown) ---
COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini* ./

# --- UNE SEULE opération chown en fin, pour tout /app ---
RUN chown -R appuser:appgroup /app

# --- Bascule en non-root pour les processus suivants ---
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]