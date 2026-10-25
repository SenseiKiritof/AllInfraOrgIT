# ADR-004 — Deploy single host con Docker Compose e Caddy

- Stato: accettata
- Data: 2026-10-25
- Decisione: D4

## Contesto

Applicazione interna su singolo host Linux. Servono HTTPS e un solo origin per SPA e API: cookie di sessione first-party e niente CORS. Un reverse proxy aziendale esiste solo se l'host è dietro di esso.

## Decisione

- Docker Compose su singolo host; niente Kubernetes in v1.
- Caddy al bordo: serve `dist/` della SPA, fa reverse proxy di `/api/*` e `/auth/*` verso l'API e gestisce TLS automatico (ACME o CA interna per la LAN).
- Stesso origin per SPA e API. In sviluppo niente Caddy: Vite :3000 con proxy verso l'API :5298.
- Keycloak sullo stesso host tramite Caddy (sottodominio o path prefix) in Fase 8, insieme alla configurazione di produzione.
- `versions.lock` per release e rollback.

## Alternative considerate

- **API serve la SPA** (`UseStaticFiles` + Kestrel): meno container, ma certificato e frontend accoppiati al deploy dell'API.
- **nginx/Traefik**: più configurazione per il TLS automatico.
- **Reverse proxy esistente**: Caddy rimosso; cambia solo il bordo.
- **Kubernetes/cloud**: fuori perimetro v1.

## Conseguenze

- Un container in più e un dominio/DNS per i certificati.
- Caddyfile e Compose validati in CI.
- In produzione Keycloak passa da `start-dev` a `start`, con hostname e proxy headers.
