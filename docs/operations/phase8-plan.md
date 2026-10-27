# Piano operativo Fase 8 — hardening e release

Deriva dai Must di `release-audit.md` (verifica 2026-10-26). Ordine scelto per dipendenze: prima l'immagine e il deploy, poi auth/sessione, osservabilità e sicurezza applicativa, infine contratti, backup, load test e release.

## Decisioni proposte

| Tema | Scelta | Motivo |
|---|---|---|
| Session store | tabella MySQL via EF, stessa istanza applicativa | niente servizio nuovo; il deploy resta un host + Compose |
| Osservabilità | log JSON Serilog + OpenTelemetry OTLP opzionale da env | funziona in locale senza collector, in produzione si abilita con env |
| Deploy | singolo host, Caddy davanti a SPA e API, Keycloak same-host | D4 confermata |
| Immagini | tag espliciti; digest al primo registry disponibile | i repo sono ancora locali |

## Work package

| WP | Contenuto | Must | Uscita |
|---|---|---|---|
| 1 | `Dockerfile` API multi-stage non-root, servizio `api` nel profilo `full`, healthcheck, `read_only`, `cap_drop`, limiti | 1, 8 | `docker compose --profile full up` serve SPA + API |
| 2 | Keycloak `start` con hostname/proxy headers, Caddy inoltra `/realms` e `/resources`, redirect del client per l'host reale | 2 | login reale same-host |
| 3 | Session store MySQL condiviso, scadenza e limiti per utente | 3 | restart API senza logout; due istanze condividono la sessione |
| 4 | Serilog JSON, correlation id, OpenTelemetry traces/metriche, health liveness/readiness distinte | 4 | log strutturati e `/health/ready` con dipendenze |
| 5 | Security header in API e Caddy, forwarded headers con proxy fidati, rate limit per callback/run/reachability/console, Origin obbligatoria | 5, 6, 7 | test su header, 429 e Origin assente |
| 6 | Generazione OpenAPI dal backend e check di drift in CI; `schema.d.ts` generato | 11 | CI fallisce su contratto driftato |
| 7 | Job migrazioni separato dall'avvio API, backup/restore MySQL applicativo e Keycloak con prova di restore | 9, 10 | runbook + script provati in locale |
| 8 | Load test su liste, topologia e save con soglie | 12 | report latenza/throughput |
| 9 | `make release`, tag `v0.x`, `versions.lock`, E2E cleanup, checklist release | 13, 14 | release checklist verde |

## Stato

- WP1 completato: `Dockerfile` API multi-stage non-root, job `migrate`, servizio `api` read-only con `cap_drop`/`no-new-privileges`, healthcheck, Caddy che attende l'API. `make full` verificato.
- WP2 completato sul profilo `full`: Keycloak `start` con `KC_HOSTNAME`, proxy headers e backchannel dinamico; Caddy inoltra `/realms` e `/resources`; login reale provato su stack isolato (`/api/session` 200 con utente `admin`). Nota: il realm esistente va aggiornato o ricreato perché `--import-realm` non modifica i redirect URI già importati.
- WP3 completato: tabelle `Sessions` in MySQL con payload cifrato DataProtection, chiavi nel volume `api-dp-keys`, scadenza e limite di sessioni per utente. Test: sessione visibile da una seconda istanza API e limite applicato.
- WP4 completato: log JSON con correlation id, OpenTelemetry OTLP attivabile da env, `/health/ready` con MySQL e Keycloak. Verificato su container: readiness `{"status":"Healthy","checks":[{"name":"mysql"...},{"name":"keycloak"...}]}` e log JSON.
- WP5 completato: security header su API e Caddy, forwarded headers con reti fidate, rate limit per callback/run/reachability/console, Origin obbligatoria sulle mutazioni. Verificato via Caddy: HSTS 31536000 con forwarded proto, CSP distinta SPA/API.
- WP6 completato: OpenAPI 3.1.1 generato dal codice in `InfraOrgITApi/openapi/InfraOrgIt.Api.json` (148 operazioni), script `scripts/openapi.sh`, step CI che rigenera e fallisce su drift. `schema.d.ts` del frontend resta un Should non ancora automatizzato.
- WP7 completato: `make backup` (dump MySQL applicativo + Keycloak, manifest), `make restore` con conferma obbligatoria, runbook `operations/backup-restore.md`. Prova su stack isolato: dump validi, restore bloccato senza conferma, restore eseguito con tabella e realm verificati.
- WP8 completato: `scripts/loadtest.py` e `make load-test` su liste, topologia e create/delete; report in `operations/load-test.md`. Stack isolato, 12 richieste per endpoint, nessun errore, medie 9–26 ms.
- WP9 completato: `make release VERSION=0.x.y` con gate `make ci`, `versions.lock`, commit del lock e tag locali; runbook `operations/release.md`. Guardie verificate (versione invalida exit 2, working tree sporco exit 1). Immagini Compose e base image .NET pinnate per digest. `make ci` verde e 5 test Playwright passati su `make dev`; release non eseguita: repo con modifiche non committate e Fase 7 reale ancora aperta.
- Review fixes: rate limit dopo l'autenticazione con test per-utente, restore con conferma/stop servizi/dump validati, backup `600`, rete Docker `auth` dedicata, `make e2e-full` verificato su Caddy, OpenAPI con security per operazione, lock sessioni concorrenti e readiness senza discovery ripetuta.

## Fuori perimetro Fase 8

- Rehearsal su dump legacy reale e runbook di cutover: restano bloccati dai dati, tracciati in `migration/phase7-plan.md`.
- Push, protezione `main` e workflow su remoto: richiedono credenziali GitHub.
