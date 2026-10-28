# Backup and restore

Covers the two MySQL databases: application `infraorgit` and Keycloak `keycloak`. Dumps are logical (`mysqldump --single-transaction`), not point-in-time.

## Backup

```bash
cd AllInfraOrgIT
make backup                       # creates backups/<UTC>/ with the two dumps + manifest
BACKUP_DIR=/path/to/backup make backup
```

Contents: `infraorgit.sql.gz`, `keycloak.sql.gz`, `manifest.txt` (timestamp, project, images). Store off-host and encrypted: the dumps contain application data and encrypted SSH credentials.

Outside the backup, and mandatory to read SSH credentials after a restore:

- `ServerAccess:CredentialKeys` and `ServerAccess:CurrentKeyVersion` (secret manager);
- DataProtection keys (`api-dp-keys`): without them, active sessions expire at the first failed decrypt, but login remains possible;
- production `.env`/secret manager.

## Restore

Destructive operation: overwrites both databases.

1. Stop the services that write:

   ```bash
   docker compose -f ../InfraOrgITDocker/compose.yaml stop web api keycloak
   ```

2. Restore:

   ```bash
   cd AllInfraOrgIT
   CONFIRM_RESTORE=yes BACKUP_DIR=/path/to/backup make restore
   ```

   The script refuses to run if `web`, `api` or `keycloak` are still running, if the `.gz` files fail `gzip -t`, or if `CONFIRM_RESTORE=yes` is missing.

3. Restart with the migration job, which is idempotent:

   ```bash
   make full
   ```

4. Verify: `/health/ready` healthy, Keycloak login, an inventory list, a diagram, a credential without an unexpected `NeedsReauth`.

## Restore test

Performed on 2026-10-27 on an isolated Compose project (`COMPOSE_PROJECT_NAME=ds-backuptest`, dedicated volumes):

1. clean stack with MySQL, Keycloak MySQL and Keycloak;
2. `probe` table with one row, dump with `make backup` (exit 0, two valid `.sql.gz`, manifest, `600` permissions and `700` directory);
3. restore without `CONFIRM_RESTORE` blocked (exit 1);
4. restore with confirmation blocked because `keycloak` was still running (exit 1);
5. `DROP TABLE probe`, stop `keycloak`, restore with confirmation (exit 0);
6. `probe` back with 1 row; `keycloak.REALM` with 2 rows.

## Migrations in deploy

The `migrate` service runs `InfraOrgIt.Api migrate` and exits before the API. In production, migrations are not applied at API startup. Application rollback: restore of this backup plus checkout of the previous `versions.lock`.

## Limits

- Logical dump: the restore does not restore binlog or in-flight transactions; stop the writers first.
- Large databases: the dump takes space and time proportional to size; check free space on host and containers.
- Keycloak: after the restore, SSO sessions may be invalid; users remain.
