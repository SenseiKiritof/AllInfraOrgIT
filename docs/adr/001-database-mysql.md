# ADR-001 — Database MySQL LTS

- Status: accepted
- Date: 2026-10-25
- Decision: D1

## Context

The legacy runs on MySQL 9.5 (innovation) with the bootstrap schema in a SQL dump separate from the EF migrations. The full migration (D5) must preserve data and IDs. Changing the engine would add SQL conversion, query rewriting and risk on the diagrams, with no requested benefit.

## Decision

- MySQL 8.4 LTS (verified: `mysql:8.4` image started on 2026-10-25), not an innovation release.
- EF Core 10 with the `MySql.EntityFrameworkCore` 10.0.x provider (Oracle): the only MySQL provider that supports `net10.0`/EF Core 10. Pomelo stops at 9.0.0, bound to EF Core 9 (STS, support ended in May 2026).
- Code-first migrations as the only source of the schema; no schema in the init SQL.
- Integration tests with Testcontainers MySQL.
- Optimistic concurrency with an application token (`Version` int or `RowVersion` byte[]); MySQL has no `xmin`.
- Two separate MySQL instances in development (application and Keycloak), as in the Compose; separate users.

## Alternatives considered

- **PostgreSQL 17 + Npgsql**: rejected due to conversion and migration cost; remains the fallback if the MySQL provider blocks.
- **Pomelo + EF Core 9**: rejected, out-of-support stack.
- **Devart dotConnect for MySQL**: commercial fallback if the Oracle provider does not cover migrations, JSON or LINQ.

## Consequences

- Oracle provider license: GPL-2.0-only WITH Universal-FOSS-exception-1.0. Internal, non-distributed use: ok; legal review if the app is distributed.
- No `JSONB`: use MySQL's `JSON` type.
- Mandatory spike in Phase 1 on migrations, JSON, LINQ and Testcontainers.
- The importer reads legacy MySQL and writes the new MySQL, preserving the IDs.

## Phase 1 verification

The legacy schema matches the 26 EF entities plus 4 join tables; there are no domain tables outside the model. The full mapping is in `docs/migration/legacy-mapping.md`. The Oracle provider has not yet been tried on migrations/JSON/LINQ: the spike remains mandatory in Phase 2.
