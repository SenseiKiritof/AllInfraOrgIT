# ADR-003 — Autenticazione Keycloak con BFF

- Stato: proposta
- Data: 2026-10-25

## Contesto

L'originale gestisce `state` e PKCE nel backend, salva i token in cookie HttpOnly e con `SameSite` obbliga tutto in HTTP in locale. Serve un flusso standard, testabile, con sessione server-side e nessun token leggibile da JavaScript.

## Decisione

- Keycloak 26, realm `infraorgit`, client confidenziale `infraorgit` con Authorization Code + PKCE S256.
- BFF nell'API: `GET /auth/login`, `GET /auth/callback`, `POST /auth/logout`, `GET /api/session`.
- `state` e `code_verifier` in un cookie HttpOnly breve; sessione server-side con cookie `HttpOnly`, `Secure`, `SameSite=Lax`, prefisso `__Host-` in produzione.
- Refresh lato server con rotazione; logout revoca la sessione Keycloak e cancella il cookie.
- Mutazioni con CSRF token e controllo `Origin`; nessun token in query string, localStorage o risposta API.
- Client secret solo nell'API.

## Alternative considerate

- **SPA con token in memoria**: scartata, token leggibili da JavaScript e refresh complesso.
- **Flusso custom dell'originale**: scartato, non standard e accoppiato a HTTP locale.

## Conseguenze

- L'API è stateful per le sessioni: serve uno store condiviso se si scala oltre una replica (decisione in Fase 2).
- Test E2E con Keycloak reale obbligatori.
- CSP più semplice: il browser non parla mai direttamente con Keycloak per le API.
