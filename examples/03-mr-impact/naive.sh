#!/usr/bin/env bash
# What an average agent gets: ls -la for each changed path + wc -l for size.
set -euo pipefail
cd "$(dirname "$0")"
while read f; do
  p="../02-repo-onboarding/input/$f"
  [ -f "$p" ] && printf '%-60s %d bytes, ' "$f" "$(wc -c < "$p")"
  [ -f "$p" ] && printf '%d lines\n' "$(wc -l < "$p")"
done < input/diff-names.txt
