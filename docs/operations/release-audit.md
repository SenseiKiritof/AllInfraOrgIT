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
| 14 | Fase 7 non pronta: importer assente | `docs/migration/phase7-plan.md` | completare importer e rehearsal |

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

- Session store in memoria: confermato, unica implementazione.
- Compose `full`: confermato incompleto (manca API, routing Keycloak).
- Import Fase 7: assente; esistono fixture e dry-run nei test.

## Non verificato

Workflow su remoto e prova di restore (non eseguibili in questo ambiente). Il profilo full e l'SSO di produzione non sono mai stati avviati end-to-end: i primi due Must possono nascondere altri errori.
