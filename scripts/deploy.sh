#!/usr/bin/env bash
# Déploiement de LOGOS sur le VPS : sauvegarde -> mise à jour du code -> reconstruction -> vérification.
# Usage (sur le serveur) : bash /root/logos/scripts/deploy.sh [branche]
set -Eeuo pipefail

BRANCH="${1:-main}"
APP_DIR="${APP_DIR:-/root/logos}"
URL="${SITE_CHECK_URL:-https://logos.djokodev.com/}"
cd "${APP_DIR}"

echo "==> 1/5 Sauvegarde de sécurité avant déploiement"
if docker compose ps --status running --services 2>/dev/null | grep -q '^db$'; then
  bash scripts/backup/backup_weekly.sh
else
  echo "    (base non démarrée : sauvegarde ignorée)"
fi

echo "==> 2/5 Récupération du code (${BRANCH})"
git fetch --prune origin
git checkout "${BRANCH}"
git pull --ff-only origin "${BRANCH}"
git log --oneline -1

echo "==> 3/5 Construction de l'image"
docker compose build web

echo "==> 4/5 Redémarrage (migrations + fichiers statiques automatiques)"
docker compose up -d --remove-orphans
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: logos.djokodev.com' -H 'X-Forwarded-Proto: https' http://127.0.0.1:8082/ || true)
  [[ "${code}" == "200" ]] && break
  sleep 2
done

echo "==> 5/5 Vérification"
docker compose ps
curl -s -o /dev/null -w "Accueil public : %{http_code}\n" "${URL}"
docker image prune -f > /dev/null
echo "Déploiement terminé."
