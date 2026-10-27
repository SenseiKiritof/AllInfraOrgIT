# graphify

Multi-repo workspace configuration.

- `workspace.example.json`: versioned model; `root` is a placeholder.
- `workspace.json`: local copy, git-ignored. Set `root` to the folder that contains `InfraOrgIT`.
- `graphify-out/` is ignored.

Usage:

```bash
cp tools/graphify/workspace.example.json tools/graphify/workspace.json
# edit "root"
```

The graphify toolchain is installed in the environment (Phase 1); the repository versions the configuration only.
