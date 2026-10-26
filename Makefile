COMPOSE ?= docker compose -f ../infraorgit-docker/compose.yaml

.PHONY: dev infra down config reset api web migrate seed test e2e ci legacy-dry-run release

dev:
	./scripts/dev.sh

infra:
	$(COMPOSE) up -d --wait mysql mysql-keycloak keycloak

down:
	$(COMPOSE) down

reset:
	$(COMPOSE) down -v
	@echo "Volumi rimossi: al prossimo make dev Keycloak reimporta il realm."

config:
	@if [ -f ../infraorgit-docker/.env ]; then \
		$(COMPOSE) --env-file ../infraorgit-docker/.env config -q; \
	else \
		$(COMPOSE) --env-file ../infraorgit-docker/.env.example config -q; \
	fi

api:
	@bash -c 'source ./scripts/env.sh && dotnet run --project ../infraorgit/src/InfraOrgIt.Api --no-launch-profile'

web:
	yarn --cwd ../infraorgit-web dev

migrate:
	@bash -c 'source ./scripts/env.sh && \
		dotnet tool restore >/dev/null && \
		dotnet tool run dotnet-ef database update \
			--project ../infraorgit/src/InfraOrgIt.Api \
			--startup-project ../infraorgit/src/InfraOrgIt.Api'

seed: migrate
	@echo "Seed ruoli/menu applicato dalle migration EF."

test:
	dotnet test ../infraorgit/InfraOrgIt.slnx
	yarn --cwd ../infraorgit-web test

e2e:
	yarn --cwd ../infraorgit-web playwright test

legacy-dry-run:
	dotnet run --project ../infraorgit/tools/LegacyImport -- \
		--input ../infraorgit/tools/LegacyImport/fixtures/rehearsal.json \
		--report /tmp/legacy-dry-run.json

ci: config
	dotnet build ../infraorgit/InfraOrgIt.slnx -warnaserror
	dotnet test ../infraorgit/InfraOrgIt.slnx
	yarn --cwd ../infraorgit-web install --frozen-lockfile
	yarn --cwd ../infraorgit-web biome ci .
	yarn --cwd ../infraorgit-web tsc --noEmit
	yarn --cwd ../infraorgit-web vitest run
	yarn --cwd ../infraorgit-web build
	jq empty versions.lock
	npx --yes @redocly/cli lint docs/api/openapi.yaml

release:
	@echo "Release e versions.lock: Fase 8." >&2
	@exit 1
