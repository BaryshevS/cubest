#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
CUBEST="${CUBEST:-python3 ../../cubest.py}"
$CUBEST -p '{
  "dimensions": ["campaign", "device"],
  "measures": [
    {"name": "rows", "type": "count"},
    {"name": "impr", "type": "sum", "field": "impressions"},
    {"name": "clicks", "type": "sum", "field": "clicks"},
    {"name": "cost", "type": "sum", "field": "cost"},
    {"name": "cost_p95", "type": "p95", "field": "cost"}
  ],
  "extract": [{"type": "preset", "preset": "csv"}],
  "output": {"format": "flat"}
}' input/ads_report.csv
