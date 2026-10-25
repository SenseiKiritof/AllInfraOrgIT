# ADR-007 — Convenzioni del contratto API

- Stato: accettata
- Data: 2026-10-25
- Decisione: D10 (route) e convenzioni §5.8; D10 confermata il 2026-10-25

## Contesto

Il legacy espone route PascalCase sotto `/api` (`/api/Providers`, `/api/Applications/...`), con il typo `/api/Enviroments`. Le liste hanno due forme (`/X` e `/X/Paginated`) e risposte `{totalCount, results}`. Gli enum sono un misto di interi e stringhe. Il frontend è l'unico client, quindi il contratto può essere corretto senza compatibilità esterna.

## Decisione

- Base `/api`, risorse in minuscolo e kebab-case plurale: `/api/providers`, `/api/environments`, `/api/provider-environments`, `/api/application-versions`, `/api/application-version-apis`, `/api/command-executions`.
- Auth BFF separata: `GET /auth/login`, `GET /auth/callback`, `POST /auth/logout`, `GET /api/session`. Nessun endpoint token esposto alla SPA.
- JSON camelCase; date UTC ISO 8601; enum come stringhe.
- Liste: `page` (1-based), `pageSize` (max 200), `sort`, `q`; risposta `{items,total,page,pageSize}`. Niente `/Paginated` separato.
- Errori RFC 7807 con `code` stabile e `traceId`; 400/401/403/404/409/422.
- `ETag`/`If-Match` su diagrammi; `Idempotency-Key` sulle esecuzioni remote.
- OpenAPI 3.x generato dal backend e versionato; la CI fallisce se il client TypeScript è driftato.
- `Enviroments` non ha alias in v1; l'alias si aggiunge solo per un client esterno (D10).

## Alternative considerate

- **Mantenere PascalCase e `/Enviroments`**: zero modifiche al frontend legacy, ma tramanda un typo e un contratto incoerente.
- **Versionamento URL `/api/v1`**: non necessario finché l'unico client è la SPA; si aggiunge se nasce un client esterno.
- **Alias `/Enviroments`**: scartato in v1; costa poco aggiungerlo dopo, costa tempo mantenere due route da subito.

## Conseguenze

- Tutte le chiamate frontend cambiano; il mapping legacy → target è in `docs/api/route-inventory.md`.
- La lista unica sostituisce `/X/Paginated`; i select usano `pageSize` alto o un endpoint dedicato se servirà.
- Il contratto diventa un artefatto di release: OpenAPI e `schema.d.ts` sono obbligatori.
