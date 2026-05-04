# syntax=docker/dockerfile:1.6

# =========================================================
#  STAGE 1 : BUILDER — compile les deps Python
# =========================================================
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Outils de compilation pour psycopg2 etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc \
      libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Créer un venv isolé pour les deps Python
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installer les deps Python dans le venv
# TODO : pensez à utiliser UV pour l'installation des dépendances, c'est plus rapide et plus fiable que pip dans un Dockerfile

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt


# =========================================================
#  STAGE 2 : RUNTIME — image finale légère
# =========================================================
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Libs runtime :
#  - libpq5 : pour psycopg2
#  - gosu   : pour basculer en non-root depuis l'entrypoint
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpq5 \
      gosu \
    && rm -rf /var/lib/apt/lists/*

# Créer un user non-root
RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --create-home --shell /bin/bash appuser

# Copier le venv depuis le stage builder
COPY --from=builder /opt/venv /opt/venv

# Créer le dossier reports
RUN mkdir -p /app/reports

# Copier le code
COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini* ./

# Copier l'entrypoint
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Donner la propriété à appuser
RUN chown -R appuser:appgroup /app /opt/venv

# ⚠️ PAS DE `USER appuser` ici !
# On reste root pour que l'entrypoint puisse chown le volume.
# La bascule en appuser se fait DANS l'entrypoint via gosu.

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]