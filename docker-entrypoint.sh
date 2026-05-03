#!/bin/bash
set -e

# Fixer les permissions du volume monté
# (s'exécute en root, autorisé par le USER root dans le Dockerfile)
if [ -d /app/reports ]; then
    chown -R appuser:appgroup /app/reports
fi

# Basculer en appuser et lancer la commande
exec gosu appuser "$@"