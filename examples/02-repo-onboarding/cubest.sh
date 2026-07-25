#!/usr/bin/env bash
# Three targeted cuts instead of reading every file.
set -euo pipefail
cd "$(dirname "$0")"
CUBEST="${CUBEST:-python3 ../../cubest.py}"
$CUBEST --profile file_tree input/
echo "---"
$CUBEST --profile api_routes input/
echo "---"
$CUBEST --profile tech_debt input/
