# ADR-002 — Frontend Vite + React + TypeScript

- Stato: accettata
- Data: 2026-10-25
- Decisione: D2

## Contesto

InfraOrgIT è una dashboard interna autenticata: SSR e SEO non servono. L'originale usa Next.js 16, JavaScript senza typecheck e un solo test; `next lint` è stato rimosso. Il frontend deve essere semplice da costruire, servire come statico e condividere il contratto dell'API.

## Decisione

- Vite + React 19 + TypeScript.
- React Router 7 per il routing, TanStack Query/Table per dati e tabelle, React Hook Form + Zod per i form.
- React Flow 12 (`@xyflow/react`) confinato in `features/diagrams`.
- Tailwind 4 + Radix + Heroicons.
- Biome 2 + `tsc --noEmit` come gate; Vitest + Testing Library + MSW per unit/componenti, Playwright per E2E.
- `api/schema.d.ts` generato dall'OpenAPI del backend; nessuna modifica manuale.

## Alternative considerate

- **Next.js stabile + TypeScript**: scartata perché SSR/SEO non servono e aggiunge un runtime Node al deploy.
- **Create React App**: scartata, non mantenuta.

## Conseguenze

- Build statica in `dist/`, servita da Caddy in produzione.
- In sviluppo Vite su :3000 con proxy `/api` e `/auth` verso l'API su :5298.
- CSP e deploy più semplici; nessun token leggibile da JavaScript.
- Il contratto OpenAPI diventa obbligatorio: la CI fallisce se il client TypeScript è driftato.
