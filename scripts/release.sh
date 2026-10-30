#!/usr/bin/env bash
# Release locale: gate, lock dei commit e tag. Nessun push.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META_ROOT="$(cd "$HERE/.." && pwd)"
ROOT="$(cd "$META_ROOT/.." && pwd)"
VERSION="${VERSION:-}"
TAG="v$VERSION"
REPOS=(InfraOrgITApi InfraOrgITWeb InfraOrgITDocker)

if [[ ! "$VERSION" =~ ^0\.[0-9]+\.[0-9]+$ ]]; then
  echo "VERSION mancante o non valida (atteso 0.MINOR.PATCH)." >&2
  exit 2
fi

for repo in "${REPOS[@]}" AllInfraOrgIT; do
  branch="$(git -C "$ROOT/$repo" branch --show-current)"
  if [ "$branch" != "main" ]; then
    echo "Branch $branch in $repo: la release parte solo da main." >&2
    exit 1
  fi
done

for repo in "${REPOS[@]}" AllInfraOrgIT; do
  if [ -n "$(git -C "$ROOT/$repo" status --porcelain)" ]; then
    echo "Working tree non pulito in $repo: commit o stash prima della release." >&2
    exit 1
  fi
done

for repo in "${REPOS[@]}" AllInfraOrgIT; do
  if git -C "$ROOT/$repo" rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
    echo "Tag $TAG già presente in $repo: verrà saltato." >&2
  fi
done

if [ "${SKIP_GATES:-}" != "1" ]; then
  make -C "$META_ROOT" ci
fi

if [ "${SKIP_E2E:-}" != "1" ]; then
  make -C "$META_ROOT" e2e
fi

python3 - "$ROOT" "$META_ROOT" "${REPOS[@]}" <<'PY'
import json
import subprocess
import sys
from datetime import datetime, timezone

root, meta, *repos = sys.argv[1:]
lock = {
    "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "repos": {
        repo: subprocess.check_output(
            ["git", "-C", f"{root}/{repo}", "rev-parse", "HEAD"], text=True
        ).strip()
        for repo in repos
    },
}
with open(f"{meta}/versions.lock", "w", encoding="utf-8") as handle:
    json.dump(lock, handle, indent=2)
    handle.write("\n")
PY

git -C "$META_ROOT" add versions.lock
git -C "$META_ROOT" commit -m ":bookmark: release $TAG"
for repo in "${REPOS[@]}"; do
  if ! git -C "$ROOT/$repo" rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
    git -C "$ROOT/$repo" tag -a "$TAG" -m "Release $TAG"
  fi
done
if ! git -C "$META_ROOT" rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  git -C "$META_ROOT" tag -a "$TAG" -m "Release $TAG"
fi

echo "Release locale $TAG creata."
echo "Push (da eseguire a mano, dopo verifica):"
for repo in "${REPOS[@]}" AllInfraOrgIT; do
  echo "  git -C $repo push origin main --follow-tags"
done
