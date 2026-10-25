# ADR-001 — Database MySQL LTS

- Stato: accettata
- Data: 2026-10-25
- Decisione: D1

## Contesto

Il legacy gira su MySQL 9.5 (innovation) con lo schema di bootstrap in un dump SQL separato dalle migration EF. La migrazione completa (D5) deve preservare dati e ID. Un cambio di engine aggiungerebbe conversione SQL, riscrittura query e rischio sui diagrammi, senza un beneficio richiesto.

## Decisione

- MySQL 8.4 LTS (verificata: immagine `mysql:8.4` avviata il 2026-10-25), non una release innovation.
- EF Core 10 con provider `MySql.EntityFrameworkCore` 10.0.x (Oracle): unico provider MySQL che supporta `net10.0`/EF Core 10. Pomelo si ferma a 9.0.0, vincolato a EF Core 9 (STS, supporto terminato a maggio 2026).
- Migration code-first come unica fonte dello schema; niente schema negli init SQL.
- Test di integrazione con Testcontainers MySQL.
- Concorrenza ottimistica con token applicativo (`Version` int o `RowVersion` byte[]); MySQL non ha `xmin`.
- Due istanze MySQL separate in sviluppo (applicativa e Keycloak), come nel Compose; utenti separati.

## Alternative considerate

- **PostgreSQL 17 + Npgsql**: scartata per costo di conversione e migrazione; resta il fallback se il provider MySQL blocca.
- **Pomelo + EF Core 9**: scartata, stack fuori supporto.
- **Devart dotConnect for MySQL**: fallback commerciale se il provider Oracle non copre migration, JSON o LINQ.

## Conseguenze

- Licenza provider Oracle: GPL-2.0-only WITH Universal-FOSS-exception-1.0. Uso interno non distribuito: ok; legal review se l'app viene distribuita.
- Niente `JSONB`: usare il tipo `JSON` di MySQL.
- Spike obbligatorio in Fase 1 su migration, JSON, LINQ e Testcontainers.
- L'importer legge MySQL legacy e scrive MySQL nuovo, preservando gli ID.

## Verifica Fase 1

Lo schema legacy coincide con le 26 entità EF più 4 tabelle di join; non ci sono tabelle di dominio fuori dal modello. Il mapping completo è in `docs/migration/legacy-mapping.md`. Il provider Oracle non è ancora stato provato su migration/JSON/LINQ: lo spike resta obbligatorio in Fase 2.
