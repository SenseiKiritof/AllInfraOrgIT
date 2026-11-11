#!/bin/sh
# Keycloak entrypoint for the deploy stack.
#
# Renders the realm template with the secrets from the environment into a
# temporary import path, then starts Keycloak unchanged. The realm file in the
# repository contains placeholders only.
set -eu

template="${REALM_TEMPLATE:-/opt/keycloak/realm/realm-infraorgit.json}"
import_dir="${KEYCLOAK_IMPORT_DIR:-/opt/keycloak/data/import}"
target="$import_dir/realm.json"

fail() {
  printf 'keycloak-entrypoint: %s\n' "$*" >&2
  exit 1
}

: "${OIDC_CLIENT_SECRET:?OIDC_CLIENT_SECRET mancante}"
: "${MCP_CLIENT_SECRET:?MCP_CLIENT_SECRET mancante}"
: "${INFRAORGIT_ADMIN_PASSWORD:?INFRAORGIT_ADMIN_PASSWORD mancante}"

check_value() {
  name=$1
  value=$2
  [ -n "$value" ] || fail "$name vuota"
  case "$value" in
    *[![:print:]]*) fail "$name contiene caratteri di controllo o newline" ;;
    *__OIDC_CLIENT_SECRET__*|*__MCP_CLIENT_SECRET__*|*__ADMIN_PASSWORD__*)
      fail "$name contiene un token del template" ;;
  esac
}

check_value OIDC_CLIENT_SECRET "$OIDC_CLIENT_SECRET"
check_value MCP_CLIENT_SECRET "$MCP_CLIENT_SECRET"
check_value INFRAORGIT_ADMIN_PASSWORD "$INFRAORGIT_ADMIN_PASSWORD"

[ -f "$template" ] || fail "template non trovato: $template"
command -v sed >/dev/null 2>&1 || fail "sed non disponibile"

umask 077
mkdir -p "$import_dir"

# Escape for a JSON string, then for the sed replacement (delimiter |).
# This keeps values containing quotes, backslashes, ampersands or pipes valid.
json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

sed_replacement() {
  printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'
}

OIDC_CLIENT_SED="$(sed_replacement "$(json_escape "$OIDC_CLIENT_SECRET")")"
MCP_CLIENT_SED="$(sed_replacement "$(json_escape "$MCP_CLIENT_SECRET")")"
ADMIN_PASSWORD_SED="$(sed_replacement "$(json_escape "$INFRAORGIT_ADMIN_PASSWORD")")"

sed -e "s|__OIDC_CLIENT_SECRET__|$OIDC_CLIENT_SED|g" \
  -e "s|__MCP_CLIENT_SECRET__|$MCP_CLIENT_SED|g" \
  -e "s|__ADMIN_PASSWORD__|$ADMIN_PASSWORD_SED|g" \
  "$template" > "$target"

for token in __OIDC_CLIENT_SECRET__ __MCP_CLIENT_SECRET__ __ADMIN_PASSWORD__; do
  if grep -Fq "$token" "$target"; then
    fail "placeholder $token non sostituito in $target"
  fi
done

export KC_HOSTNAME="${KEYCLOAK_HOSTNAME:-https://localhost:8443}"
export KC_HOSTNAME_ADMIN="${KEYCLOAK_HOSTNAME_ADMIN:-http://localhost:18081}"
export KC_HOSTNAME_BACKCHANNEL_DYNAMIC=true
export KC_PROXY_HEADERS=xforwarded

exec /opt/keycloak/bin/kc.sh "$@"
