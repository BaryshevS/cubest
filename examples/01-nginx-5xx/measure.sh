#!/usr/bin/env bash
# Measure token counts (chars / 4) for naive vs cubest approach.

set -uo pipefail
cd "$(dirname "$0")"

naive_chars=$(./naive.sh | wc -c)
cubest_chars=$(./cubest.sh | wc -c)

naive_tok=$((naive_chars / 4))
cubest_tok=$((cubest_chars / 4))
ratio=$(python3 -c "print(f'{$naive_tok / max($cubest_tok, 1):.1f}')")

printf '| Approach | Chars | Est. tokens |\n'
printf '|---|---:|---:|\n'
printf '| Naive (read log) | %d | %d |\n' "$naive_chars" "$naive_tok"
printf '| Cubest           | %d | %d |\n' "$cubest_chars" "$cubest_tok"
printf '| **Ratio**        |   | **%sx** |\n' "$ratio"
