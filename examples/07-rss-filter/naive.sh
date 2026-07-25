#!/usr/bin/env bash
# Naive: grep every <category> across all feeds and print them all.
set -euo pipefail
cd "$(dirname "$0")"
for f in input/*.xml; do
  echo "=== $f"
  grep -oE '<title>[^<]+</title>|<category>[^<]+</category>' "$f"
done
