#!/usr/bin/env bash
# Preflight for the image-based deploy stack.
#
# Refuses missing values, CHANGE_ME placeholders and the development secrets
# that were previously shipped in deploy/.env.example. It only reads the file:
# no value is printed, no stack is started.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
ENV_FILE="${1:-$ROOT/.env}"

if [ "$#" -gt 1 ]; then
  echo "Uso: $0 [file-env]" >&2
  exit 2
fi

fail() {
  printf 'check-env: %s\n' "$*" >&2
  exit 1
}

warn() {
  printf 'check-env: avviso: %s\n' "$*" >&2
}

[ -f "$ENV_FILE" ] || fail "file non trovato: $ENV_FILE (copiare deploy/.env.example in deploy/.env)"

case "$(uname -s)" in
  Darwin) mode="$(stat -f '%Lp' "$ENV_FILE" 2>/dev/null || true)" ;;
  *) mode="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || true)" ;;
esac
case "$mode" in
  400|600|"") ;;
  *) warn "permessi $mode su $ENV_FILE: usare chmod 600 $ENV_FILE" ;;
esac

# Read KEY=VALUE without sourcing the file. Compose-style quotes and an
# optional "export " prefix are accepted; comments and blank lines are skipped.
get_value() {
  awk -v wanted="$1" '
    { sub(/\r$/, "") }
    /^[[:space:]]*#/ { next }
    /^[[:space:]]*$/ { next }
    {
      line = $0
      sub(/^[[:space:]]*export[[:space:]]+/, "", line)
      eq = index(line, "=")
      if (eq == 0) next
      key = substr(line, 1, eq - 1)
      gsub(/[[:space:]]/, "", key)
      if (key != wanted) next
      value = substr(line, eq + 1)
      if (value ~ /^".*"$/) value = substr(value, 2, length(value) - 2)
      else if (value ~ /^\047.*\047$/) value = substr(value, 2, length(value) - 2)
      print value
      exit
    }
  ' "$ENV_FILE"
}

check_placeholder() {
  name=$1
  value=$2
  case "$value" in
    *CHANGE_ME*|*change_me*|*Change_Me*|*CHANGEME*|*changeme*)
      fail "$name contiene un placeholder CHANGE_ME: generare un valore reale" ;;
  esac
}

require_value() {
  name=$1
  minimum=$2
  value="$(get_value "$name")"
  [ -n "$value" ] || fail "$name mancante o vuota in $ENV_FILE"
  check_placeholder "$name" "$value"
  case "$value" in
    dev-*|*-dev|admin|password|secret|changeme|test)
      fail "$name usa un valore di sviluppo o generico noto: generare un valore reale" ;;
  esac
  [ "${#value}" -ge "$minimum" ] ||
    fail "$name troppo corta (${#value} caratteri, minimo $minimum)"
}

require_value MYSQL_PASSWORD 16
require_value MYSQL_ROOT_PASSWORD 16
require_value KEYCLOAK_DB_PASSWORD 16
require_value KEYCLOAK_DB_ROOT_PASSWORD 16
require_value KEYCLOAK_ADMIN_PASSWORD 16
require_value INFRAORGIT_ADMIN_PASSWORD 16
require_value Oidc__ClientSecret 24
require_value MCP_CLIENT_SECRET 24

# Mirror the realm password policy for the templated bootstrap administrator:
# deploy/keycloak/realm-infraorgit.json sets length(12), upperCase(1),
# lowerCase(1), digits(1), specialChars(1), notUsername and notEmail. Keycloak
# enforces the policy on password changes, but import-time validation of the
# seeded credential is not a reliable control (it depends on the Keycloak
# version and can fail the whole realm import), so reject a weak password here
# with a clear message before the container starts. The imported user is "admin"
# with email "admin@example.invalid"; the length rule already makes those
# values unusable, the explicit checks keep the preflight aligned with the
# realm if the policy changes.
check_admin_password_policy() {
  name=INFRAORGIT_ADMIN_PASSWORD
  value="$(get_value "$name")"
  missing=""
  [ "${#value}" -ge 12 ] || missing="$missing length(12)"
  case "$value" in *[A-Z]*) ;; *) missing="$missing upperCase(1)" ;; esac
  case "$value" in *[a-z]*) ;; *) missing="$missing lowerCase(1)" ;; esac
  case "$value" in *[0-9]*) ;; *) missing="$missing digits(1)" ;; esac
  case "$value" in *[[:punct:]]*) ;; *) missing="$missing specialChars(1)" ;; esac
  lower="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"
  [ "$lower" != "admin" ] || missing="$missing notUsername"
  [ "$lower" != "admin@example.invalid" ] || missing="$missing notEmail"
  [ -z "$missing" ] ||
    fail "$name non rispetta la password policy del realm:$missing (generare con openssl rand -base64 32)"
}

