COMPOSE ?= docker compose -f ../InfraOrgITDocker/compose.yaml
COMPOSE_FULL ?= $(COMPOSE) -f ../InfraOrgITDocker/compose.full.yaml

.PHONY: dev infra full down config reset api web migrate seed test e2e e2e-full ci openapi backup restore load-test legacy-up legacy-dry-run legacy-rehearsal release

dev:
	./scripts/dev.sh

openapi:
	../InfraOrgITApi/scripts/openapi.sh

backup:
	./scripts/backup.sh

load-test:
	REQUESTS=$${REQUESTS:-30} CONCURRENCY=$${CONCURRENCY:-5} ./scripts/loadtest.py

restore:
	./scripts/restore.sh $(BACKUP_DIR)

full:
	yarn --cwd ../InfraOrgITWeb build
	@bash -c 'source ./scripts/env.sh && \
		$(COMPOSE_FULL) --profile full up -d --build && \
		$(COMPOSE_FULL) --profile full restart caddy'

infra:
	$(COMPOSE) up -d --wait mysql mysql-keycloak keycloak

down:
	$(COMPOSE) --profile full --profile legacy down

reset:
	$(COMPOSE) --profile full --profile legacy down -v
	@echo "Volumi rimossi: al prossimo make dev Keycloak reimporta il realm."

config:
	@if [ -f ../InfraOrgITDocker/.env ]; then \
		$(COMPOSE) --env-file ../InfraOrgITDocker/.env config -q && \
		$(COMPOSE_FULL) --env-file ../InfraOrgITDocker/.env config -q; \
	else \
		$(COMPOSE) --env-file ../InfraOrgITDocker/.env.example config -q && \
		$(COMPOSE_FULL) --env-file ../InfraOrgITDocker/.env.example config -q; \
	fi

api:
	@bash -c 'source ./scripts/env.sh && dotnet run --project ../InfraOrgITApi/src/InfraOrgIt.Api --no-launch-profile'

web:
	yarn --cwd ../InfraOrgITWeb dev

migrate:
	@bash -c 'source ./scripts/env.sh && \
		dotnet tool restore >/dev/null && \
		dotnet tool run dotnet-ef database update \
			--project ../InfraOrgITApi/src/InfraOrgIt.Api \
			--startup-project ../InfraOrgITApi/src/InfraOrgIt.Api'

seed: migrate
	@echo "Seed ruoli/menu applicato dalle migration EF."

test:
	dotnet test ../InfraOrgITApi/InfraOrgIt.slnx
	yarn --cwd ../InfraOrgITWeb test

e2e:
	yarn --cwd ../InfraOrgITWeb playwright test

e2e-full:
	@$(COMPOSE_FULL) --profile full exec -T mysql sh -c 'mysql -u root -p"$$MYSQL_ROOT_PASSWORD" infraorgit -e "INSERT IGNORE INTO Users (Name,Surname,Username,CreatedAt,UpdatedAt,Version) VALUES (\"Dev\",\"Admin\",\"admin\",UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),0); INSERT IGNORE INTO RoleUser (RolesId,UsersId) SELECT 3,Id FROM Users WHERE Username=\"admin\";"'
	E2E_BASE_URL=https://localhost E2E_IGNORE_HTTPS=1 yarn --cwd ../InfraOrgITWeb playwright test

legacy-up:
	$(COMPOSE) --profile legacy up -d --wait mysql-legacy

legacy-rehearsal: legacy-up
	@bash -c 'source ./scripts/env.sh && \
		LEGACY_SOURCE_CONNECTION="Server=localhost;Port=3308;Database=infraorgit_legacy;User ID=legacy;Password=$${LEGACY_DB_PASSWORD:-dev-legacy-password};" \
		dotnet run --project ../InfraOrgITApi/tools/LegacyImport -- \
			--report /tmp/legacy-rehearsal.json && \
		echo "Report: /tmp/legacy-rehearsal.json"'

legacy-dry-run:
	dotnet run --project ../InfraOrgITApi/tools/LegacyImport -- \
		--input ../InfraOrgITApi/tools/LegacyImport/fixtures/rehearsal.json \
		--report /tmp/legacy-dry-run.json

ci: config
	dotnet build ../InfraOrgITApi/InfraOrgIt.slnx -warnaserror
	dotnet test ../InfraOrgITApi/InfraOrgIt.slnx
	yarn --cwd ../InfraOrgITWeb install --frozen-lockfile
	yarn --cwd ../InfraOrgITWeb biome ci .
	yarn --cwd ../InfraOrgITWeb tsc --noEmit
	yarn --cwd ../InfraOrgITWeb vitest run
	yarn --cwd ../InfraOrgITWeb build
	jq empty versions.lock
	../InfraOrgITApi/scripts/openapi.sh
	@test -z "$$(git -C ../InfraOrgITApi status --porcelain -- openapi/InfraOrgIt.Api.json)" || \
		{ echo "OpenAPI drift: rigenerare e committare openapi/InfraOrgIt.Api.json" >&2; exit 1; }
	npx --yes @redocly/cli lint docs/api/openapi.yaml

release:
	@test -n "$(VERSION)" || { echo "Uso: make release VERSION=0.8.0" >&2; exit 2; }
	VERSION=$(VERSION) ./scripts/release.sh
