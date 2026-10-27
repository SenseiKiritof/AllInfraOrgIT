# Backlog

Opened on 2026-10-27. Each item is work not done yet: tick only after its verification passes.

## Frontend — `InfraOrgITWeb`

- [x] **Menu item icons**
  `@heroicons/react` + `path → icon` mapping in `src/lib/icons.ts` (fallback for unknown paths, detail routes mapped to their list). Tests in `src/lib/icons.test.ts`.

- [x] **User and theme icons in the header**
  Theme toggle with `SunIcon`/`MoonIcon`, user in a `details` element with `UserCircleIcon` and logout with `ArrowRightOnRectangleIcon`.

- [x] **Detail header: back + fullscreen**
  In `Shell`: “Back” button to the list when the path is `/<section>/<id>` and fullscreen toggle (`documentElement.requestFullscreen`, state synced on `fullscreenchange`).
  Still to evaluate: use the menu `HideBackButton` instead of path matching, if exceptions are needed later.

- [x] **Servers page UI bugs**
  Sidebar made scrollable (`min-h-0 overflow-y-auto`) and shell `overflow-hidden`; tables already inside `overflow-x-auto`. The residual overlay from the screenshot is not reproducible after refresh: if it comes back, note the route and menu state.

## Workspace

- [x] **Rename workspace and subrepositories**
  `AllInfraOrgIT`, `InfraOrgITApi`, `InfraOrgITWeb`, `InfraOrgITDocker` (no legacy prefix, no dots). Updated `Makefile`, `scripts/`, workflows, `versions.lock`, docs, README and GitHub remotes. Legacy copies were archived outside the workspace.
  Compose project `infraorgit`, images `infraorgit-api`/`infraorgit-web` (Docker names must be lowercase).

- [ ] **Validate the Docker images on the first tag**
  Implemented `InfraOrgITWeb/Dockerfile` + `Caddyfile`, image version labels for the API, `docker.yml` workflows in `InfraOrgITApi` and `InfraOrgITWeb` (GHCR, tags `X.Y.Z`, `X.Y`, `sha`, `latest`).
  Missing: first `v*` tag, workflow and push verification, image digests in `versions.lock`, published image usage in the release compose.
  Verification: `gh run list` green, `docker pull` both images, `APP_VERSION`/`VITE_APP_VERSION` visible at runtime.
