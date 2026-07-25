#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
CUBEST="${CUBEST:-python3 ../../cubest.py}"
cat input/diff-names.txt | $CUBEST -F - --profile mr_impact ../02-repo-onboarding/input/
