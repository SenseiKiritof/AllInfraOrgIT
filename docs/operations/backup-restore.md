# Backup e restore

Copre i due database MySQL: applicativo `infraorgit` e Keycloak `keycloak`. I dump sono logici (`mysqldump --single-transaction`), non point-in-time.

## Backup

```bash
cd AllInfraOrgIT
make backup                       # crea backups/<UTC>/ con i due dump + manifest
BACKUP_DIR=/percorso/backup make backup
```

Contenuto: `infraorgit.sql.gz`, `keycloak.sql.gz`, `manifest.txt` (timestamp, progetto, immagini). Conservare fuori host e cifrato: i dump contengono dati applicativi e credenziali SSH cifrate.

Fuori dal backup, e obbligatorie per leggere le credenziali SSH dopo un restore:

- `ServerAccess:CredentialKeys` e `ServerAccess:CurrentKeyVersion` (secret manager);
- chiavi DataProtection (`api-dp-keys`): senza, le sessioni attive decadono al primo decrypt fallito, ma il login resta possibile;
- `.env`/secret manager di produzione.

## Restore

Operazione distruttiva: sovrascrive entrambi i database.

1. Ferma i servizi che scrivono:

   ```bash
   docker compose -f ../infraorgit-docker/compose.yaml \
     -f ../infraorgit-docker/compose.full.yaml --profile full stop api caddy keycloak
   ```

2. Ripristina:

   ```bash
   cd AllInfraOrgIT
   CONFIRM_RESTORE=yes BACKUP_DIR=/percorso/backup make restore
   ```

   Lo script rifiuta l'esecuzione se `api`, `caddy` o `keycloak` sono ancora attivi, se i `.gz` non passano `gzip -t` o se manca `CONFIRM_RESTORE=yes`.

3. Riavvia con il job migrazioni, che è idempotente:

   ```bash
   make full
   ```

4. Verifica: `/health/ready` healthy, login Keycloak, una lista inventario, un diagramma, una credenziale senza `NeedsReauth` inatteso.

## Prova di restore

Eseguita il 2026-10-27 su progetto Compose isolato (`COMPOSE_PROJECT_NAME=ds-backuptest`, volumi dedicati):

1. stack pulito con MySQL, MySQL Keycloak e Keycloak;
2. tabella `probe` con una riga, dump con `make backup` (exit 0, due `.sql.gz` validi, manifest, permessi `600` e directory `700`);
3. restore senza `CONFIRM_RESTORE` bloccato (exit 1);
4. restore con conferma bloccato perché `keycloak` era ancora attivo (exit 1);
5. `DROP TABLE probe`, stop di `keycloak`, restore con conferma (exit 0);
6. `probe` tornata con 1 riga; `keycloak.REALM` con 2 righe.

## Migrazioni in deploy

Il servizio `migrate` esegue `InfraOrgIt.Api migrate` e termina prima dell'API. In produzione non si applicano migrazioni all'avvio dell'API. Rollback applicativo: ripristino di questo backup più checkout del `versions.lock` precedente.

## Limiti

- Dump logico: il restore non ripristina binlog né transazioni in corso; fermare i writer prima.
- Database grandi: il dump occupa spazio e tempo proporzionali; verificare spazio su host e container.
- Keycloak: dopo il restore le sessioni SSO possono essere invalide; gli utenti restano.
