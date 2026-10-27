# ADR-002 — Frontend Vite + React + TypeScript

- Status: accepted
- Date: 2026-10-25
- Decision: D2

## Context

InfraOrgIT is an authenticated dashboard for a private infrastructure: SSR and SEO are not needed. The original uses Next.js 16, JavaScript without typecheck and a single test; `next lint` has been removed. The frontend must be simple to build, serve as static files and share the API contract.

## Decision

- Vite + React 19 + TypeScript.
- React Router 7 for routing, TanStack Query/Table for data and tables, React Hook Form + Zod for forms.
- React Flow 12 (`@xyflow/react`) confined to `features/diagrams`.
- Tailwind 4 + Radix + Heroicons.
- Biome 2 + `tsc --noEmit` as gates; Vitest + Testing Library + MSW for units/components, Playwright for E2E.
- `api/schema.d.ts` generated from the backend OpenAPI; no manual edits.

## Alternatives considered

- **Stable Next.js + TypeScript**: rejected because SSR/SEO are not needed and it adds a Node runtime to the deployment.
- **Create React App**: rejected, unmaintained.

## Consequences

- Static build in `dist/`, served by Caddy in production.
- In development Vite on :3000 with `/api` and `/auth` proxied to the API on :5298.
- Simpler CSP and deployment; no token readable from JavaScript.
- The OpenAPI contract becomes mandatory: CI fails if the TypeScript client drifts.
