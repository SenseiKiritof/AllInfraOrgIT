#!/usr/bin/env bash
# Backup coerente di MySQL applicativo e Keycloak. Nessun segreto nel dump oltre ai dati.
set -euo pipefail
umask 077

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META_ROOT="$(cd "$HERE/.." && pwd)"
DOCKER_DIR="$META_ROOT/../InfraOrgITDocker"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DIR="${BACKUP_DIR:-$META_ROOT/backups/$STAMP}"

mkdir -p "$DIR"
chmod 700 "$DIR"

dump() {
  local service="$1" database="$2" file="$3"
  docker compose -f "$DOCKER_DIR/compose.yaml" exec -T "$service" \
    sh -c 'exec mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" \
      --single-transaction --routines --triggers --databases "$0"' "$database" \
    | gzip > "$DIR/$file"
}

dump mysql infraorgit infraorgit.sql.gz
dump mysql-keycloak keycloak keycloak.sql.gz

{
  echo "created_at=$STAMP"
  echo "project=${COMPOSE_PROJECT_NAME:-infraorgit}"
  docker compose -f "$DOCKER_DIR/compose.yaml" images
} > "$DIR/manifest.txt"

echo "Backup in $DIR"
ls -lh "$DIR"
