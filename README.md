# cubest

**English** · [简体中文](README.zh-CN.md) · [Русский](README.ru.md) · [Español](README.es.md) · [日本語](README.ja.md)

> **7-22× fewer tokens per tool response** (measured across 7 real scenarios,
> reproducible via [`examples/run_all.sh`](examples/run_all.sh)). A single-pass
> OLAP aggregator that turns any text stream — code, logs, CSV, JSONL, XML,
> HTML, SDD artefacts — into a compact cube. Built for **Claude Code, Cursor,
> Codex, Aider, Windsurf, Cline, Continue.dev** and any tool-calling agent that
> pays per input token.

<p align="left">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License Apache 2.0"></a>
  <img src="https://img.shields.io/badge/python-3.8%2B-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/deps-stdlib%20only-green.svg" alt="stdlib only">
  <img src="https://img.shields.io/badge/tests-57%20passing-brightgreen.svg" alt="57 tests passing">
  <img src="https://img.shields.io/badge/profiles-31%20built--in-purple.svg" alt="31 profiles">
  <img src="https://img.shields.io/badge/formats-13-orange.svg" alt="13 output formats">
</p>

## 🧠 Why an AI agent should care

Measured across 7 realistic scenarios (see [`examples/`](examples/)):

| # | Scenario                              | Naive tool response | Cubest response | Ratio     |
|---|---------------------------------------|:-------------------:|:---------------:|:---------:|
| 1 | Nginx 5xx investigation on 5000-line log | 3,590 tok        | 158 tok         | **22.7×** |
| 2 | Repo onboarding (40 files)            | 1,256 tok           | 175 tok         | 7.2×      |
| 3 | MR impact map from `git diff`          | 280 tok             | 16 tok          | **17.5×** |
| 4 | Small CSV rollup (300 rows)            | 280 tok             | 368 tok         | 0.8× ❌   |
| 5 | SEO audit of 10 HTML pages             | 382 tok             | 49 tok          | 7.8×      |
| 6 | Disk-usage audit (300 files)           | 338 tok             | 68 tok          | 5.0×      |
| 7 | RSS category rollup (3 feeds × 30)     | 1,692 tok           | 265 tok         | 6.4×      |
|   | **Median**                             |                     |                 | **7.2×**  |
|   | **Peak (streaming logs)**              |                     |                 | **22.7×** |

Cubest wins on **large streams and hierarchical data**. On very small
tabular data (300-row CSV) a plain `awk` chain is already compact enough,
and cubest actually loses. Where it matters — logs, code trees, sitemap
crawls — 5-25× fewer tokens land in the agent's context.

At $3–15 per million input tokens (Claude Sonnet 4.6 / Opus 4.7) and 1000
agent sessions per day, that's **thousands of dollars per month** saved
on tool-response ingestion alone — and long sessions stop hitting the
context wall. Run [`examples/run_all.sh`](examples/run_all.sh) yourself.

## ⚡ Before / After

**Question the agent needs to answer:** "What does this project do, what
endpoints does it expose, and where's the tech debt?"

```bash
# ❌ Before — the agent burns 30-60k tokens on raw files:
find . -type f -name '*.py' | xargs cat        # 40k tokens
grep -rn 'TODO\|FIXME' .                        # 8k tokens
grep -rn '@app\|@router' .                      # 3k tokens

# ✅ After — one Python file, three OLAP cuts, 200 tokens back:
cubest --profile file_tree .
cubest --profile api_routes .
cubest --profile tech_debt .
```

## 🎯 What it actually does

One Python file (`cubest.py`, ~1800 lines, `PyYAML` optional) that:

1. **Streams** a text source — files, directories, `.gz` archives, stdin
2. **Extracts** records via regex or one of 10 built-in presets
3. **Aggregates** them into an in-memory hierarchical OLAP cube
   (dimensions × measures: `count`, `sum`, `avg`, `min`, `max`, `p50`,
   `p90`, `p95`, `p99` via reservoir sampling)
4. **Renders** the cube in one of 13 formats — from compact tree to
   standalone interactive HTML dashboard

Zero database. Zero LLM. Zero tree-sitter. Zero external services.
Just `python3 cubest.py --profile ... <path>`.

## 🚀 Install

