#!/usr/bin/env bash
# Same answer via cubest — one call, ~300 tokens back.

set -euo pipefail
cd "$(dirname "$0")"
CUBEST="${CUBEST:-python3 ../../cubest.py}"

$CUBEST -p '{
  "dimensions": ["path_root", "status"],
  "measures": [
    {"name": "hits", "type": "count"},
    {"name": "p95_ms", "type": "p95", "field": "duration"}
  ],
  "extract": [
    {
      "type": "regex",
      "multiline": false,
      "pattern": "\"(?P<method>GET|POST|PUT|DELETE) /(?P<path_root>[^/? ]+)[^ ]* HTTP/[\\d.]+\" (?P<status>5\\d{2}) \\d+ \"[^\"]*\" \"[^\"]*\" (?P<duration>[0-9.]+)"
    }
  ],
  "output": {"format": "flat", "top_n": 10}
}' input/access.log.gz
