"""
Instance Celery — le "moteur" qui orchestre les tâches asynchrones.
"""
from celery import Celery

from app.config import settings


# =========================================================
#  Instance Celery
# =========================================================
celery_app = Celery(
    "reports_worker",                  # Nom du worker
    broker=settings.redis_url,         # Où pusher les tâches (Redis)
    backend=settings.redis_url,        # Où stocker les résultats (Redis aussi)
    include=["app.tasks"],             # Où trouver les tâches déclarées
)


# =========================================================
#  Configuration Celery
# =========================================================
celery_app.conf.update(
    # --- Sérialisation ---
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # --- Timezone ---
    timezone="Europe/Paris",
    enable_utc=True,

    # --- Comportement des tâches ---
    task_track_started=True,           # Statut "STARTED" visible quand une tâche commence
    task_time_limit=300,               # Kill une tâche qui dépasse 5 min (sécurité)
    task_soft_time_limit=240,          # Avertit la tâche à 4 min (elle peut nettoyer)

    # --- Worker ---
    worker_prefetch_multiplier=1,      # Prend 1 tâche à la fois (pas de greedy prefetch)
    worker_max_tasks_per_child=100,    # Recycle le worker tous les 100 tâches (anti fuites mémoire)
)