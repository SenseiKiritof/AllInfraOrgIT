#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META_ROOT="$(cd "$HERE/.." && pwd)"
DOCKER_DIR="$META_ROOT/../InfraOrgITDocker"

# shellcheck disable=SC1091
source "$META_ROOT/scripts/env.sh"

cd "$DOCKER_DIR"
# Se lo stack completo è attivo, ferma API e web prima di tornare alla modalità dev.
docker compose stop api web >/dev/null 2>&1 || true
KC_MODE=dev docker compose up -d --wait mysql mysql-keycloak keycloak
cd "$META_ROOT"

dotnet tool restore >/dev/null
dotnet tool run dotnet-ef database update \
  --project "$META_ROOT/../InfraOrgITApi/src/InfraOrgIt.Api" \
  --startup-project "$META_ROOT/../InfraOrgITApi/src/InfraOrgIt.Api" >/dev/null

dotnet run --project "$META_ROOT/../InfraOrgITApi/src/InfraOrgIt.Api" --no-launch-profile &
api_pid=$!
yarn --cwd "$META_ROOT/../InfraOrgITWeb" dev &
web_pid=$!

cleanup() {
  kill "$api_pid" "$web_pid" 2>/dev/null || true
  wait "$api_pid" "$web_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# bash 3.2 (macOS) non ha `wait -n`: si esce al primo dei due processi che termina.
while kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null; do sleep 1; done
