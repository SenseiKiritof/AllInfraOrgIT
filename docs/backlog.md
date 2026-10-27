# Backlog

Aperto il 2026-10-27. Ogni voce è un lavoro non ancora fatto: spuntare solo a verifica completata.

## Frontend — `InfraOrgITWeb`

- [x] **Icone sulle voci di menu**
  `@heroicons/react` + mapping `path → icona` in `src/lib/icons.ts` (fallback per path sconosciuti, route di dettaglio mappate sulla lista). Test in `src/lib/icons.test.ts`.

- [x] **Icone utente e tema nell'header**
  Toggle tema con `SunIcon`/`MoonIcon`, utente in `details` con `UserCircleIcon` e logout con `ArrowRightOnRectangleIcon`.

- [x] **Header di dettaglio: indietro + fullscreen**
  In `Shell`: pulsante “Indietro” verso la lista quando il path è `/<sezione>/<id>` e toggle fullscreen (`documentElement.requestFullscreen`, stato sincronizzato su `fullscreenchange`).
  Resta da valutare: usare `HideBackButton` del menu al posto del match sul path, se in futuro servono eccezioni.

- [x] **Bug grafici pagina Servers**
  Sidebar resa scrollabile (`min-h-0 overflow-y-auto`) e shell con `overflow-hidden`; tabelle già dentro `overflow-x-auto`. L'overlay residuo dello screenshot non è riproducibile dopo il refresh: se ricompare, annotare route e stato del menu.

## Workspace

- [x] **Rinominare il workspace e i sottorepo**
  `AllInfraOrgIT`, `InfraOrgITApi`, `InfraOrgITWeb`, `InfraOrgITDocker` (niente prefisso `DS`, niente punti). Aggiornati `Makefile`, `scripts/`, workflow, `versions.lock`, docs, README e remote GitHub. Le copie legacy sono state rinominate `legacy copy` e `legacy Docker copy`.
  Compose project `infraorgit`, immagini `infraorgit-api`/`infraorgit-web`.

- [ ] **Validare le immagini Docker al primo tag**
  Implementati `InfraOrgITWeb/Dockerfile` + `Caddyfile`, label/versione nell'immagine API, workflow `docker.yml` in `InfraOrgITApi` e `InfraOrgITWeb` (GHCR, tag `X.Y.Z`, `X.Y`, `sha`, `latest`).
  Manca: primo tag `v*`, verifica workflow e push, digest delle immagini in `versions.lock`, uso dell'immagine pubblicata nel compose di release.
  Verifica: `gh run list` verde, `docker pull` delle due immagini, `APP_VERSION`/`VITE_APP_VERSION` visibili a runtime.
