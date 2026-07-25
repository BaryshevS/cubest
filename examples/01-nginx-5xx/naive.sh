#!/usr/bin/env bash
# What an average agent gets as a tool response WITHOUT cubest.
# The agent asks for a smart awk chain — the best a competent grep/awk user
# would build. It returns all 5xx rows plus per-row latency (needed for
# any percentile reasoning). This is what the LLM must ingest to reason.
set -euo pipefail
cd "$(dirname "$0")"
zcat input/access.log.gz \
  | awk '$9 ~ /^5/ {
      match($0, /"[A-Z]+ (\/[^ ?"]+)/, a);
      print a[1], $9, $NF
    }' \
  | sort