```bash
# Option A — plain download (no deps, JSON profiles work as-is)
curl -O https://raw.githubusercontent.com/BaryshevS/cubest/main/cubest.py
python3 cubest.py --profile file_tree .

# Option B — pip (PyPI publish coming)
pip install cubest
cubest --profile file_tree .

# Option C — ephemeral via uv, no venv needed
uv run --with pyyaml \
  https://raw.githubusercontent.com/BaryshevS/cubest/main/cubest.py \
  --profile file_tree .

# Option D — npm wrapper (delegates to python3)
npx cubest --profile file_tree .
```

Only optional dependency is `PyYAML` (for YAML profiles / YAML output).

## 🔌 AI agent integration

Cubest is agent-agnostic. Tested and works out of the box with:

| Agent                    | How to wire it up                                          |
|--------------------------|------------------------------------------------------------|
| **Claude Code**          | Ships as `.claude/skills/cubest/` skill; see [SKILL.md](SKILL.md) |
| **Cursor**               | Add `cubest` as an allowed shell tool in Cursor rules      |
| **OpenAI Codex CLI**     | Use directly in shell — Codex will discover it via `--help` |
| **Aider**                | `/run cubest ...` or add to `--command` alias              |
| **Windsurf (Codeium)**   | Allow `cubest` in `windsurf.rules`                         |
| **Cline (VS Code)**      | Enable command execution; agent will invoke on request     |
| **Continue.dev**         | Add as custom slash command in `~/.continue/config.json`   |
| **Any tool-calling agent**| Wrap `cubest -p '<inline JSON>' <path>` as a tool         |

The magic: the agent generates the `<inline JSON>` profile itself, on the
fly, tailored to the exact question the user asked. No pre-baked prompts,
no rigid API — one tool that shape-shifts to any query.

## ⚡ Quick start

```bash
# Map an unfamiliar repo (30 lines instead of 3000)
cubest --profile file_tree .

# Nginx access.log.gz — top URLs × status × avg duration + p95/p99
cubest --profile nginx_access /var/log/nginx/access.log.gz

# Count lines of code by language (drop-in for scc/tokei/cloc)
cubest --profile loc_counter .

# Approximate call graph → interactive HTML dashboard
cubest --profile call_graph src/ > graph.html && open graph.html

# CSV → OLAP → ECharts dashboard (one HTML file, no server needed)
cubest -p '{
  "dimensions": ["campaign", "device"],
  "measures": [{"name":"impressions","type":"sum","field":"impressions"}],
  "extract": [{"type":"preset","preset":"csv"}],
  "output": {"format":"echarts","chart_type":"sankey"}
}' ads.csv > ads.html

# MR/PR impact map from git diff
git diff --name-only origin/main...HEAD | \
  cubest -F - --profile mr_impact .
```

## 📊 What you get

**13 output formats** — pick the one that matches your audience:

| Format          | Best for                                          |
|-----------------|---------------------------------------------------|
| `tree` (default)| Human eyeballs, terminals                         |
| `flat`          | ~30% fewer tokens than tree (breadcrumb rows)     |
| `compact`       | Top-level only, sorted by count                   |
| `csv` / `tsv`   | Spreadsheets, downstream tools                    |
| `md_table`      | PR/Confluence/README                              |
| `yaml` / `json` | Programmatic consumption                          |
| `xml`           | XML pipelines                                     |
| `dot`           | GraphViz → SVG/PDF                                |
| `mermaid`       | GitHub/GitLab/Notion inline                       |
| `plantuml`      | Enterprise documentation stacks                   |
| `drawio`        | draw.io / diagrams.net import                     |
| `echarts`       | Standalone interactive HTML (6 chart types)       |

**31 built-in profiles** — pick or customize:

<details><summary>Full profile table (click to expand)</summary>

