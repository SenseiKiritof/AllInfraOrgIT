COMPOSE ?= docker compose -f ../infraorgit-docker/compose.yaml

.PHONY: dev infra down config test migrate seed e2e release

dev: infra
	@echo "Infra avviata. API e frontend arrivano in Fase 2: vedi ../PLAN.md."

infra:
	$(COMPOSE) up -d --wait mysql mysql-keycloak keycloak

down:
	$(COMPOSE) down

config:
	$(COMPOSE) --env-file ../infraorgit-docker/.env.example config -q

test migrate seed e2e release:
	@echo "Target '$@' disponibile dalla Fase 2; nessun progetto applicativo ancora scaffoldato." >&2
	@exit 1
