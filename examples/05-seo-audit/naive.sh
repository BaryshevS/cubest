#!/usr/bin/env bash
# Naive agent: cats every HTML + prints extracted title/meta lines.
set -euo pipefail
cd "$(dirname "$0")"
for f in input/*.html; do
  echo "=== $f"
  grep -Eo '<title>[^<]+</title>|<h1[^>]*>[^<]+</h1>|<link[^>]*canonical[^>]*>|application/ld\+json' "$f" || true
done
