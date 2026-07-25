#!/usr/bin/env bash
# What an average agent gets on realistic reconnaissance tool-calls WITHOUT
# cubest — a tree listing + head of each source file + grep for TODOs.
# All outputs are what the LLM must ingest to reason about the repo.
set -euo pipefail
cd "$(dirname "$0")"
find input -type f | head -40
echo "---"
find input -type f -name '*.py' -exec sh -c 'echo "=== $1"; head -20 "$1"' _ {} \;
echo "---"
grep -rn 'TODO\|FIXME\|HACK' input/ 2>/dev/null || true
