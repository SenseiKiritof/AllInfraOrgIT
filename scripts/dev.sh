#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META_ROOT="$(cd "$HERE/.." && pwd)"
DOCKER_DIR="$META_ROOT/../infraorgit-docker"

cd "$DOCKER_DIR"
docker compose up -d --wait mysql mysql-keycloak keycloak

# shellcheck disable=SC1091
source "$META_ROOT/scripts/env.sh"
cd "$META_ROOT"

dotnet run --project "$META_ROOT/../infraorgit/src/InfraOrgIt.Api" --no-launch-profile &
api_pid=$!
yarn --cwd "$META_ROOT/../infraorgit-web" dev &
web_pid=$!

cleanup() {
  kill "$api_pid" "$web_pid" 2>/dev/null || true
  wait "$api_pid" "$web_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait -n "$api_pid" "$web_pid"
