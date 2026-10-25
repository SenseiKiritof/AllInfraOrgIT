# ADR-008 — Nomi dello schema e colonne di audit

- Stato: accettata
- Data: 2026-10-25

## Contesto

Lo schema legacy usa nomi PascalCase (`Environments`, `ProviderEnvironments`, `ApplicationApiQueryParams`) e non ha timestamp né concorrenza ottimistica. La migrazione deve preservare gli ID perché i diagrammi li referenziano. Un rinomina completa in snake_case aggiungerebbe mapping e rischio senza un beneficio richiesto.

## Decisione

- Mantenere tabella e colonne in PascalCase, come il legacy, salvo:
  - `EnvironmentEntity` → `EnvironmentDefinition`, tabella `EnvironmentDefinitions`, FK `EnvironmentDefinitionId`.
- Ogni tabella di dominio con PK propria riceve `CreatedAt`, `UpdatedAt` (UTC, `datetime(6)`) e `Version` (`int`, default 0, token di concorrenza). Eccezioni: `CommandExecutions` e join.
- `ServerCredentials` riceve `KeyVersion` e `NeedsReauth`.
- Enum numerici legacy convertiti in stringhe con check constraint; `ParameterValues` in colonna `JSON`.
- Vincoli unici candidati: `Users.Username`, `Roles.Name`, `ProviderEnvironments (ProviderId, EnvironmentDefinitionId)`, `ApplicationVersions (ApplicationId, VersionNumber)`, `ProxyRoutes (ProxyConnectionId, Route)`, `ProviderEnvironmentGroupRoles (ProviderEnvironmentId, GroupId, RoleId)`, `DiagramScopeItems/Nodes` per chiave logica. Vanno verificati sul export legacy prima dell'import.
- Hard delete; nessun soft delete in v1. Le delete distruttive hanno anteprima impatti e audit.
- `CommandExecutions` resta append-only con `ServerId` senza FK.

## Alternative considerate

- **snake_case**: più convenzionale in MySQL, ma richiede mapping totale e non risolve un problema reale.
- **Tenere `Environments` come tabella**: meno rinomine, ma lascia ambiguità con `ProviderEnvironment` e con l'entità `EnvironmentDefinition`.
- **RowVersion byte[]**: MySQL non ha un rowversion server-side; `Version` int è esplicito e testabile.

## Conseguenze

- L'importer mappa un numero limitato di nomi.
- Il data dictionary è la fonte per migration e test.
- I vincoli `UQ*` possono fallire su dati legacy duplicati: la decisione di pulizia va presa in Fase 7, non silenziosamente nell'importer.
