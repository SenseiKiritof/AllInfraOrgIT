#!/usr/bin/env bash
# Carica le variabili di sviluppo condivise con il Compose.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META_ROOT="$(cd "$HERE/.." && pwd)"
DOCKER_DIR="$META_ROOT/../infraorgit-docker"

if [ ! -f "$DOCKER_DIR/.env" ]; then
  cp "$DOCKER_DIR/.env.example" "$DOCKER_DIR/.env"
fi

set -a
# shellcheck disable=SC1091
source "$DOCKER_DIR/.env"
set +a

export ASPNETCORE_ENVIRONMENT="${ASPNETCORE_ENVIRONMENT:-Development}"
export ASPNETCORE_URLS="${ASPNETCORE_URLS:-http://localhost:5298}"
export ConnectionStrings__MySql="Server=localhost;Port=3306;Database=infraorgit;User ID=infraorgit;Password=${MYSQL_PASSWORD};"
export Oidc__ClientSecret="${Oidc__ClientSecret:-${OIDC__CLIENT_SECRET:-dev-client-secret}}"
