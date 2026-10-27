#!/usr/bin/env bash
# Ripristino distruttivo: sovrascrive database applicativo e Keycloak.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META_ROOT="$(cd "$HERE/.." && pwd)"
DOCKER_DIR="$META_ROOT/../infraorgit-docker"
DIR="${1:-}"

if [ -z "$DIR" ] || [ ! -d "$DIR" ]; then
  echo "Uso: CONFIRM_RESTORE=yes $0 <cartella-backup>" >&2
  exit 2
fi

if [ "${CONFIRM_RESTORE:-}" != "yes" ]; then
  echo "Ripristino bloccato: sovrascrive i database applicativo e Keycloak." >&2
  echo "Ferma prima API/Caddy/Keycloak e rilancia con CONFIRM_RESTORE=yes." >&2
  exit 1
fi

for file in infraorgit.sql.gz keycloak.sql.gz; do
  if [ ! -f "$DIR/$file" ]; then
    echo "File mancante: $DIR/$file" >&2
    exit 2
  fi
  if ! gzip -t "$DIR/$file"; then
    echo "Dump corrotto: $DIR/$file" >&2
    exit 2
  fi
done

running="$(docker compose -f "$DOCKER_DIR/compose.yaml" ps --services --status running 2>/dev/null || true)"
for service in api caddy keycloak; do
  if printf '%s\n' "$running" | grep -qx "$service"; then
    echo "Servizio $service ancora attivo: fermalo prima del restore." >&2
    exit 1
  fi
done

restore() {
  local service="$1" file="$2"
  gunzip -c "$DIR/$file" | docker compose -f "$DOCKER_DIR/compose.yaml" exec -T "$service" \
    sh -c 'exec mysql -u root -p"$MYSQL_ROOT_PASSWORD"'
}

restore mysql infraorgit.sql.gz
restore mysql-keycloak keycloak.sql.gz

echo "Ripristino completato da $DIR"
