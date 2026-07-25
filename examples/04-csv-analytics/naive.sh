#!/usr/bin/env bash
# What an average agent gets on a smart awk chain for CSV rollup.
# Note: no percentile — awk can't easily emit p95 without sorting all rows.
set -euo pipefail
cd "$(dirname "$0")"
awk -F, 'NR>1 {
  key=$1 "|" $2
  imp[key]+=$3; clk[key]+=$4; cost[key]+=$5; rows[key]++
}
END {
  printf "%-20s %-10s %10s %8s %10s %6s\n","campaign","device","impressions","clicks","cost","rows"
  for (k in rows) {
    split(k, a, "|");
    printf "%-20s %-10s %10d %8d %10.2f %6d\n", a[1], a[2], imp[k], clk[k], cost[k], rows[k]
  }
}' input/ads_report.csv | sort
