#!/usr/bin/env bash
# Syncs dashboard/dist/ (the dashboard submodule's build output) into
# dashboard-dist/ (an ordinary git-tracked directory at the repo root).
#
# dashboard/ stays a submodule for dev/source purposes only — its own repo,
# own CI, own history. dashboard-dist/ is what actually ships and gets
# served at runtime (see scripts/usage_dashboard.py), because a submodule
# gitlink alone isn't enough: a fresh `/plugin install`, a marketplace
# clone, or Claude Code's flat installed-plugin cache all have no way to
# run `git submodule update --init` for you. dashboard-dist/, being plain
# tracked files, is just present everywhere the parent repo is.
#
# Run this after building the dashboard submodule (`cd dashboard && npm
# run build`), whenever its dist/ output changes. It only syncs files —
# it does not `git add` or commit anything; that's left to whoever runs
# it (see .harness/workflow.md's dashboard-submodule-bump convention).
#
# Resolves paths from this script's own location, so it can be run from
# anywhere inside the repo.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/dashboard/dist"
DEST="$REPO_ROOT/dashboard-dist"

if [ ! -d "$SRC" ]; then
    echo "error: $SRC does not exist — build the dashboard submodule first:" >&2
    echo "  cd dashboard && npm install && npm run build" >&2
    exit 1
fi

mkdir -p "$DEST"

if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "$SRC/" "$DEST/"
else
    # rsync not available — fall back to cp, clearing stale content first
    # so removed build files don't linger.
    find "$DEST" -mindepth 1 -delete
    cp -r "$SRC/." "$DEST/"
fi

echo "synced $SRC -> $DEST"
