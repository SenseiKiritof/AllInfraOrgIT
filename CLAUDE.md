# AllInfraOrgIT — guida per agenti

`AGENTS.md` è un symlink a questo file, letto da opencode e dagli altri agenti: modifica solo `CLAUDE.md`.

Repo meta del workspace InfraOrgIT. Guida d'uso e struttura in `README.md`; lavori aperti in `docs/backlog.md`.

## Cosa vive qui

- `docs/adr/`: ogni decisione architetturale, una voce per ADR, stato esplicito.
- `versions.lock`: SHA dei repo applicativi; aggiornarlo solo a release verificate.
- `tools/graphify/workspace.json`: configurazione locale, mai committata; l'esempio sì.
- `Makefile` e `scripts/`: orchestrazione e ambiente di sviluppo.
- `.opencode/`: regole, skill e plugin OpenCode (vedi `.opencode/README.md`).
- `.config/dotnet-tools.json`: versione locale di `dotnet-ef`.

## Regole

- Un ADR nuovo non modifica uno accettato: lo sostituisce con `Stato: sostituita da ADR-NNN`.
- Niente segreti, dump reali, path assoluti personali nei file versionati (`workspace.example.json` usa un placeholder).
- I comandi documentati devono esistere: niente build/test inventati prima della Fase 2.
