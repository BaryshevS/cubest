#!/usr/bin/env bash
# Run every scenario's measure.sh, save its result into that scenario's
# RESULT.md, then emit an aggregate table on stdout (and into RESULT.md
# at the root of examples/).
set -uo pipefail   # no -e — we tolerate individual failures
cd "$(dirname "$0")"

# Ensure inputs exist. Idempotent — the generator can safely run again.
if [ ! -f 01-nginx-5xx/input/access.log.gz ] || [ ! -f 07-rss-filter/input/tech-news.xml ]; then
    ./generate_inputs.sh >/dev/null
fi

for dir in 01-nginx-5xx 02-repo-onboarding 03-mr-impact 04-csv-analytics \
           05-seo-audit 06-disk-usage 07-rss-filter; do
    if [ -x "$dir/measure.sh" ]; then
        {
            echo "# $dir — measured token cost"
            echo
            "$dir/measure.sh"
        } > "$dir/RESULT.md"
    fi
done

TMP=$(mktemp)
{
  printf '# examples/ — aggregate benchmark\n\n'
  printf '| # | Scenario | Naive tokens | Cubest tokens | Ratio |\n'
  printf '|---|---|---:|---:|---:|\n'
  for dir in 01-nginx-5xx 02-repo-onboarding 03-mr-impact 04-csv-analytics \
             05-seo-audit 06-disk-usage 07-rss-filter; do
      lines=$(sed -n '5,6p' "$dir/RESULT.md")
      naive=$( echo "$lines" | awk -F'|' 'NR==1 {gsub(/[ *]/,""); print $4}')
      cubest=$(echo "$lines" | awk -F'|' 'NR==2 {gsub(/[ *]/,""); print $4}')
      ratio=$(python3 -c "print(f'{${naive:-0}/max(${cubest:-1},1):.1f}')")
      printf '| %s | %s | %s | %s | %sx |\n' "${dir%%-*}" "${dir#*-}" "$naive" "$cubest" "$ratio"
  done
} > "$TMP"
cat "$TMP" | tee RESULT.md >/dev/null
cat RESULT.md
rm -f "$TMP"