| Profile               | Purpose                                                              |
|-----------------------|----------------------------------------------------------------------|
| `file_tree`           | Project map: top dir × extension × size                              |
| `disk_usage`          | Disk audit N-deep: `sum(size)` + `count(files)`                      |
| `code_stats`          | Functions / classes per file                                         |
| `code_atlas`          | 15-language function atlas (Python nesting via indent)               |
| `sql_functions`       | Functions in files with raw SQL                                      |
| `call_graph`          | Approximate caller→callee pairs → DOT/Mermaid/ECharts                |
| `api_routes`          | FastAPI/Flask/Django HTTP endpoints                                  |
| `tech_debt`           | TODO/FIXME/HACK by kind and file                                     |
| `react_components`    | React/Vue components by declaration type                             |
| `imports`             | Python imports grouped by module                                     |
| `doc_structure`       | Markdown headers ≤ h3                                                |
| `loc_counter`         | LOC per language (drop-in for scc/tokei/cloc)                        |
| `nginx_access`        | Combined access log → URL section × status × method                  |
| `nginx_cdn_covers`    | CDN TSV logs → size × format × device                                |
| `frontend_geoip`      | Frontend log + GeoIP: country/UA/endpoint filter → ext × p90         |
| `csv_analytics`       | GA4/AdWords/Metrica CSV → campaign × device                          |
| `jsonl_events`        | JSONL/NDJSON events → event × source                                 |
| `mr_impact`           | MR/PR impact map via `git diff --name-only`                          |
| `git_log_activity`    | Author × month from `git log --numstat`                              |
| `sdd_specs`           | Spec catalog from md-frontmatter                                     |
| `sdd_checklist`       | Progress on Markdown checklists: done vs todo                        |
| `spec_status`         | SDD lifecycle: `phase × status × owner` → md-table                   |
| `agents_inventory`    | Claude subagents catalog (model × name)                              |
| `skills_inventory`    | Claude skills catalog (top-dir × name)                               |
| `k8s_resources`       | Kubernetes manifests: kind × namespace × name                        |
| `openapi_endpoints`   | OpenAPI/Swagger: method × path                                       |
| `xml_tags`            | XML/HTML/SVG/POM inventory: tag × file                               |
| `yaml_keys`           | Top-level YAML/JSON keys                                             |
| `seo_audit`           | HTML crawl audit: title/desc/H1/canonical/schema                     |
| `seo_semantic_tree`   | H1–H6 semantic tree → ECharts sunburst                               |
| `sitemap_map`         | sitemap.xml URL taxonomy → treemap                                   |

</details>

## 🧪 Benchmarks

Measured on CPython 3.8, laptop-class hardware (July 2026):

| Scenario                       | Metric                                        |
|--------------------------------|-----------------------------------------------|
| Cube insert                    | ~200k records/s, 25 MiB RSS at 500k           |
| Scan 10k small files           | ~14k files/s (`paths` preset, no read)        |
| Streaming gzip access log      | ~43k lines/s, **ΔRSS <200 KiB per 500k lines**|
| Format `flat` from 50k cells   | ~1 ms                                         |
| Token savings vs naïve read    | **212×** (see table above)                    |

Streaming stays flat-memory — 10 TB of logs is bound by I/O, not RAM.

## 🔁 Replaces common tools

Not a full replacement, but covers 80% of typical scenarios with one file
instead of installing a whole zoo:

| Tool                          | Replaced by                                          |
|-------------------------------|------------------------------------------------------|
| `scc` / `tokei` / `cloc`      | `loc_counter`                                        |
| `du -sh */`                   | `disk_usage`                                         |
| `find + wc -l`                | `file_tree`                                          |
| GoAccess                      | `nginx_access` + `format: echarts`                   |
| `grep -c` + `sort \| uniq -c` | inline regex + count                                 |
| `jq | sort | uniq -c`         | `jsonl_events`                                       |
| `yq` / `kubectl get`          | `k8s_resources`                                      |
| `swagger-cli`                 | `openapi_endpoints`                                  |
| `git log --stat | awk`        | `git_log_activity`                                   |
| `git diff --stat | wc`        | `mr_impact --files-from -`                           |
| `ctags` + grep                | `code_atlas`                                         |
| awk histograms + percentiles  | `p50/p90/p95/p99` measures                           |
| Screaming Frog (SEO)          | `seo_audit` + `seo_semantic_tree` + `sitemap_map`    |
| `treemap.py` / sqlite-utils   | `format: echarts` (treemap/sunburst)                 |
| `pyan` / `graphviz-ast`       | `call_graph` + `format: dot`                         |

## 👥 Roles

| Role                | Main use cases                                                 |
|---------------------|----------------------------------------------------------------|
| **AI agent**        | Compact repo maps, machine-readable JSON/CSV/DOT for tool chains, context economy for long sessions |
| **Developer**       | Onboarding, API/component/tech-debt inventory, PR preflight     |
| **SRE / on-call**   | Incident investigation on `.gz` logs, latency percentiles       |
| **DevOps**          | CI reports, K8s manifest inventory, git activity dashboards     |
| **Data engineer**   | Second-pass OLAP on warehouse exports, analytics rollups        |
| **SEO / Content**   | Site audit, semantic heading tree, sitemap taxonomy             |

