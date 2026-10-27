# ADR-006 — Full legacy data migration

- Status: accepted
- Date: 2026-10-25
- Decision: D5

## Context

v1 must replace the original without losing inventory, catalog, diagrams, users and history. Entity IDs are referenced by the diagrams; SSH credentials are encrypted with a versioned key. Legacy data is exported outside the repository and is never committed.

## Decision

- Read-only snapshot of the legacy MySQL and a sanitized dump for tests; no production data in the repos.
- Standalone importer in `InfraOrgITApi/tools/LegacyImport`: reads legacy MySQL, writes the new MySQL, preserves IDs, produces a report.
- Order: reference → identity → catalog → inventory → diagrams → audit; transaction per class, repeatable and idempotent.
- Validation: per-table counts, orphan FKs, uniques, diagram rendering, checksums of key fields; blocking errors in the report.
- Credentials: decrypt with the old `ServerAccess:CredentialKey`, re-encrypt with the new one; if the key is missing, mark `needs_reauth`. Never log the plaintext.
- Users: Keycloak import or recreation with required actions; mapping by username until the `sub` is available, then preference for the `sub`.
- Cutover: write freeze, delta import, smoke tests, DNS switch, old system read-only; rollback to the previous lock if the smoke tests fail.

## Alternatives considered

- **Demo seed only**: rejected by D5; no Phase 7 and no importer.
- **Raw dump/restore**: rejected, schema and name drift, no re-encryption of credentials.

## Consequences

- The old `CredentialKey` is needed only during the import: never print it, never store it in the new repos.
- A reliable export of topology data is needed, including the data outside git.
- Rehearsal and validation report mandatory before cutover (Phase 7).

## Phase 1 verification

The legacy schema has 26 domain tables plus 4 join tables; the full mapping, the enums, the new fields and the import order are in `docs/migration/legacy-mapping.md`. Still open: an approved export of the legacy dataset, the Keycloak user mapping and the redaction of the legacy audit.
