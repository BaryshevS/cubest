#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
n=$(./naive.sh | wc -c); c=$(./cubest.sh | wc -c)
printf '| Approach | Chars | Est. tokens |\n|---|---:|---:|\n'
printf '| Naive (du + find/sort) | %d | %d |\n' "$n" "$((n/4))"
printf '| Cubest (disk_usage)    | %d | %d |\n' "$c" "$((c/4))"
python3 -c "print(f'| **Ratio** | | **{$n/max($c,1):.1f}x** |')"
