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

# Lib runtime pour psycopg2 (libpq, version "simple", pas "-dev")
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Créer un user non-root
RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --create-home --shell /bin/bash appuser

# Copier le venv depuis le stage builder
COPY --from=builder /opt/venv /opt/venv

# Créer le dossier reports (en root)
RUN mkdir -p /app/reports

# Copier le code
COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini* ./

# Donner la propriété à appuser
RUN chown -R appuser:appgroup /app /opt/venv

# Bascule en non-root
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]