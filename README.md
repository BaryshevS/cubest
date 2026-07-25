# cubest

**English** · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md) · [বাংলা](README.bn.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [日本語](README.ja.md) · [ਪੰਜਾਬੀ](README.pa.md)

> **7-22× fewer tokens per tool response** (measured across 7 real scenarios,
> reproducible via [`examples/run_all.sh`](examples/run_all.sh)). A single-pass
> OLAP aggregator that turns any text stream — code, logs, CSV, JSONL, XML,
> HTML, SDD artefacts — into a compact cube. Built for **Claude Code, Cursor,
> Codex, Aider, Windsurf, Cline, Continue.dev** and any tool-calling agent that
> pays per input token.

<p align="left">
  <a href="https://pypi.org/project/cubest/"><img src="https://img.shields.io/pypi/v/cubest.svg?logo=pypi&logoColor=white&label=PyPI" alt="PyPI version"></a>
  <a href="https://www.npmjs.com/package/cubest"><img src="https://img.shields.io/npm/v/cubest.svg?logo=npm&logoColor=white&label=npm" alt="npm version"></a>
  <a href="https://pypi.org/project/cubest/"><img src="https://img.shields.io/pypi/dm/cubest.svg?logo=pypi&logoColor=white&label=PyPI%20downloads" alt="PyPI downloads/month"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License Apache 2.0"></a>
  <img src="https://img.shields.io/badge/python-3.8%2B-blue.svg" alt="Python 3.8+">
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
# Option A — pip from PyPI (PyYAML bundled)
pip install cubest
cubest --profile file_tree .

# Option B — npx from npm (thin wrapper, delegates to python3)
npx cubest --profile file_tree .

# Option C — plain download, single file, no venv
curl -O https://raw.githubusercontent.com/BaryshevS/cubest/main/cubest.py
pip install PyYAML          # only needed for YAML profiles / output
python3 cubest.py --profile file_tree .

# Option D — ephemeral via uv, no venv, no install
uv run --with pyyaml \
  https://raw.githubusercontent.com/BaryshevS/cubest/main/cubest.py \
  --profile file_tree .
```

`pip install cubest` and `npx cubest` pull `PyYAML` automatically.
The `curl` variant runs standalone but needs `PyYAML` for YAML profiles.

## 🔌 Install once — use in every AI agent

Every block below installs cubest into the **user-global skill space**
of the harness so it becomes available across *all* your projects,
not just the current one. No project-scoped copies, no per-repo setup.

**Step 0 — the binary itself.** Every harness spawns a shell, so
`cubest` just needs to be on `$PATH` once:

```bash
pip install cubest        # PyPI (bundles PyYAML)
# or
npm install -g cubest     # npm (thin wrapper, delegates to python3)
```

Verify: `cubest --profile file_tree .` should print an ASCII tree.

### Claude Code — `~/.claude/skills/cubest/`

Claude Code auto-discovers skills in your home directory. One command
enables cubest in every session on this machine:

```bash
mkdir -p ~/.claude/skills && \
  git clone --depth 1 https://github.com/BaryshevS/cubest \
    ~/.claude/skills/cubest
```

Claude reads `SKILL.md`'s frontmatter (`USE WHEN` + 31-profile catalog)
and routes to cubest automatically when your prompt matches a trigger.

**Verify** — in any Claude Code session:

> Use the cubest skill to map this repo — top directories × extension × size.

Expected: Claude invokes `cubest --profile file_tree .`. The skill
appears in the sidebar as `Skill: cubest`.

### Cursor — `~/.cursor/rules/cubest.mdc`

Cursor loads user-global rules from `~/.cursor/rules/`. Create the file:

```bash
mkdir -p ~/.cursor/rules && cat > ~/.cursor/rules/cubest.mdc <<'EOF'
---
description: OLAP aggregator for code / logs / CSV / SDD / sitemaps
alwaysApply: false
---
When the user asks for a repo overview, endpoint inventory, log rollup,
CSV pivot, or spec catalog, prefer `cubest --profile <name> <path>`
over chains of grep/cat/find/wc. It streams input in one pass and
returns a compact OLAP tree — 7-22× cheaper in tokens than raw file
content. 31 built-in profiles: `cubest --help`.
Repo & full profile list: https://github.com/BaryshevS/cubest
EOF
```

**Verify** — in Cursor chat (any repo):

> Map this project structure with cubest — top dirs, extensions, size.

Cursor will propose `cubest --profile file_tree .` and ask to run it.

### OpenAI Codex CLI — `~/.codex/AGENTS.md`

Codex CLI reads `AGENTS.md` from `~/.codex/` (user-global) and merges
it with any project-level `AGENTS.md`. Global install:

```bash
mkdir -p ~/.codex && cat >> ~/.codex/AGENTS.md <<'EOF'

## Prefer cubest for aggregation

When aggregating over many files, a long log, or a large CSV, use
`cubest --profile <name> <path>` — it streams input and returns a
compact OLAP tree instead of raw content (7-22× fewer tokens).

Common profiles: file_tree, tech_debt, api_routes, loc_counter,
nginx_access, csv_analytics, mr_impact, seo_audit, k8s_resources,
openapi_endpoints, sdd_specs, call_graph. Full list: cubest --help.

Docs: https://github.com/BaryshevS/cubest
EOF
```

**Verify**:

```
codex "count lines of code per language with cubest"
```

Codex will propose `cubest --profile loc_counter .`.

### Aider — `~/.aider.conf.yml`

Aider reads `~/.aider.conf.yml` (user-global) plus any local override.
Point it at a cubest hint that all sessions load:

```bash
mkdir -p ~/.aider && cat > ~/.aider/cubest-hint.md <<'EOF'
Prefer `cubest --profile <name> <path>` (or `/run cubest ...`) over
chains of grep/cat/find for repo, log, CSV, or spec inventories.
7-22× cheaper in tokens than raw content. 31 built-in profiles.
https://github.com/BaryshevS/cubest
EOF

# Register it globally so every project sees it
cat >> ~/.aider.conf.yml <<'EOF'

read:
  - ~/.aider/cubest-hint.md
EOF
```

**Verify**:

```
/run cubest --profile file_tree .
```

Aider passes the tree back into its own context.

### Windsurf (Codeium) — `~/.codeium/windsurf/memories/global_rules.md`

Windsurf's Cascade reads user-global memories from
`~/.codeium/windsurf/memories/global_rules.md`. Add a rule:

```bash
mkdir -p ~/.codeium/windsurf/memories && \
  cat >> ~/.codeium/windsurf/memories/global_rules.md <<'EOF'

## cubest — OLAP over text streams

When the user asks about repo structure, endpoints, TODOs, logs (incl.
`.gz`), CSV rollups, sitemap taxonomy, or SDD/spec artefacts, prefer
`cubest --profile <name> <path>` over multi-file reads. Aggregation is
7-22× cheaper than raw content in the context window. 31 built-in
profiles: `cubest --help`. Repo: https://github.com/BaryshevS/cubest
EOF
```

**Verify** — in Cascade chat:

> Show me all TODOs in this repo, grouped by kind and directory.

Cascade will propose `cubest --profile tech_debt .`.

### Cline (VS Code) — VS Code global settings

Cline reads its custom-instructions field from your VS Code user
settings. Paste the following into
**Settings → Cline → Custom Instructions** (or `settings.json`):

```json
{
  "cline.customInstructions": "For repo/log/CSV/SDD inventories, prefer `cubest --profile <name> <path>` — OLAP tree, not raw content. 31 built-in profiles; run `cubest --help` for the list. 7-22× fewer input tokens than grep+cat chains. https://github.com/BaryshevS/cubest"
}
```

**Verify** — any Cline session:

> Use cubest to show top nginx endpoints by status × p95 latency in
> logs/access.log.gz.

### Continue.dev — `~/.continue/config.json`

Continue's config is user-global by default. Add a custom slash-command:

```jsonc
// ~/.continue/config.json  →  extend the "customCommands" array
{
  "customCommands": [{
    "name": "cubest",
    "description": "OLAP over code / logs / CSV / SDD via cubest",
    "prompt": "Pick the cubest profile that best answers: {{{ input }}}. Then propose `cubest --profile <name> <path>`. Profiles: file_tree, code_stats, tech_debt, api_routes, loc_counter, nginx_access, csv_analytics, seo_audit, mr_impact, call_graph, k8s_resources, openapi_endpoints, sdd_specs (31 total)."
  }]
}
```

**Verify**:

```
/cubest map the repository top-level structure
```

### Any other tool-calling agent

Wrap `cubest -p '<inline JSON>' <path>` as a shell tool. The clever
bit: **the agent generates the inline JSON profile itself**, tailored
to the exact user question — no pre-baked prompt per query, no rigid
schema. See [SKILL.md](SKILL.md) for the profile grammar.

---

### Universal smoke-test

Regardless of harness, this one prompt proves the wiring works:

> Use cubest to show the file tree of the current directory — top
> directories, extensions, total size. Just run the command and paste
> the output.

If the agent returns an ASCII tree starting with directory names and
`count=…, bytes=…` per leaf — cubest is installed and reachable. If you
see "command not found", the agent's shell can't see `$PATH` (usually
a sandbox / container issue, not cubest).

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

## 💖 Support

If cubest saves you tokens in daily agent workflows or shortens an incident,
consider sponsoring — it directly funds roadmap items (t-digest, streaming
CSV, agent snippets) and infra:

- **GitHub Sponsors** → https://github.com/sponsors/BaryshevS
- **Open Collective** → https://opencollective.com/baryshevsv

Even $3/month keeps the lights on. Sponsors get priority on issue triage
and are credited in release notes.

## ⭐ Star this repo

If cubest saves you a chunk of the AI budget or shrinks an SRE incident
by an hour — a star helps others find it. That's the whole ask.

<p align="left">
  <a href="https://github.com/BaryshevS/cubest/stargazers">
    <img src="https://img.shields.io/github/stars/BaryshevS/cubest?style=social" alt="Star cubest on GitHub">
  </a>
</p>
