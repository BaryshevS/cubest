#!/usr/bin/env bash
# geoip_enrich.sh — FALLBACK GeoIP tag for nginx-style access log.
#
# ⚠️ PREFERRED APPROACH: write GeoIP fields to the access log AT nginx time
# using ngx_http_geoip2_module. Post-processing here is a fallback for old
# logs / when you can't touch nginx config.
#
# Why nginx-side is better:
#   - Zero extra I/O (no re-read of every line by a bash loop)
#   - No IP → country cache-miss latency in your ETL
#   - Correct handling of X-Forwarded-For / real_ip chain
#   - Works at nginx throughput (100k+ req/s) — this script will bottleneck
#     at ~1-5k rows/s due to fork/awk per line
#
# nginx configuration example (http_geoip2 module):
#
#   # /etc/nginx/nginx.conf
#   load_module modules/ngx_http_geoip2_module.so;
#   http {
#     geoip2 /usr/share/GeoIP/GeoLite2-City.mmdb {
#       $geoip2_country_code   default=XX  country iso_code;
#       $geoip2_subdivision    default=XX  subdivisions 0 iso_code;
#       $geoip2_city           default=""  city names en;
#     }
#     log_format main_geoip
#       '$remote_addr - $remote_user [$time_local] '
#       '"$request" $status $body_bytes_sent '
#       '"$http_referer" "$http_user_agent" '
#       '$request_time '
#       '$geoip2_country_code $geoip2_subdivision';
#     access_log /var/log/nginx/access.log main_geoip;
#   }
#
# Then cubest parses country/subdivision directly — no bash step needed.
# ------------------------------------------------------------------
#
# This script (fallback only): reads combined format from STDIN, extracts
# remote_addr (first field), looks up ISO country code via geoiplookup or
# mmdblookup, and appends it as an extra column at the end of the line.
#
# Usage:
#   zcat access.log.gz | tools/geoip_enrich.sh > enriched.log
#   tail -f access.log  | tools/geoip_enrich.sh | cubest.py -p frontend_geoip -
#
# Dependencies (pick one):
#   - geoiplookup  (apt-get install geoip-bin — legacy but simple)
#   - mmdblookup   (apt-get install mmdb-bin, needs GeoLite2-Country.mmdb)

set -eu

MMDB="${GEOIP_MMDB:-/usr/share/GeoIP/GeoLite2-Country.mmdb}"

lookup() {
    local ip="$1"
    if command -v mmdblookup >/dev/null && [ -f "$MMDB" ]; then
        mmdblookup --file "$MMDB" --ip "$ip" country iso_code 2>/dev/null \
            | awk -F\" 'NR==1{print $2}'
    elif command -v geoiplookup >/dev/null; then
        geoiplookup "$ip" 2>/dev/null \
            | head -1 \
            | awk -F: '{gsub(/^ */,"",$2); split($2,a,","); print a[1]}'
    else
        echo "--"
    fi
}

# Cache lookups so we do not hit mmdb for every request from the same IP.
declare -A CACHE

while IFS= read -r line; do
    ip="${line%% *}"
    if [ -z "${CACHE[$ip]:-}" ]; then
        cc="$(lookup "$ip")"
        CACHE[$ip]="${cc:-XX}"
    fi
    printf '%s %s\n' "$line" "${CACHE[$ip]}"
done
