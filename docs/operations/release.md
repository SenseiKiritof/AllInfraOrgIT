# Release

Procedura locale per taggare una versione `v0.MINOR.PATCH`. Nessun push automatico.

## Precondizioni

- Working tree pulito e branch `main` nei quattro repo (`infraorgit`, `-fe`, `-docker`, `AllInfraOrgIT`).
- Gate verdi: `make ci` (build `-warnaserror`, unit/integration, Biome, tsc, Vitest, build frontend, `jq versions.lock`, OpenAPI generato e senza drift).
- Stack attivo per `make e2e` (o `E2E_BASE_URL`); `SKIP_E2E=1` solo per prove locali.
- OpenAPI rigenerato e committato (`make openapi`, nessun diff).
- Backup pre-deploy eseguito (`make backup`) e restore provato.
- Fase 7: il rehearsal su dump legacy reale resta un blocco noto; la release sintetica non copre il cutover reale.

## Comando

```bash
cd AllInfraOrgIT
make release VERSION=0.8.0
```

`scripts/release.sh`:

1. rifiuta versioni non `0.x.y`, branch diverso da `main`, working tree sporco e tag già esistenti;
2. esegue `make ci` e `make e2e` (`SKIP_GATES=1`/`SKIP_E2E=1` solo per prova);
3. scrive `versions.lock` con `generatedAt` e gli SHA correnti dei tre repo applicativi;
4. commit `:bookmark: release v0.8.0` nel meta repo;
5. crea il tag annotato `v0.8.0` nei tre repo e nel meta repo;
6. stampa i comandi di push, da eseguire a mano.

## Push e deploy

I tag locali non sono una release pubblica. Dopo verifica:

```bash
git -C infraorgit push origin main --follow-tags
git -C infraorgit-web push origin main --follow-tags
git -C infraorgit-docker push origin main --follow-tags
git -C AllInfraOrgIT push origin main --follow-tags
```

Il deploy parte da `versions.lock`: checkout degli SHA, build immagini con `API_TAG=0.8.0`, `make full`, job `migrate`, smoke test (login, inventario, diagramma, health/ready).

## Rollback

- Ripristina il backup pre-deploy (`CONFIRM_RESTORE=yes make restore BACKUP_DIR=...`).
- Checkout di `versions.lock` del tag precedente e nuovo deploy.
- Keycloak: le sessioni SSO possono decadere; gli utenti restano.

## Stato 2026-10-27

`make release` implementato e guardie verificate (versione invalida → exit 2, working tree sporco → exit 1). Release non eseguita: i repo hanno modifiche non committate e la Fase 7 reale è ancora aperta.
