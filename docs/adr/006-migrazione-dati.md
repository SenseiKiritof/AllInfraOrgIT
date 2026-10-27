# ADR-006 — Migrazione completa dei dati legacy

- Stato: accettata
- Data: 2026-10-25
- Decisione: D5

## Contesto

La v1 deve sostituire l'originale senza perdere inventario, catalogo, diagrammi, utenti e storico. Gli ID delle entità sono referenziati dai diagrammi; le credenziali SSH sono cifrate con una chiave versionata. Il dump `the legacy export` è ignorato da git e può contenere dati rappresentativi.

## Decisione

- Snapshot read-only del MySQL legacy e dump sanificato per i test; nessun dato reale nei repo.
- Importer standalone in `InfraOrgITApi/tools/LegacyImport`: legge MySQL legacy, scrive MySQL nuovo, preserva gli ID, produce un report.
- Ordine: riferimento → identità → catalogo → inventario → diagrammi → audit; transazione per classe, ripetibile e idempotente.
- Validazione: conteggi per tabella, FK orfane, unique, render dei diagrammi, checksum dei campi chiave; errori bloccanti nel report.
- Credenziali: decifrare con la vecchia `ServerAccess:CredentialKey`, ricifrare con la nuova; se la chiave manca, marcare `needs_reauth`. Mai loggare il plaintext.
- Utenti: import Keycloak o ricreazione con azioni richieste; mapping per username finché il `sub` non è disponibile, poi preferenza al `sub`.
- Cutover: freeze delle scritture, import delta, smoke test, switch DNS, vecchio sistema in sola lettura; rollback al lock precedente se gli smoke falliscono.

## Alternative considerate

- **Solo seed demo**: scartata da D5; niente Fase 7 e niente importer.
- **Dump/restore raw**: scartato, drift di schema e nomi, nessuna ricifratura delle credenziali.

## Conseguenze

- La vecchia `CredentialKey` serve solo durante l'import: mai stamparla, mai salvarla nei nuovi repo.
- Serve un export affidabile dei dati di topologia, inclusi quelli fuori git.
- Rehearsal e report di validazione obbligatori prima del cutover (Fase 7).

## Verifica Fase 1

Lo schema legacy ha 26 tabelle di dominio più 4 join; il mapping completo, gli enum, i campi nuovi e l'ordine di import sono in `docs/migration/legacy-mapping.md`. Restano aperti l'export approvato di `the legacy export`, la mappatura utenti Keycloak e la redazione dell'audit legacy.
