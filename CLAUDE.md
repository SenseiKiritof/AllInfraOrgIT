# AllInfraOrgIT — agent guide

`AGENTS.md` is a symlink to this file, read by opencode and the other agents: edit `CLAUDE.md` only.

Meta repository of the InfraOrgIT workspace. Usage guide and layout in `README.md`; open work in `docs/backlog.md`.

## What lives here

- `docs/adr/`: every architectural decision, one entry per ADR, explicit status.
- `.opencode/`: project OpenCode documentation; personal configuration lives in `~/.config/opencode/`.
- `versions.lock`: application repo SHAs and images; update only on verified releases.
- `tools/graphify/workspace.json`: local configuration, never committed; the example is.
- `Makefile` and `scripts/`: orchestration and development environment.
- `.config/dotnet-tools.json`: local `dotnet-ef` version.

## Rules

- A new ADR never edits an accepted one: it supersedes it with `Status: superseded by ADR-NNN`.
- No secrets, production dumps or personal absolute paths in versioned files (`workspace.example.json` uses a placeholder).
- Documented commands must exist: no invented build/test before Phase 2.
