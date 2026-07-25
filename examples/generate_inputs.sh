#!/usr/bin/env bash
# Generates synthetic input data for each example scenario.
# All outputs are deterministic (fixed RNG seed) so measurements are reproducible.

set -euo pipefail
cd "$(dirname "$0")"

echo "=== [01] nginx access log (5000 lines) ==="
mkdir -p 01-nginx-5xx/input
python3 -c "
import random; random.seed(42)
paths=['api/v1/users','api/v1/orders','api/v1/search','api/v2/products','static/img.png','static/app.js','admin/panel','healthz','metrics','auth/login']
statuses=[200]*70+[301]*8+[404]*10+[500]*7+[502]*3+[503]*2
methods=['GET']*85+['POST']*12+['PUT']*3
uas=['Mozilla/5.0 (X11; Linux) Chrome/128','Mozilla/5.0 (iPhone) Mobile Safari','curl/8.5','Go-http-client/2.0','Bot/1.0']
for i in range(5000):
    ip='.'.join(str(random.randint(1,254)) for _ in range(4))
    path=random.choice(paths); st=random.choice(statuses); m=random.choice(methods)
    b=random.randint(200,50000); dur=round(random.expovariate(30),3)
    ua=random.choice(uas)
    print(f'{ip} - - [15/Jul/2026:12:{i%60:02d}:00 +0000] \"{m} /{path} HTTP/1.1\" {st} {b} \"-\" \"{ua}\" {dur}')
" > 01-nginx-5xx/input/access.log
gzip -kf 01-nginx-5xx/input/access.log
ls -la 01-nginx-5xx/input/

echo
echo "=== [02] tiny sample repo (~40 files) ==="
mkdir -p 02-repo-onboarding/input/{src/{api,core,util},tests,docs}
cat > 02-repo-onboarding/input/README.md <<'EOF'
# demo-service — order management microservice
EOF
for m in users orders products payments shipping; do
  cat > "02-repo-onboarding/input/src/api/${m}.py" <<EOF
from fastapi import APIRouter
router = APIRouter()

@router.get("/${m}")
def list_${m}(): return []

@router.get("/${m}/{id}")
def get_${m}(id: int): return {"id": id}

@router.post("/${m}")
def create_${m}(payload: dict): return payload

# TODO: add pagination
# FIXME: N+1 query in list_${m}
EOF
done
for m in database cache queue worker scheduler; do
  cat > "02-repo-onboarding/input/src/core/${m}.py" <<EOF
class ${m^}Client:
    def __init__(self, url): self.url = url
    def connect(self): pass
    def close(self): pass

# HACK: hardcoded timeout, revisit
EOF
done
for m in retry_util log_util time_util json_util config_util; do
  cat > "02-repo-onboarding/input/src/util/${m}.py" <<EOF
def helper_a(x): return x + 1
def helper_b(y): return y * 2
def helper_c(z): return str(z)
EOF
done
for m in test_users test_orders test_products test_health; do
  cat > "02-repo-onboarding/input/tests/${m}.py" <<EOF
def test_ok(): assert True
def test_edge(): assert 1 == 1
EOF
done
ls 02-repo-onboarding/input/src/api/ | head

echo
echo "=== [03] MR/PR — 15 changed files list ==="
mkdir -p 03-mr-impact/input
ls 02-repo-onboarding/input/src/api/*.py 02-repo-onboarding/input/src/core/*.py 02-repo-onboarding/input/tests/*.py \
  | sed 's|02-repo-onboarding/input/||' > 03-mr-impact/input/diff-names.txt
wc -l 03-mr-impact/input/diff-names.txt

echo
echo "=== [04] Google-Ads-like CSV (300 rows) ==="
mkdir -p 04-csv-analytics/input
python3 -c "
import random; random.seed(1)
camps=['Brand_Search','Retargeting','Display_RSA','YouTube_Video','Shopping']
devs=['mobile','desktop','tablet']
print('Campaign,Device,Impressions,Clicks,Cost')
for c in camps:
    for d in devs:
        for _ in range(20):
            imps=random.randint(1000,500000); clk=random.randint(10,imps//10); cost=round(clk*random.uniform(0.05,2.5),2)
            print(f'{c},{d},{imps},{clk},{cost}')
" > 04-csv-analytics/input/ads_report.csv
wc -l 04-csv-analytics/input/ads_report.csv

echo
echo "=== [05] SEO — 10-page HTML crawl ==="
mkdir -p 05-seo-audit/input
for i in $(seq 1 10); do
  cat > "05-seo-audit/input/page-$i.html" <<EOF
<!DOCTYPE html><html lang="en">
<head>
<title>Page $i — demo shop</title>
<meta name="description" content="Description for page $i in the demo catalog with useful keywords about shopping and delivery.">
<meta name="keywords" content="shop,demo,page$i">
<link rel="canonical" href="https://example.com/page-$i">
<meta property="og:title" content="Shop page $i">
<meta name="twitter:card" content="summary">
$([ $((i % 3)) -eq 0 ] && echo '<script type="application/ld+json">{"@type":"Product"}</script>')
</head><body>
<h1>Catalog page $i</h1>
<h2>Section A</h2><h3>Item 1</h3><h3>Item 2</h3>
<h2>Section B</h2><h3>Item 3</h3><h3>Item 4</h3>
$([ $((i % 4)) -eq 0 ] && echo '<h1>Bonus heading (duplicate H1)</h1>')
</body></html>
EOF
done
ls 05-seo-audit/input/ | wc -l

echo
echo "=== [06] Disk-usage audit — 300-file tree ==="
mkdir -p 06-disk-usage/input/{cache,logs,backups,media,tmp}
for d in cache logs backups media tmp; do
  for i in $(seq 1 60); do
    dd if=/dev/urandom of="06-disk-usage/input/$d/file_$i.bin" bs=1K count=$((RANDOM % 200 + 1)) 2>/dev/null
  done
done
du -sh 06-disk-usage/input/

echo
echo "=== [07] RSS feed — 3 feeds × 30 items ==="
mkdir -p 07-rss-filter/input
for f in tech-news devops-weekly ai-research; do
python3 -c "
import random; random.seed(hash('$f')%1000)
tags=['python','ai','llm','kubernetes','devops','sre','security','postgres','javascript','rust','go','ml']
print('<?xml version=\"1.0\"?>')
print('<rss version=\"2.0\"><channel>')
print('<title>$f</title><link>https://example.com/$f</link>')
for i in range(30):
    t=random.sample(tags,3)
    print(f'<item><title>Post {i} on '+', '.join(t)+'</title>')
    print(f'<link>https://example.com/$f/post-{i}</link>')
    print(f'<category>{t[0]}</category>')
    print(f'<pubDate>Mon, 0{(i%9)+1} Jul 2026 10:00:00 GMT</pubDate>')
    print(f'<description>Detailed post number {i} on '+', '.join(t)+' — lots of content here about the subject.</description>')
    print('</item>')
print('</channel></rss>')
" > "07-rss-filter/input/$f.xml"
done
ls 07-rss-filter/input/

echo
echo "=== Done. Total input size: ==="
du -sh 0*/input/ 2>/dev/null | tail
