# graphify

Configurazione del workspace multi-repo.

- `workspace.example.json`: modello versionato; `root` è un placeholder.
- `workspace.json`: copia locale, ignorata da git. Impostare `root` sulla cartella che contiene `InfraOrgIT`.
- `graphify-out/` è ignorato.

Uso:

```bash
cp tools/graphify/workspace.example.json tools/graphify/workspace.json
# modificare "root"
```

La toolchain graphify si installa nell'ambiente (Fase 1); il repo versiona solo la configurazione.