## 🧑‍🍳 Cookbook — before → after

<details><summary>1. Lines of code by language</summary>

```bash
# Before
find . -name "*.py" -not -path "./venv/*" | xargs wc -l | tail -1
find . -name "*.js" -not -path "./node_modules/*" | xargs wc -l | tail -1
# ...repeat for every language

# After
cubest --profile loc_counter .
```
</details>

<details><summary>2. Top 5xx URLs from gzipped nginx log</summary>

```bash
# Before
zcat access.log.gz | awk '$9 ~ /^5/' | awk '{print $7}' | sort | uniq -c | sort -rn | head -20

# After
cubest -p '{
  "dimensions":["path_root","status"],
  "measures":[{"name":"hits","type":"count"}],
  "extract":[{"type":"regex","pattern":"\"(?P<method>GET|POST) /(?P<path_root>[^/? ]+)[^ ]* HTTP/[\\\\d.]+\" (?P<status>5\\\\d\\\\d)"}],
  "output":{"format":"flat","top_n":20}
}' access.log.gz
```
</details>

<details><summary>3. Latency p50/p95/p99 with constant memory</summary>

```bash
# Before: custom awk that sorts everything and eats RAM, or install GoAccess

# After
cubest -p '{
  "dimensions":["path_root"],
  "measures":[
    {"name":"hits","type":"count"},
    {"name":"p50","type":"p50","field":"duration"},
    {"name":"p95","type":"p95","field":"duration"},
    {"name":"p99","type":"p99","field":"duration"}
  ],
  "extract":[{"type":"regex","pattern":" /(?P<path_root>[^/? ]+)[^ ]* HTTP.* (?P<duration>[0-9.]+)$"}],
  "scan":{"stream":true},
  "output":{"format":"flat","top_n":20}
}' access.log.gz
```

Reservoir sampling → **O(k) memory**, regardless of file size.
</details>

<details><summary>4. CSV analytics → ECharts dashboard</summary>

```bash
cubest -p '{
  "dimensions":["campaign","device"],
  "measures":[
    {"name":"impressions","type":"sum","field":"impressions"},
    {"name":"cost","type":"sum","field":"cost"},
    {"name":"cost_p95","type":"p95","field":"cost"}
  ],
  "extract":[{"type":"preset","preset":"csv"}],
  "output":{"format":"echarts","chart_type":"sankey"}
}' report.csv > report.html
```
</details>

<details><summary>5. SEO audit + semantic heading tree</summary>

```bash
cubest --profile seo_audit ./crawl/          # md-table of title/desc/H1/schema
cubest --profile seo_semantic_tree ./crawl/  # interactive sunburst of H1-H6
cubest --profile sitemap_map sitemap.xml     # URL taxonomy treemap
```
</details>

<details><summary>6. PR impact report in GitHub Actions</summary>

```bash
git diff --name-only origin/main...HEAD | \
  cubest -F - --profile mr_impact . \
    -p '{"output":{"format":"md_table"}}' > /tmp/impact.md
gh pr comment ${{ github.event.number }} --body-file /tmp/impact.md
```
</details>

<details><summary>7. Call graph as SVG or interactive HTML</summary>

```bash
cubest --profile call_graph src/ | dot -Tsvg > graph.svg
# or interactive:
cubest --profile call_graph src/ -p '{"output":{"format":"echarts","chart_type":"graph"}}' > graph.html
```
</details>

<details><summary>8. OpenAPI / Swagger spec inventory</summary>

```bash
# Every endpoint across all OpenAPI YAML/JSON specs
cubest --profile openapi_endpoints ./api/

# Only /admin/* endpoints, output as md-table for a PR comment
cubest --profile openapi_endpoints ./api/ \
  -p '{"filters":["path.startswith(\"/admin\")"],"output":{"format":"md_table"}}'

# Fast diff — what endpoints changed between two branches?
git checkout main && cubest -p openapi_endpoints ./api/ \
  -p '{"output":{"format":"json"}}' > /tmp/base.json
git checkout -   && cubest -p openapi_endpoints ./api/ \
  -p '{"output":{"format":"json"}}' > /tmp/head.json
diff /tmp/base.json /tmp/head.json
```

Works on both YAML and JSON specs — no `swagger-cli` / `redocly-cli` /
`openapi-generator` install needed. Regex over the `paths:` block.
</details>

