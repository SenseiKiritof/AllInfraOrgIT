COMPOSE ?= docker compose -f ../InfraOrgITDocker/compose.yaml
DOCKER_DIR ?= ../InfraOrgITDocker

.PHONY: dev infra full down config reset api web migrate seed test e2e e2e-full ci openapi backup restore load-test legacy-dry-run release

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
	$(COMPOSE) up -d --build --wait

infra:
	KC_MODE=dev $(COMPOSE) up -d --wait mysql mysql-keycloak keycloak

down:
	$(COMPOSE) down

reset:
	$(COMPOSE) down -v
	rm -rf $(DOCKER_DIR)/data
	@echo "Dati rimossi: al prossimo make dev mysql reinizializza infraorgit e Keycloak reimporta il realm."

config:
	@if [ -f ../InfraOrgITDocker/.env ]; then \
		$(COMPOSE) --env-file ../InfraOrgITDocker/.env config -q; \
	else \
		$(COMPOSE) --env-file ../InfraOrgITDocker/.env.example config -q; \
	fi

api:
	@bash -c 'source ./scripts/env.sh && dotnet run --project ../InfraOrgITApi/src/InfraOrgIt.Api --no-launch-profile'

web:
	yarn --cwd ../InfraOrgITWeb dev

migrate:
	@bash -c 'source ./scripts/env.sh && \
		dotnet tool restore >/dev/null && \
		dotnet restore ../InfraOrgITApi/InfraOrgIt.slnx >/dev/null && \
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
	@$(COMPOSE) exec -T mysql sh -c 'mysql -u root -p"$$MYSQL_ROOT_PASSWORD" infraorgit -e "INSERT IGNORE INTO Users (Name,Surname,Username,CreatedAt,UpdatedAt,Version) VALUES (\"Dev\",\"Admin\",\"admin\",UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),0); INSERT IGNORE INTO RoleUser (RolesId,UsersId) SELECT 3,Id FROM Users WHERE Username=\"admin\";"'
	E2E_BASE_URL=https://localhost:8443 E2E_IGNORE_HTTPS=1 yarn --cwd ../InfraOrgITWeb playwright test

legacy-dry-run:
	dotnet run --project ../InfraOrgITApi/tools/LegacyImport -- \
		--input ../InfraOrgITApi/tools/LegacyImport/fixtures/rehearsal.json \
		--report /tmp/legacy-dry-run.json

ci: config
	dotnet build ../InfraOrgITApi/InfraOrgIt.slnx -warnaserror
	dotnet test ../InfraOrgITApi/InfraOrgIt.slnx
	dotnet run --project ../InfraOrgITApi/tools/RewrapCredentials -- --self-check
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
