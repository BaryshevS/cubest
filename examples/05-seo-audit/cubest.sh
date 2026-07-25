#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
CUBEST="${CUBEST:-python3 ../../cubest.py}"
$CUBEST --profile seo_audit input/