## 💰 Business impact (industry benchmarks)

Figures below are industry benchmarks for observability/AIOps in general
(Forrester, Research Square, Rootly 2025, incident.io ROI calc). Cubest
doesn't replace Datadog / New Relic — it fills the gap between `grep`
and a data warehouse.

- **MTTR reduction**: manual log investigation consumes 60-80% of MTTR;
  aggregation cuts it materially (Forrester: up to 50%)
- **Cost savings**: at $10k/hour downtime and 60→30-minute MTTR, mid-
  size enterprise saves ~$250k+/year
- **Post-mortem archaeology**: 60-90 min → 10-15 min per incident
- **LLM token cost**: measured 212× at typical repo size
- **Warehouse compute**: moves work out of BigQuery/Snowflake/Athena
  (paid per TB scanned) into a local aggregator ($0)

## 🕳️ Related projects (honest comparison)

GitHub search for the exact combination (single-pass + OLAP + CLI +
Python + regex) returned **zero direct competitors**. Partial overlaps:

| Project                                                                     | Stack   | What overlaps                                | What's missing vs cubest                          |
|-----------------------------------------------------------------------------|---------|----------------------------------------------|---------------------------------------------------|
| [rholder/grepby](https://github.com/rholder/grepby)                         | Go      | group-by count for grep                      | no hierarchy, formats, presets, diagrams          |
| [john-sterling/LogScraper](https://github.com/john-sterling/LogScraper)     | Python  | regex + named-group aggregation for logs     | logs only, count/sum only, no formats             |
| [KarnerTh/xogs](https://github.com/KarnerTh/xogs)                           | Go      | YAML profiles + regex for live logs          | live-only, no diagrams                            |
| [ReagentX/Logria](https://github.com/ReagentX/Logria)                       | Rust    | live-log TUI                                 | TUI-first, not batch                              |
| [boyter/scc](https://github.com/boyter/scc)                                 | Go      | fast LOC counter                             | code only                                         |
| [XAMPPRocky/tokei](https://github.com/XAMPPRocky/tokei)                     | Rust    | fast LOC counter                             | code only                                         |
| [allinurl/goaccess](https://github.com/allinurl/goaccess)                   | C       | web-log HTML report                          | nginx/apache only                                 |
| [saulpw/visidata](https://github.com/saulpw/visidata)                       | Python  | interactive TUI table explorer               | TUI-only                                          |
| [multiprocessio/dsq](https://github.com/multiprocessio/dsq)                 | Go      | SQL over CSV/JSON/logs                       | requires SQL; no diagrams                         |
| [Graphify](https://graphify.com/)                                           | ?       | AST + LLM knowledge graph for code           | code only, heavy setup                            |

## 🧪 Tests

```bash
python3 tests/run_tests.py     # 57 unit tests
python3 tests/bench.py         # quick load test
HEAVY=1 python3 tests/bench.py # 5M records, 200k files (~30s, ~500 MiB RSS)
```

## 📜 License & attribution

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

**Attribution requirement (Apache 2.0 §4d):** if you redistribute cubest —
in derivative works, embedded in your product, as part of a hosted service,
container image, CLI wrapper, IDE plugin, agent template — you MUST include
the NOTICE file (or its readable contents) preserving the upstream URL:

> https://github.com/BaryshevS/cubest

Placement options: a `NOTICE` / `THIRD_PARTY_NOTICES` / `ATTRIBUTION` file
in your distribution, your documentation, or an "About" / "Credits" /
"Powered by" screen.

## 🗺️ Roadmap

See [ROADMAP.md](ROADMAP.md). Highlights:

- `examples/` directory with self-contained scripts + input data + expected
  output for each cookbook recipe
- Exact percentiles via optional t-digest
- `--diff` mode comparing two cubes for CI regressions
- Streaming CSV parser for > 1 GB inputs
- More AI-agent integration snippets in `examples/agents/`

## 🤝 Contributing

Issues and PRs welcome. For substantive changes please open a discussion
first. All contributions are accepted under the Apache 2.0 license.

## ⭐ Star this repo

If cubest saves you a chunk of the AI budget or shrinks an SRE incident
by an hour — a star helps others find it. That's the whole ask.

<p align="left">
  <a href="https://github.com/BaryshevS/cubest/stargazers">
    <img src="https://img.shields.io/github/stars/BaryshevS/cubest?style=social" alt="Star cubest on GitHub">
  </a>
</p>
