#!/usr/bin/env bash
# Carica le variabili di sviluppo condivise con il Compose.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META_ROOT="$(cd "$HERE/.." && pwd)"
DOCKER_DIR="$META_ROOT/../InfraOrgITDocker"

if [ ! -f "$DOCKER_DIR/.env" ]; then
  cp "$DOCKER_DIR/.env.example" "$DOCKER_DIR/.env"
fi

# Chiave AES-GCM di sviluppo per le credenziali SSH: generata una volta, resta nel .env ignorato.
if ! grep -q '^ServerAccess__CredentialKey=' "$DOCKER_DIR/.env"; then
  key=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)
  printf 'ServerAccess__CredentialKey=%s\n' "$key" >> "$DOCKER_DIR/.env"
fi

set -a
# shellcheck disable=SC1091
source "$DOCKER_DIR/.env"
set +a

export ASPNETCORE_ENVIRONMENT="${ASPNETCORE_ENVIRONMENT:-Development}"
export ASPNETCORE_URLS="${ASPNETCORE_URLS:-http://localhost:5298}"
export ConnectionStrings__MySql="Server=localhost;Port=13336;Database=infraorgit;User ID=infraorgit;Password=${MYSQL_PASSWORD};"
export Oidc__ClientSecret="${Oidc__ClientSecret:-${OIDC__CLIENT_SECRET:-dev-client-secret}}"
export ServerAccess__CredentialKeys__1="${ServerAccess__CredentialKey:?ServerAccess__CredentialKey mancante}"
export ServerAccess__CurrentKeyVersion="${ServerAccess__CurrentKeyVersion:-1}"
