# First push and `main` protection

Procedure to bring the four repos to GitHub. It has not been executed: this environment has no GitHub credentials (`gh` missing, no token). The repos are ready on the local `main` branch.

## 1. Create the repos

Private, same owner for all four:

```bash
gh repo create <owner>/AllInfraOrgIT --private
gh repo create <owner>/InfraOrgITApi --private
gh repo create <owner>/InfraOrgITWeb --private
gh repo create <owner>/InfraOrgITDocker --private
```

Alternatively create them empty from the UI, without README, license or `.gitignore`.

## 2. Add the remotes and push

From the workspace root:

```bash
for r in AllInfraOrgIT InfraOrgITApi InfraOrgITWeb InfraOrgITDocker; do
  git -C "$r" remote add origin "git@github.com:<owner>/$r.git"
  git -C "$r" push -u origin main
  git -C "$r" push --tags
done
```

The push must include only versioned files: no `.env`, no dumps, no `node_modules`.

## 3. Protect `main`

With `gh` authenticated, for each repo:

```bash
for r in AllInfraOrgIT InfraOrgITApi InfraOrgITWeb InfraOrgITDocker; do
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

The check names are the job names: `build-test` (backend), `lint-test-build` (frontend), `config` (docker), `check` (meta). Confirm them on the Actions page after the first push; for the meta repo also add `keycloak-login` if the E2E workflow is enabled.

## 4. Secret for the E2E workflow

The nightly workflow clones the three application repos. With private repos `github.token` is not enough: create a fine-grained PAT with `Contents: read` on the three repos and store it as `REPO_TOKEN` in the meta repo (`Settings → Secrets and variables → Actions`). The workflow uses `secrets.REPO_TOKEN || github.token`.

## 5. Verification

1. First push to `main`: the `meta`, `backend-ci`, `frontend-ci`, `docker` workflows must start and pass.
2. `workflow_dispatch` of `e2e`: Keycloak, stack, Playwright.
3. `make ci` locally must give the same result as the workflows (excluding E2E, which requires `make dev`).
4. Update `versions.lock` only after a verified push.

## Running the workflows locally

The four application workflows were run locally with [`act`](https://github.com/nektos/act) on 2026-10-26:

```bash
act -P ubuntu-latest=catthehacker/ubuntu:act-latest -j <job> --pull=false
```

- `meta` / `check`
- `backend-ci` / `build-test` (12 integration tests on Testcontainers)
- `frontend-ci` / `lint-test-build`
- `docker` / `config`

The `e2e` workflow cannot run with `act` until the repos have a remote: it clones the three sibling repos from GitHub. Its steps (`make dev`, `make e2e`) are covered by the local test.