check_admin_password_policy

[ "$(get_value Oidc__ClientSecret)" != "$(get_value MCP_CLIENT_SECRET)" ] ||
  fail "Oidc__ClientSecret e MCP_CLIENT_SECRET devono essere diversi"

credential_key="$(get_value ServerAccess__CredentialKey)"
[ -n "$credential_key" ] || fail "ServerAccess__CredentialKey mancante o vuota in $ENV_FILE"
check_placeholder ServerAccess__CredentialKey "$credential_key"
case "$credential_key" in
  YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=)
    fail "ServerAccess__CredentialKey e la chiave di sviluppo nota (32 byte 'a'): generarne una nuova" ;;
esac
[ "${#credential_key}" -eq 44 ] ||
  fail "ServerAccess__CredentialKey deve essere base64 di 32 byte (44 caratteri): openssl rand -base64 32"
case "$credential_key" in
  *=) ;;
  *) fail "ServerAccess__CredentialKey non e base64 valido: openssl rand -base64 32" ;;
esac
command -v openssl >/dev/null 2>&1 || fail "openssl richiesto per verificare ServerAccess__CredentialKey"
decoded_len="$(printf '%s' "$credential_key" | openssl base64 -d -A 2>/dev/null | wc -c | tr -d '[:space:]')" ||
  fail "ServerAccess__CredentialKey non e base64 valido"
[ "$decoded_len" -eq 32 ] ||
  fail "ServerAccess__CredentialKey deve decodificare a 32 byte (trovati $decoded_len): openssl rand -base64 32"

# Image tags are part of the deploy input. A fresh .env must make an explicit
# choice, and a mutable branch tag is refused unless the exact manifest is
# pinned by digest: deploy must be reproducible.
check_digest() {
  name=$1
  value="$(get_value "$name")"
  [ -n "$value" ] || return 0
  check_placeholder "$name" "$value"
  [[ "$value" =~ ^sha256:[0-9a-f]{64}$ ]] ||
    fail "$name deve essere un digest sha256 completo (sha256:<64 hex>), non '$value'"
}

require_tag() {
  name=$1
  digest_name=$2
  value="$(get_value "$name")"
  [ -n "$value" ] || fail "$name mancante in $ENV_FILE (usare una versione X.Y.Z o sha-<commit>)"
  check_placeholder "$name" "$value"
  case "$value" in
    main|dev|latest)
      [ -n "$(get_value "$digest_name")" ] ||
        fail "$name=$value e un tag mobile: usare una versione X.Y.Z/sha-<commit> oppure impostare $digest_name=sha256:<64 hex>"
      ;;
  esac
}

check_digest API_DIGEST
check_digest WEB_DIGEST
require_tag API_TAG API_DIGEST
require_tag WEB_TAG WEB_DIGEST

web_bind="$(get_value WEB_BIND)"
[ -n "$web_bind" ] || web_bind="127.0.0.1"
case "$web_bind" in
  127.0.0.1|::1|localhost) ;;
  *)
    warn "WEB_BIND=$web_bind espone la UI oltre il loopback: assicurarsi che sia intenzionale, con firewall e TLS validi"
    ;;
esac

keycloak_admin="$(get_value KEYCLOAK_ADMIN)"
[ -n "$keycloak_admin" ] || keycloak_admin="admin"
if [ "$keycloak_admin" = "admin" ]; then
  warn "KEYCLOAK_ADMIN resta 'admin': il nome e noto, la password deve essere unica e ruotata"
fi

printf 'check-env: OK (%s, WEB_BIND=%s)\n' "$ENV_FILE" "$web_bind"
