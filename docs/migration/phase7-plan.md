# Piano operativo Fase 7 — migrazione legacy

Analisi del 2026-10-26 sul nuovo schema e sullo schema legacy (`../InfraOrgITDocker/legacy/01-schema.sql`, sole definizioni). Nessun dato reale letto o copiato.

## Blocchi da chiudere prima dell'importer

1. **`tools/LegacyImport`** non esiste: console .NET 10 indipendente da API/migration, con `--dry-run`, `--classes`, `--batch-size`, `--report`, `--fresh` esplicito.
2. **Fixture sanificate** per tutte le classi: oggi solo riferimento+catalogo (`Legacy/Fixtures/legacy-reference-catalog.json`); mancano inventario, credenziali, proxy, diagrammi, audit.
3. **Preflight duplicati**: il nuovo schema ha unique che il legacy non aveva (username, nomi provider/ambiente/applicazione/progetto, versione per applicazione, route per connessione, nodi/edge per chiave, PEGR, `ServerApplications.ProxyRouteId`). Decisione per ogni collisione: merge, rename o reject bloccante.
4. **Orfani e default legacy**: `ProviderEnvironmentId=0`, `ProxyRoutes.ProxyConnectionId=0`, FK orfane, `ReachabilityTests.Port` fuori range, proxy con source=target. Preflight bloccante.
5. **Ciclo `ServerApplications.ProxyRouteId` ↔ `ProxyRoutes.TargetServerApplicationId`**: import a due fasi (deploy senza link → route → update link), senza disattivare FK se possibile.
6. **`sub` Keycloak**: il nuovo `User` non ha `ExternalId`; import per username e report dei non matchati. Aggiungere la colonna in Fase 7 se serve stabilità.
7. **Credenziali**: decifratura legacy separata dalla chiave nuova; se la vecchia `ServerAccess:CredentialKey` manca o il record è invalido → `NeedsReauth=true`, `EncryptedSecret=''`. Conteggio `migrati + needs_reauth = totale`.
8. **Audit**: policy di redazione. Default prudente: importare metadati, `Script=''`, `Output=''`, contare i record redatti. Mai plaintext/ciphertext nei report.
9. **Timestamp**: il `SaveChanges` del DbContext sovrascrive `UpdatedAt`; per preservare i timestamp usare SQL raw controllato. `Version=0` salvo diverso.
10. **Diagrammi**: verificare ogni scope/node/edge su entità esistenti; al massimo un `IsDefault`; l'id 0 legacy è la vista virtuale, non una riga.

## Ordine di import

1. Riferimento: `EnvironmentDefinitions`, `Providers`, `ProviderEnvironments`; upsert di `Roles`, `Menus` sui seed esistenti; `MenuRole` in merge.
2. Identità: `Users`, `Groups`, `GroupUser`, `RoleUser`, `MenuRole`, `ProviderEnvironmentGroupRoles`.
3. Catalogo: `Projects`, `Applications`, `ApplicationVersions`, `ApplicationVersionApis`, `ApplicationApiQueryParams`, `ApplicationProject`, `CommandTemplates`, `ApplicationActions`.
4. Inventario: `ServerCredentials`, `Servers`, `ProxyConnections`, `ServerApplications` (link nullo), `ProxyRoutes`, update link, `ReachabilityTests`.
5. Diagrammi: `Diagrams`, `DiagramScopeItems`, `DiagramNodes`, `DiagramEdges`.
6. Audit: `CommandExecutions` (ultimo, nessuna FK su server).

Join dopo i padri; self-FK (`Menus.ParentId`, `ProxyRoutes.TargetProxyConnectionId`) con padri prima. `SET FOREIGN_KEY_CHECKS=0` solo come ultima risorsa, sessione locale, poi verifica orfani. Non usare `SET UNIQUE_CHECKS=0`.

## Requisiti importer

- Input: connection string legacy **read-only**, target, vecchia chiave da env/secret, path report.
- Dry-run: legge, valida, calcola il piano; nessuna scrittura; stesso report/exit code del run.
- Report: per classe letti/inseriti/aggiornati/saltati/rifiutati; PK e motivo; conteggi credenziali; checksum; nessun segreto.
- Idempotenza: insert se assente, skip o `--force`; join `INSERT IGNORE`; `--fresh` solo con conferma esplicita.
- Transazione per classe; inventario e ciclo route/deploy nella stessa transazione; checkpoint per riprendere.
- ID preservati sempre; nessun remap di `Diagram*.EntityId`.
- Verifica finale `AUTO_INCREMENT > MAX(Id)` su ogni tabella.

## Validazione bloccante

- Conteggi: `letti - rifiutati = target`.
- FK orfane: zero, escluso `CommandExecutions.ServerId` (senza FK per progetto).
- Unique: zero duplicati su ogni nuovo vincolo o decisione esplicita.
- Check: enum, `AuthType`, `Kind`, porta, source≠target, date non zero.
- Checksum ordinato per ID su campi chiave (nome, IP, hostname, coordinate, handle, bend, route).
- Credenziali: roundtrip in memoria, `KeyVersion` nuova, `needs_reauth` coerente.
- Diagrammi: target esistenti, `IsDefault` unico, render di ogni diagramma.
- Audit: conteggio, script/output vuoti o redatti, nessun pattern di segreto.
- Utenti: match con Keycloak e lista mancanti.
- Smoke: login, inventario, diagramma legacy, console su server di test.

## Cutover

Il legacy non ha `UpdatedAt` sulla maggior parte delle tabelle: un “delta import” affidabile non è possibile. Durante il freeze serve re-import completo idempotente o CDC/binlog. Rollback = checkout del `versions.lock` precedente e ripristino del DB pre-cutover.

## Rischi

- Dump reali vietati nei repo: snapshot read-only e fixture sanificate.
- Perdita della vecchia chiave credenziali.
- Host key legacy considerata fidata: valutare reset per server critici.
- `longtext` grandi: batch piccoli e `max_allowed_packet`.
- Duplicati/check possono fermare l'import a metà classe: preflight bloccante.
- Keycloak senza utenti allineati: login rotto dopo il cutover.
