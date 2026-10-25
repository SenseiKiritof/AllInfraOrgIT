# Primo push e protezione `main`

Procedura per portare i quattro repo su GitHub. Non è stata eseguita: in questo ambiente non ci sono credenziali GitHub (`gh` assente, nessun token). I repo sono pronti sul branch `main` locale.

## 1. Creare i repo

Private, stesso owner per tutti e quattro:

```bash
gh repo create <owner>/AllInfraOrgIT --private
gh repo create <owner>/infraorgit --private
gh repo create <owner>/infraorgit-web --private
gh repo create <owner>/infraorgit-docker --private
```

In alternativa crearli vuoti dalla UI, senza README, licenza o `.gitignore`.

## 2. Aggiungere i remote e pushare

Dalla root del workspace:

```bash
for r in AllInfraOrgIT infraorgit infraorgit-web infraorgit-docker; do
  git -C "$r" remote add origin "git@github.com:<owner>/$r.git"
  git -C "$r" push -u origin main
  git -C "$r" push --tags
done
```

Il push deve includere solo file versionati: nessun `.env`, nessun dump, nessun `node_modules`.

## 3. Proteggere `main`

Con `gh` autenticato, per ogni repo:

```bash
for r in AllInfraOrgIT infraorgit infraorgit-web infraorgit-docker; do
  gh api -X PUT "repos/<owner>/$r/branches/main/protection" \
    -f required_status_checks.strict=true \
    -f required_status_checks.contexts[]='build-test' \
    -f enforce_admins=true \
    -f required_pull_request_reviews.required_approving_review_count=1 \
    -f restrictions=null \
    -f allow_force_pushes=false \
    -f allow_deletions=false
done
```

I nomi dei check sono quelli dei job: `build-test` (backend), `lint-test-build` (frontend), `config` (docker), `check` (meta). Confermarli nella pagina Actions dopo il primo push; per il repo meta aggiungere anche `keycloak-login` se il workflow E2E è abilitato.

## 4. Segreto per il workflow E2E

Il workflow notturno clona i tre repo applicativi. Con repo privati `github.token` non basta: creare un fine-grained PAT con `Contents: read` sui tre repo e salvarlo come `REPO_TOKEN` nel repo meta (`Settings → Secrets and variables → Actions`). Il workflow usa `secrets.REPO_TOKEN || github.token`.

## 5. Verifica

1. Primo push su `main`: i workflow `meta`, `backend-ci`, `frontend-ci`, `docker` devono partire e passare.
2. `workflow_dispatch` di `e2e`: Keycloak, stack, Playwright.
3. `make ci` in locale deve dare lo stesso esito dei workflow (escluso E2E, che richiede `make dev`).
4. Aggiornare `versions.lock` solo dopo un push verificato.

## Esecuzione locale dei workflow

I quattro workflow applicativi sono stati eseguiti localmente con [`act`](https://github.com/nektos/act) il 2026-10-26:

```bash
act -P ubuntu-latest=catthehacker/ubuntu:act-latest -j <job> --pull=false
```

- `meta` / `check`
- `backend-ci` / `build-test` (12 test di integrazione su Testcontainers)
- `frontend-ci` / `lint-test-build`
- `docker` / `config`

Il workflow `e2e` non è eseguibile con `act` finché i repo non hanno un remote: clona i tre repo fratelli da GitHub. I suoi passi (`make dev`, `make e2e`) sono coperti dal test locale.
