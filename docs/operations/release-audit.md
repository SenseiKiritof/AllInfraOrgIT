# Audit release Fase 8

Verifica del 2026-10-26 su codice e configurazione, non solo sul piano. Stato: **non pronta**.

## Must — bloccano la release

| # | Problema | Evidenza | Azione |
|---|---|---|---|
| 1 | Nessun `Dockerfile` API; Caddy punta a `api:8080` inesistente | `compose.yaml`, `Caddyfile` | immagine API non-root + servizio nel profilo full |
| 2 | Keycloak `start-dev`, hostname/proxy non configurati, Caddy non inoltra `/realms`/`/resources`, redirect realm solo localhost | `compose.yaml`, `Caddyfile`, realm | modalità production, hostname, proxy headers, redirect reali |
| 3 | Session store in memoria: restart = logout, no multi-istanza, nessun limite | `InMemorySessionStore.cs` | store condiviso + limiti |
| 4 | Osservabilità assente: no Serilog/OTel, log non JSON | `Program.cs`, csproj | log strutturati, correlazione, metriche/tracce |
| 5 | Security header assenti (CSP/HSTS/nosniff/referrer/frame) | `Program.cs`, `Caddyfile` | header in API e Caddy |
| 6 | Forwarded headers assenti dietro Caddy: IP/schema errati | `Program.cs` | `UseForwardedHeaders` + trust proxy |
| 7 | Rate limit solo login e globale, nessun limite su callback/run/reachability/console | `Program.cs` | policy partizionate per IP/utente/azione |
| 8 | Immagini senza digest, senza `user`/`read_only`/`cap_drop`/limiti | `compose.yaml` | hardening e pinning |
| 9 | Migrazioni solo in Development, nessun job di deploy | `Program.cs` | job migration separato + runbook |
| 10 | Backup/restore assente | `docs/operations/` | script e prova di restore |
| 11 | OpenAPI non generato e driftabile; la CI non lo verifica | `docs/api/openapi.yaml`, workflow | generazione/verifica contratto |
| 12 | Nessun load test | test | latenza/throughput su liste/topologia/save |
| 13 | `make release` esce 1, niente tag | `Makefile` | release checklist, tag, lock |
| 14 | Fase 7 verificata solo su dump fittizio: mancano rehearsal su dump sanificato reale e runbook cutover/rollback | `docs/migration/phase7-plan.md` | dump sanificato, rehearsal e runbook firmato |

## Should

- Origin obbligatoria sulle mutazioni (oggi header assente passa).
- Console: idle timeout e limite sessioni per utente.
- Reachability: rate limit e allowlist destinazioni; non esporre `exception.Message` SSH al client.
- Log EF a `Warning` in produzione (oggi i parametri SQL finiscono nei log).
- `AllowedHosts` esplicito; `BootstrapAdminUsername` vietato fuori Development.
- Keycloak password policy e reset password.
- CI: action pinnate per SHA, Dependabot/audit, immagini e Redocly pinnati.
- E2E: cleanup del processo figlio, non solo del PID di `make`.
- Contratto TypeScript generato (`schema.d.ts`) invece dei tipi manuali.
- Audit delle mutazioni admin.
- `/health/ready` con dipendenza Keycloak o distinzione liveness/readiness.

## Nice

- Caddy access log con rotazione; `SECURITY.md`/`CODEOWNERS`/`LICENSE`.
- Coverage gate (coverlet già presente).
- Marcatore di troncamento nell'output audit.
- Aggiornare il commento “Fase 2” nel Caddyfile.

## Debito dichiarato — stato reale

- Session store: MySQL condiviso con payload cifrato DataProtection e limite per utente (Fase 8 WP3).
- Compose `full`: confermato incompleto (manca API, routing Keycloak).
- Import Fase 7: importer, adattatore MySQL e dump fittizio presenti; manca il rehearsal sui dati rappresentativi.

## Non verificato

Workflow su remoto e prova di restore (non eseguibili in questo ambiente). Il profilo full è stato avviato e il login verificato su volumi puliti; restano load test, backup/restore e la verifica su un host con dominio reale.

## Aggiornamento Fase 8 (2026-10-26)

- Must #1 risolto: immagine API multi-stage non-root, job `migrate`, servizio `api` read-only con `cap_drop` e healthcheck.
- Must #2 risolto sul profilo `full`: Keycloak `start`, hostname/proxy headers/backchannel dinamico, Caddy inoltra `/realms` e `/resources`; login reale verificato su stack pulito.
- Must #3 risolto: sessioni in MySQL cifrate con chiavi DataProtection persistenti; restart API senza logout e limite per utente testati.
- Must #4 risolto: log JSON con correlation id, OpenTelemetry OTLP opzionale, readiness con MySQL e Keycloak.
- Must #5, #6, #7 risolti: security header su API e Caddy, forwarded headers con reti fidate, rate limit partizionati per callback/run/reachability/console; Origin obbligatoria sulle mutazioni autenticate.
- Must #8 parziale: hardening e limiti presenti sull'API; restano da irrobustire le immagini MySQL/Keycloak e il pinning per digest.
- Must #11 risolto: OpenAPI generato dal codice e step CI che fallisce sul drift; `schema.d.ts` frontend resta Should.
- Must #9 risolto: job `migrate` separato e idempotente prima dell'API; avvio API senza migrazioni in Production.
- Must #10 risolto: `make backup` / `make restore` con conferma, runbook `operations/backup-restore.md` e prova di restore su stack isolato.
- Must #12 risolto: `scripts/loadtest.py` / `make load-test` su liste, topologia e create/delete; risultati in `operations/load-test.md`.
- Must #13 risolto come processo: `make release VERSION=0.x.y` esegue i gate, aggiorna `versions.lock` e crea i tag locali; push manuale. Guardie verificate, release non ancora eseguita.
- Must #14 resta aperto: rehearsal su dump legacy reale e runbook di cutover non eseguibili senza dati sanificati.
- Must #8 risolto per digest e hardening API: MySQL, Keycloak e Caddy pinnate per digest, base image .NET pinnate; API non-root/read-only/cap_drop. Le immagini upstream DB restano con entrypoint standard.
- E2E: `make e2e` non avvia processi figli, richiede `make dev` esterno; `make e2e-full` esegue gli stessi 5 test contro Caddy/HTTPS. Trace in `test-results/` ignorati.
