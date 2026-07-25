#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
CUBEST="${CUBEST:-python3 ../../cubest.py}"
$CUBEST -p '{
  "dimensions": ["category", "file"],
  "measures": [{"name": "posts", "type": "count"}],
  "extract": [
    {"type": "regex", "multiline": false, "pattern": "<category>(?P<category>[^<]+)</category>"}
  ],
  "scan": {"include": ["*.xml"]},
  "output": {"format": "flat", "top_n": 20}
}' input/
