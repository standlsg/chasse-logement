#!/usr/bin/env bash
# Déploiement manuel sur un VPS :  ./deploy/deploy.sh user@host.example.com [/var/www/chasse-logement]
# Prérequis côté serveur : docker + git, le dépôt cloné une fois dans la destination,
# et .env + config.yaml placés manuellement (JAMAIS commités).
set -euo pipefail

HOST="${1:?usage: deploy.sh user@host [dest]}"
DEST="${2:-/var/www/chasse-logement}"

echo "==> sync du code vers $HOST:$DEST"
rsync -az --delete \
  --exclude .git --exclude .venv --exclude data --exclude .env --exclude __pycache__ \
  ./ "$HOST:$DEST/"

echo "==> redémarrage des conteneurs"
ssh "$HOST" "cd '$DEST' && docker compose -f deploy/docker-compose.prod.yml up -d --build"

echo "==> OK. UI : https://\${DOMAIN:-<host>}/  (basic auth) — health: /healthz"
