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
  esac
  for token in __OIDC_CLIENT_SECRET__ __MCP_CLIENT_SECRET__ __ADMIN_PASSWORD__ \
    __MFA_BROWSER_FLOW__ __MFA_REQUIRED_ACTIONS__ __MFA_ADMIN_REQUIRED_ACTIONS__; do
    case "$value" in
      *"$token"*) fail "$name contiene un token del template" ;;
    esac
  done
}

check_value OIDC_CLIENT_SECRET "$OIDC_CLIENT_SECRET"
check_value MCP_CLIENT_SECRET "$MCP_CLIENT_SECRET"
check_value INFRAORGIT_ADMIN_PASSWORD "$INFRAORGIT_ADMIN_PASSWORD"

[ -f "$template" ] || fail "template non trovato: $template"
command -v sed >/dev/null 2>&1 || fail "sed non disponibile"
command -v tr >/dev/null 2>&1 || fail "tr non disponibile"

# MFA is an explicit deployment choice (PT-08). The realm always defines the
# browser-mfa flow; this switch only binds it and forces TOTP enrollment.
# Accept the same spellings as deploy/scripts/check-env.sh.
mfa_value="${KEYCLOAK_MFA:-false}"
case "$(printf '%s' "$mfa_value" | tr '[:upper:]' '[:lower:]')" in
  true|1|yes) mfa_enabled=true ;;
  false|0|no) mfa_enabled=false ;;
  *) fail "KEYCLOAK_MFA non valido: '$mfa_value' (true/false/1/0/yes/no)" ;;
esac

# UPDATE_PASSWORD is always registered for the realm: an empty requiredActions
# list makes Keycloak ignore the bootstrap admin's forced password change.
update_password_action='{"alias": "UPDATE_PASSWORD", "name": "Update Password", "providerId": "UPDATE_PASSWORD", "enabled": true, "defaultAction": false, "priority": 30}'
totp_action='{"alias": "CONFIGURE_TOTP", "name": "Configure OTP", "providerId": "CONFIGURE_TOTP", "enabled": true, "defaultAction": true, "priority": 10}'

if [ "$mfa_enabled" = true ]; then
  browser_flow=browser-mfa
  required_actions="$update_password_action, $totp_action"
  admin_required_actions='"UPDATE_PASSWORD", "CONFIGURE_TOTP"'
else
  browser_flow=browser
  required_actions="$update_password_action"
  admin_required_actions='"UPDATE_PASSWORD"'
fi

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
REQUIRED_ACTIONS_SED="$(sed_replacement "$required_actions")"
ADMIN_REQUIRED_ACTIONS_SED="$(sed_replacement "$admin_required_actions")"

sed -e "s|__OIDC_CLIENT_SECRET__|$OIDC_CLIENT_SED|g" \
  -e "s|__MCP_CLIENT_SECRET__|$MCP_CLIENT_SED|g" \
  -e "s|__ADMIN_PASSWORD__|$ADMIN_PASSWORD_SED|g" \
  -e "s|\"__MFA_REQUIRED_ACTIONS__\"|$REQUIRED_ACTIONS_SED|g" \
  -e "s|\"__MFA_ADMIN_REQUIRED_ACTIONS__\"|$ADMIN_REQUIRED_ACTIONS_SED|g" \
  -e "s|__MFA_BROWSER_FLOW__|$browser_flow|g" \
  "$template" > "$target"

for token in __OIDC_CLIENT_SECRET__ __MCP_CLIENT_SECRET__ __ADMIN_PASSWORD__ \
  __MFA_BROWSER_FLOW__ __MFA_REQUIRED_ACTIONS__ __MFA_ADMIN_REQUIRED_ACTIONS__; do
  if grep -Fq "$token" "$target"; then
    fail "placeholder $token non sostituito in $target"
  fi
done

# Refuse a partially applied switch: the bound flow and the forced actions
# must agree with KEYCLOAK_MFA. This runs before Keycloak imports the realm.
if [ "$mfa_enabled" = true ]; then
  grep -Fq '"browserFlow": "browser-mfa"' "$target" ||
    fail "browserFlow non impostato su browser-mfa con KEYCLOAK_MFA=true"
  grep -Fq '"CONFIGURE_TOTP"' "$target" ||
    fail "CONFIGURE_TOTP non presente con KEYCLOAK_MFA=true"
else
  grep -Fq '"browserFlow": "browser"' "$target" ||
    fail "browserFlow non impostato su browser con KEYCLOAK_MFA=false"
  if grep -Fq 'CONFIGURE_TOTP' "$target"; then
    fail "CONFIGURE_TOTP ancora forzato con KEYCLOAK_MFA=false"
  fi
fi

# Validate the rendered realm as strict JSON. Keycloak ships a JRE with
# jdk.compiler and Jackson, so source-file mode needs no extra binary; if the
# image drops either, startup fails closed rather than importing a broken realm.
validate_json() {
  checker="$import_dir/RealmJsonCheck.java"
  cat > "$checker" <<'JAVA'
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.File;

public final class RealmJsonCheck {
  public static void main(String[] args) throws Exception {
    ObjectMapper mapper = new ObjectMapper();
    mapper.enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    mapper.readTree(new File(args[0]));
  }
}
JAVA
  command -v java >/dev/null 2>&1 || fail "java non disponibile per validare il realm"
  java -cp '/opt/keycloak/lib/lib/main/*' "$checker" "$target" >/dev/null ||
    fail "realm renderizzato non e JSON valido: $target"
}

validate_json

export KC_HOSTNAME="${KEYCLOAK_HOSTNAME:-https://localhost:8443}"
export KC_HOSTNAME_ADMIN="${KEYCLOAK_HOSTNAME_ADMIN:-http://localhost:18081}"
export KC_HOSTNAME_BACKCHANNEL_DYNAMIC=true
export KC_PROXY_HEADERS=xforwarded

exec /opt/keycloak/bin/kc.sh "$@"
