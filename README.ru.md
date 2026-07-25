# cubest — универсальный single-pass OLAP-индексатор

[English](README.md) · [简体中文](README.zh-CN.md) · **Русский** · [Español](README.es.md) · [日本語](README.ja.md)

> **7–22× меньше токенов на запрос AI-агенту.** Single-pass OLAP-агрегатор
> для любого текстового потока — код, логи, CSV, JSONL, XML, HTML,
> SDD-артефакты. Для **Claude Code, Cursor, Codex, Aider, Windsurf, Cline,
> Continue.dev** и любого AI-агента, платящего за input-токены.
> Измеренные результаты — в [`examples/`](examples/) (воспроизводимо через
> `./run_all.sh`).

---

Один Python-файл. Читает поток текстовых записей (файлы кода, логи, TSV/CSV,
JSONL, экспорты аналитики, дампы колоночных БД) за **один проход**, строит
в памяти иерархический OLAP-куб по указанным измерениям (dimensions) и
считает меры (measures: count / sum / avg / min / max), затем печатает
компактное дерево, breadcrumb-строки, CSV или JSON.

Проектная цель — **не тянуть содержимое исходников в контекст LLM**.
Вместо десятков `cat`+`grep` — один запуск с готовым агрегатом на выходе,
десятки-сотни строк вместо десятков тысяч.

## Ключевые свойства

- Один файл, только `pyyaml` из зависимостей (JSON-профили работают и без него).
- Поддержка gzip: `.gz` → авто-streaming построчно.
- Автопереключение в streaming-режим на файлах > 10 MiB.
- Gitignore-подобные фильтры: `*.py`, `docs/**/*.md`, `node_modules/`,
  `/README.md`, `!keep.me` (negation).
- Пресеты: `paths` (метаданные путей, не читая файл), `funcs`, `headers`, `lines`.
- Форматы вывода: `tree`, `flat` (breadcrumb), `compact`, `csv`, `json`.
- Экономия токенов: `top_n`, `min_count`, `max_lines`, `max_depth`,
  `human_bytes`.

## Value proposition — что здесь самое ценное

Приоритизировано по трём осям: **Impact** (насколько меняет workflow),
**Uniqueness** (насколько отсутствует у альтернатив), **Frequency** (как
часто пригождается). Максимум по оси = 5. Суммарный score из 15.

| # | Что даёт                                                   | Impact | Uniq | Freq | Total | Кому важнее всего                            |
|---|-------------------------------------------------------------|:------:|:----:|:----:|:-----:|----------------------------------------------|
| 1 | **Экономия токенов LLM** через свёртку потока в агрегат     | 5      | 5    | 5    | **15** | AI-агенты (Claude Code, Cursor, Codex)      |
| 2 | **Динамическая гибкость** — inline JSON/YAML профиль полностью параметризует вход/обработку/выход | 5 | 5 | 4 | **14** | AI-агенты, автоматизация в CI                 |
| 3 | **Универсальность формата** — 15+ типов данных одним tool (код/логи/csv/xml/html/json/sdd/k8s/openapi) | 4 | 5 | 5 | **14** | Все роли; заменяет 10+ CLI-утилит             |
| 4 | **Работа с терабайтными файлами** через streaming .gz + reservoir sampling (O(k) память) | 5 | 4 | 4 | **13** | SRE, data-инженер |
| 5 | **12 форматов вывода** — от tree/csv/md до dot/mermaid/plantuml/drawio/echarts | 4 | 5 | 4 | **13** | Team leads, PR-workflow, LLM-агенты          |
| 6 | **Zero-install** — один Python-файл, только stdlib для JSON-профилей | 4 | 4 | 4 | **12** | Container/CI, air-gapped envs, quick ad-hoc  |
| 7 | **Percentile из коробки** (p50/p90/p95/p99 через reservoir) без t-digest / HDR-hist deps | 4 | 5 | 3 | **12** | SRE, performance-инженер                     |
| 8 | **Скорость** — 200k rec/s insert, 43k lines/s gzip stream (CPython 3.8) | 3 | 3 | 5 | **11** | Все роли                                     |
| 9 | **Готовая визуализация без спина инфры** — интерактивный ECharts HTML в один файл | 4 | 4 | 3 | **11** | Обмен результатами с не-техн. командой       |
| 10| **Composability** — stdin, pipe, `-F -` для файловых списков (MR-workflow) | 3 | 3 | 4 | **10** | DevOps, CI-скрипты                           |
| 11| **Reproducibility** — YAML-профиль в git → одинаковый результат в CI и локально | 3 | 3 | 4 | **10** | Team leads, аудит, приёмка                   |
| 12| **Approximate call-graph** без tree-sitter/AST-setup       | 3      | 4    | 2    | 9     | Разработчик при onboarding                   |
| 13| **Air-gapped безопасность** — работает без интернета (echarts CDN vendorable) | 3 | 4 | 2 | 9     | On-prem, enterprise, регулируемые среды      |

### Top-3 ключевых свойств (что здесь по-настоящему уникально)

**🥇 #1 — Экономия токенов LLM-агентов.** Это главный value для 2026-эпохи.
Один запуск сворачивает содержимое сотен файлов в 20-100 строк агрегата
(вместо 30-60k input-токенов при обычном read/grep). При $3-15/M токенов
(Opus/Sonnet) на LLM-heavy workflow экономия — **20-50× за операцию**,
переводит длинные сессии из «упирается в контекст» в «делает больше».

**🥇 #2 — Динамическая гибкость.** Агент сам генерирует профиль inline
(dimensions, measures, filters, format) под каждый конкретный вопрос
пользователя. Не нужно писать код или добавлять шаблоны — вся логика
в одном JSON, который агент собирает на лету. Никакие awk/jq/sql/du/wc
такого не дают: там для каждой задачи нужен свой синтаксис.

**🥇 #3 — Универсальность на 15+ типов данных.** Один инструмент вместо
`scc + tokei + cloc + GoAccess + jq-агрегаты + yq-инвентарь + pyan + awk
+ Graphviz + du + Screaming Frog`. Уменьшает cognitive load, не требует
переключения контекста между 10 разными CLI.

### Что отличает cubest от «универсальных» альтернатив

- **vs DuckDB/dsq/q (SQL-on-files)**: SQL требует полноценного
  парсера входа (для nginx — регулярка через `regexp_matches`),
  выгрузка идёт в таблицу. cubest работает regex-first,
  сохраняет иерархию OLAP-cube нативно, отдаёт диаграммы из коробки.
- **vs визуализатор (Grafana / Kibana)**: требуют развёрнутого стека,
  индексов, retention. cubest — one-shot, self-contained HTML.
- **vs AIOps (Datadog / New Relic)**: SaaS с оплатой per host/GB.
  cubest — 0$, работает над архивом на локальном диске.
- **vs Graphify (AST + LLM knowledge graph)**: тяжёлый setup + LLM
  инференс. cubest — быстрая эвристика без LLM, дополняет Graphify
  на слое OLAP-агрегатов для не-code данных.

## Роли и типовые задачи

### Разработчик
- **Onboarding в незнакомый монорепо**: `file_tree` даёт карту за 30 строк
  вместо 3k строк листингов
- **Инвентарь**: `api_routes` (все HTTP endpoints), `code_atlas` (функции
  по 15 языкам), `react_components`, `imports`, `tech_debt` (TODO/FIXME)
- **Автодокументация**: file → class → method → nested function в один
  запуск (`code_atlas` с `parent`/`depth` для Python)
- **Approx call-graph**: `call_graph` + `format: dot|mermaid|echarts` —
  быстрый скетч архитектуры без tree-sitter
- **PR-preflight**: `mr_impact` по `git diff --name-only` — увидеть
  распределение изменений до отправки на ревью

### SRE / on-call
- **Расследование инцидента**: агрегат `nginx_access.log.gz` за минуты
  вместо часов ручного `grep|awk|sort|uniq` — сокращение investigation
  phase (обычно 60-80% MTTR) через готовый OLAP-cut
- **Latency-профиль**: `p50/p90/p95/p99` над длительностями запросов из
  логов, с memory O(k) — прогонится над терабайтом gzip без OOM
- **Blast-radius для deployment**: изменённые сервисы × кластеры ×
  количество вызовов через `mr_impact`
- **CDN-аудит**: `nginx_cdn_covers` — топ форматов/размеров/устройств
  за окно
- **Kubernetes-inventory**: `k8s_resources` по helm-chart / kustomize
- **Disk-clean**: `disk_usage` до глубины 2-3 с `content_match` для
  таргетинга (например, только логи старше X)

### DevOps
- **CI-отчёты**: junit/allure XML → agg по suite × status × avg(duration)
- **API-инвентарь**: `openapi_endpoints` — счёт `method × path` по всем
  спекам репо
- **Config-audit**: `yaml_keys` — что вообще есть в куче YAML/JSON
  манифестов (docker-compose, GHA, GitLab CI, Terraform yaml, Ansible)
- **Git-активность**: `git_log_activity` — MD-таблица авторов и вкладов
  для quarterly review

### Data-инженер
- **Второй OLAP-проход** после ClickHouse/DuckDB/Athena экспорта: SQL
  выдаёт данные в TSV → cubest делает финальный cut без запроса на
  кластер (экономия compute)
- **Ad/analytics rollup**: `csv_analytics` — GA4/AdWords/Metrica-выгрузки
  сводятся в 30-100 строк вместо десятков тысяч
- **JSONL-поток**: `jsonl_events` — event × source × schema-версия
- **Sample-based percentile**: `p95/p99` над метриками без t-digest-
  зависимости

### AI-специалист / prompt-engineer
- **SDD-каталог**: `spec_status` — MD-таблица `phase × status × owner`
  для дашборда фаз в PR
- **Прогресс приёмки**: `sdd_checklist` — done vs todo per file
- **Каталог агентов и скиллов**: `agents_inventory`, `skills_inventory`
  для аудита длины descriptions, модели, обязательных полей

### AI-агент (Claude Code / Cursor / Codex)
- **Компактная карта репо** вместо 30k токенов листингов — один tool
  call сворачивает содержимое в 30 строк tree/flat
- **Machine-readable**: JSON/YAML/CSV/DOT для последующих tool-цепочек
- **Экономия контекста в длинных сессиях**: сотни kb → сотни байт
- **Prescan гипотез**: «есть ли X в проекте, где, сколько» — одним
  запуском, вместо десятков read/grep

## Замена популярных инструментов (drop-in для многих задач)

Не полная замена, но покрывает 80% типовых сценариев одним скриптом
без установки массы CLI:

| Инструмент          | Что заменяет cubest                                                | Профиль / рецепт                          |
|---------------------|----------------------------------------------------------------------|-------------------------------------------|
| **scc / tokei / cloc** | LOC-каунт по языкам с делением на code / blanks / comments        | `loc_counter`                             |
| **cloc --by-file**  | LOC по файлам                                                         | `--profile loc_counter --dimensions [file]` (inline) |
| **du -sh */**       | disk-usage до N-й глубины + подсчёт файлов                            | `disk_usage`                              |
| **find + wc -l**    | inventory файлов по типу/пути без запуска wc                          | `file_tree`                               |
| **GoAccess**        | базовые агрегаты nginx-логов (URL × status × avg duration + HTML)     | `nginx_access` + `format: echarts`        |
| **grep -c PAT**     | счётчик вхождений с группировкой по файлу/каталогу                    | inline-regex + count                      |
| **ripgrep + xargs** | «найти все места + сгруппировать» одной командой                      | inline-regex + dimensions                 |
| **jq \| sort \| uniq -c** | агрегат по полю JSONL                                            | `jsonl_events`                            |
| **yq / kubectl get**| инвентарь K8s-манифестов в файлах чарта                               | `k8s_resources`                           |
| **swagger-cli**     | инвентарь endpoints в OpenAPI/Swagger                                 | `openapi_endpoints`                       |
| **git log --stat \| awk** | активность авторов по месяцам с added/removed                    | `git_log_activity`                        |
| **git diff --stat \| wc** | размер MR/PR по каталогам и языкам                               | `mr_impact --files-from -`                |
| **ctags + grep**    | быстрый инвентарь символов кода (без AST-точности)                    | `code_atlas`                              |
| **rga / grep --include** | код-поиск с фильтром по типу файла и агрегатом                   | inline + `content_match`                  |
| **allure/junit-xml summary** | rollup по suite × status × avg duration                       | inline regex по XML                       |
| **awk histogram**   | histogram, percentile, распределение метрик из логов                  | `p50/p90/p95/p99` measure                 |
| **treemap.py / sqlite-utils** | визуализация иерархии                                       | `format: echarts` (treemap/sunburst)      |
| **graphviz-ast**    | approximate call-graph → SVG/PNG                                      | `call_graph` + `format: dot`              |

Плюс — три преимущества, которые дают drop-in-replacement:

- **Один Python-файл**, ставится в контейнер за 1 команду, не тянет
  ni tree-sitter, ни SQLite, ни LSP;
- **Единый формат конфига** (yaml/JSON profile) для всех задач — вместо
  запоминания флагов 15 разных утилит;
- **Автоматически подходит агентам** — machine-readable выход в JSON/CSV/
  YAML/DOT для tool-цепочек.

## Классические cookbook-задачи: было → стало

Один и тот же результат, разное количество тыкания.

### 1. LOC-каунт по языкам в репозитории

**Было** (`scc` не установлен, `cloc` тоже):
```bash
find . -name "*.py" -not -path "./venv/*" | xargs wc -l | tail -1
find . -name "*.js" -not -path "./node_modules/*" | xargs wc -l | tail -1
find . -name "*.go" -not -path "./vendor/*"        | xargs wc -l | tail -1
# ...повторить для каждого языка
```

**Стало:**
```bash
python .claude/skills/cubest/cubest.py --profile loc_counter .
```

Выводит:
```
py>src        12503  lines=12503, blanks=1240.0, comments=812.0, bytes=421.3KiB
ts>web        8942   lines=8942,  blanks=1105.0, comments=610.0, bytes=298.1KiB
go>cmd        3210   lines=3210,  blanks=298.0,  comments=140.0, bytes=112.6KiB
...
```

### 2. Топ URL по количеству 5xx-ошибок за сутки из nginx-логов

**Было:**
```bash
zcat access.log.gz | awk '$9 ~ /^5/' | awk '{print $7}' | sort | uniq -c | sort -rn | head -20
```

**Стало:**
```bash
python .claude/skills/cubest/cubest.py -p '{
  "dimensions":["path_root","status"],
  "measures":[{"name":"hits","type":"count"}],
  "extract":[{"type":"regex","pattern":"\"(?P<method>GET|POST|PUT|DELETE) /(?P<path_root>[^/? ]+)[^ ]* HTTP/[\\\\d.]+\" (?P<status>5\\\\d\\\\d)"}],
  "output":{"format":"flat","top_n":20}
}' access.log.gz
```

Дополнительно получаем: gzip-стриминг из коробки, sub-percentile-latency
через `p95/p99`, ECharts-визуализацию с `format: echarts`.

### 3. Disk-usage до 2-й глубины директорий

**Было:**
```bash
du -sh */ | sort -rh | head -20               # только 1 уровень
du -h --max-depth=2 . | sort -rh | head -20   # шумно, много служебки
```

**Стало:**
```bash
python .claude/skills/cubest/cubest.py --profile disk_usage .
```

Выводит с человеческими размерами + счёт файлов + max_file per каталог.

### 4. Все TODO/FIXME в проекте с группировкой

**Было:**
```bash
grep -rn --include='*.py' --include='*.js' -E 'TODO|FIXME|HACK' . | wc -l
grep -rn --include='*.py' 'TODO' . | awk -F: '{print $1}' | sort | uniq -c | sort -rn | head
```

**Стало:**
```bash
python .claude/skills/cubest/cubest.py --profile tech_debt .
```

### 5. Активность коммиттеров за 6 месяцев

**Было:**
```bash
git log --format='%an' --since=6.months | sort | uniq -c | sort -rn
git log --numstat --format='COMMIT|%an' --since=6.months | \
  awk '/^COMMIT/{a=$2}/^[0-9]/{c[a]+=$1+$2}END{for(k in c)print c[k],k}' | sort -rn
```

**Стало:**
```bash
git log --numstat --format='COMMIT|%an|%ai' --since=6.months > /tmp/gitlog.txt
python .claude/skills/cubest/cubest.py --profile git_log_activity /tmp/gitlog.txt
```

Готовая MD-таблица `author × month → commits, added, removed`.

### 6. Percentile латентности из access-log

**Было:**
```bash
# для этого обычно ставят GoAccess или пишут awk-скрипт
zcat access.log.gz | awk '{print $NF}' | sort -n | \
  awk 'BEGIN{c=0}{arr[c++]=$1}END{print arr[int(c*0.95)]}'
# и это ест всю память, потому что sort -n
```

**Стало:**
```bash
python .claude/skills/cubest/cubest.py -p '{
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

Reservoir sampling → **O(k) память** независимо от размера файла.

### 7. Inventory K8s-манифестов в helm-chart

**Было:**
```bash
find . -name '*.yaml' -exec grep -l '^apiVersion:' {} \; | \
  xargs -I {} yq eval '.kind + " " + .metadata.namespace + " " + .metadata.name' {} | \
  sort | uniq -c
```

**Стало:**
```bash
python .claude/skills/cubest/cubest.py --profile k8s_resources ./chart/
```

### 8. Approximate call-graph в SVG

**Было:**
```bash
# либо большой pyan / snakefood / pyreverse setup
# либо ручной grep + Graphviz-разметка
pyan3 src/*.py --uses --colored --grouped --annotated --dot | dot -Tsvg > graph.svg
```

**Стало:**
```bash
python .claude/skills/cubest/cubest.py --profile call_graph src/ | dot -Tsvg > graph.svg
```

Или сразу интерактивный HTML:
```bash
python .claude/skills/cubest/cubest.py --profile call_graph src/ \
  -p '{"output":{"format":"echarts","chart_type":"graph"}}' > graph.html
```

### 9. Отчёт по MR/PR без клонирования локально

**Было:**
```bash
# либо custom CI-скрипт на bash с find/xargs/awk
# либо тяжёлый инструмент вроде Danger.js
```

**Стало (в 2 строки в GitHub Actions):**
```bash
git diff --name-only origin/main...HEAD | \
  python .claude/skills/cubest/cubest.py -F - --profile mr_impact . \
    -p '{"output":{"format":"md_table"}}' > /tmp/impact.md
gh pr comment ${{ github.event.number }} --body-file /tmp/impact.md
```

### 10. SEO: семантическое дерево и аудит сайта

Три преcета для работы с HTML/XML сайтов без внешних SEO-краулеров:

- **`html_meta`** — один record на страницу с полями `title`, `title_len`,
  `description`, `desc_len`, `keywords`, `canonical`, `robots`,
  `og_title`, `og_description`, `twitter_card`, `lang`, `h1_count`,
  `h1_first`, `h2_count`, `h3_count`, `has_schema` (JSON-LD).
- **`html_headings`** — один record на каждый heading: `level` (1-6),
  `title`. Даёт семантическое дерево страницы.
- **`sitemap`** — один record на `<url>` из sitemap.xml: `url`, `path`,
  `host`, `priority`, `lastmod`, `changefreq`, `depth`, `section_1`,
  `section_2`, `section_3` (первые 3 сегмента URL).

Готовые профили:

```bash
# 1) Общий SEO-аудит: длины title/description, дубли, наличие schema
python .claude/skills/cubest/cubest.py --profile seo_audit ./crawl/
# → md_table: pages | title_avg | title_max | desc_avg | h1_total | schema_pages

# 2) Семантическое дерево: file × level × title как interactive sunburst
python .claude/skills/cubest/cubest.py --profile seo_semantic_tree ./crawl/ > tree.html

# 3) URL-таксономия из sitemap.xml как treemap
python .claude/skills/cubest/cubest.py --profile sitemap_map sitemap.xml > urls.html
```

**Как раньше** делали то же самое:
```bash
# Screaming Frog GUI, лицензия $259/год; либо
# сmartupdate + jq для каждой страницы; либо
# python + BeautifulSoup + lxml + custom-скрипт
```

**Как теперь** — 3 команды на терминале, готовый ECharts HTML для команды.

Прицельные вопросы, на которые отвечают эти профили:

- «Какие страницы без H1?» → `filters: ["h1_count == 0"]` в `seo_audit`
- «Где title > 60 символов?» → `filters: ["title_len > 60"]`
- «Где отсутствует canonical?» → `filters: ["canonical == ''"]`
- «Какой раздел сайта самый крупный?» → `sitemap_map` treemap
- «Дубликаты title через страницы» → `dimensions: [title]` + count > 1
- «Страницы без JSON-LD schema» → `filters: ["has_schema == 0"]`

Inline-пример «топ H1-заголовков сайта» под ключевые слова:

```bash
python .claude/skills/cubest/cubest.py -p '{
  "dimensions": ["title"],
  "measures": [{"name":"pages","type":"count"}],
  "extract": [{"type":"preset","preset":"html_headings"}],
  "filters": ["level == 1"],
  "output": {"format":"md_table","top_n":30}
}' ./crawl/ >> KEYWORD_AUDIT.md
```

Комбинируется с `content_match` для фильтра по content-nature: «H1 только
на страницах, где встречается upgrade-CTA» и т.п.

### 11. CSV/TSV на входе → OLAP-агрегат → ECharts HTML

Native CSV/TSV-парсер stdlib с header row: имена колонок автоматически
нормализуются (`Campaign Name` → `campaign_name`), становятся полями
record'а. Дальше — обычные dimensions/measures + любой формат вывода,
включая интерактивный ECharts HTML.

```bash
# GA4/AdWords/Metrica/Facebook Ads CSV → готовая диаграмма
python .claude/skills/cubest/cubest.py --profile csv_analytics \
  ~/downloads/ads_report.csv > /tmp/ads.html
open /tmp/ads.html  # интерактивный sankey/treemap/bar в браузере
```

Свой профиль под конкретный CSV-экспорт — inline JSON, без создания файла:

```bash
python .claude/skills/cubest/cubest.py -p '{
  "dimensions": ["campaign", "device"],
  "measures": [
    {"name":"impressions","type":"sum","field":"impressions"},
    {"name":"clicks","type":"sum","field":"clicks"},
    {"name":"cpm","type":"avg","field":"cost"},
    {"name":"cost_p95","type":"p95","field":"cost"}
  ],
  "extract": [{"type":"preset","preset":"csv"}],
  "output": {"format":"echarts","chart_type":"sankey","title":"Campaign → Device"}
}' /path/to/report.csv > /tmp/report.html
```

Опции preset:

| Опция       | Что делает                                                          |
|-------------|---------------------------------------------------------------------|
| `sep`       | Разделитель: `","` для csv (default), `"\t"` для tsv, `";"` для EU CSV |
| `header`    | `true` (default), `false` (использует `col_0..col_N`) или явный список имён |
| `skip`      | Сколько строк выкинуть перед header (GA4 иногда пишет метаданные)   |
| `quotechar` | Символ кавычек, default `"`                                          |

Тот же CSV можно выдать в разных форматах — `md_table` для PR, `csv` для
пайпа в дальнейшую обработку, `json` для программного потребления,
`mermaid` для встраивания в GitHub markdown:

```bash
python cubest.py -p '{"dimensions":["campaign"],"extract":[{"type":"preset","preset":"csv"}],"measures":[{"name":"impressions","type":"sum","field":"impressions"}],"output":{"format":"md_table"}}' report.csv >> PR_DESCRIPTION.md
```

### 12. Frontend/CDN log с GeoIP: мобильный Chrome из US/CA по /pub/covers/*

Задача: посчитать нагрузку по расширениям картинок (webp/jpg/png/avif) с
метриками `hits`, `p90(duration)`, `avg(size)`, отфильтровав по стране
(US/CA), UA (Mobile Chrome), эндпоинту (`/pub/covers/*`) и статусу 200.

**Как раньше** (набор шагов на awk/sort/uniq):
```bash
zcat access.log.gz \
  | awk '$9==200 && $7 ~ /^\/pub\/covers\// { print $1, $7, $10, $NF }' \
  | while read ip url dur bytes; do
      cc=$(geoiplookup "$ip" | awk -F: '{print $2}' | awk '{print $1}')
      # ... тут ещё нужен ручной extract UA, ext, дальше sort/awk по ext
    done | ...
```
и это без p90 (для перцентиля обычно нужен GoAccess или отдельный скрипт).

**Как теперь**:

Шаг 1 — предпочтительно, добавляем GeoIP в log_format nginx (см.
`tools/geoip_enrich.sh` для полного примера конфига):
```nginx
load_module modules/ngx_http_geoip2_module.so;
http {
  geoip2 /usr/share/GeoIP/GeoLite2-City.mmdb {
    $geoip2_country_code default=XX country iso_code;
    $geoip2_subdivision  default=XX subdivisions 0 iso_code;
  }
  log_format main_geoip
    '$remote_addr - $remote_user [$time_local] '
    '"$request" $status $body_bytes_sent '
    '"$http_referer" "$http_user_agent" $request_time '
    '$geoip2_country_code $geoip2_subdivision';
  access_log /var/log/nginx/access.log main_geoip;
}
```

Если тронуть nginx нельзя — fallback через bash-скрипт (медленнее в 20-100
раз, но работает на архивных логах):
```bash
zcat access.log.gz | tools/geoip_enrich.sh > enriched.log
```

Шаг 2 — один запуск cubest:
```bash
python .claude/skills/cubest/cubest.py \
  --profile frontend_geoip enriched.log.gz
```

Профиль встроен и делает всё разом:
- **regex-парсер** вынимает `ip, datetime, method, path, status, bytes,
  ua, duration, country, region, ext`
- **filters** оставляют только `status==200`, `country in {US, CA}`,
  `Mobile in ua and Chrome in ua`, `ext in {webp, jpg, png, avif, gif}`
- **dimensions=[ext]**, measures: `hits`, `p50_ms`, `p90_ms`, `p99_ms`,
  `avg_size`, `bytes_total`
- **output** — интерактивный ECharts HTML с bar-графиком (можно
  переключить на treemap/pie в UI), либо flat/csv/md_table для CI

Пример вывода `format: flat`:
```
webp  128432  hits=128432, p50_ms=0.041, p90_ms=0.180, p99_ms=0.520, avg_size=18234.2, bytes_total=2.2GiB
jpg    54210  hits=54210,  p50_ms=0.055, p90_ms=0.240, p99_ms=0.780, avg_size=32188.4, bytes_total=1.6GiB
avif    3212  hits=3212,   p50_ms=0.038, p90_ms=0.150, p99_ms=0.410, avg_size=9420.1,  bytes_total=28.9MiB
```

Быстрое расширение: добавить второе измерение (`dimensions: [country, ext]`)
или сгруппировать по региону штата/провинции (`dimensions: [country, region, ext]`).
Всё в том же профиле, изменение одной строки — не переписывая regex/фильтры.

### 13. Быстрый LOC на изменённых файлах MR

**Было:** отдельная утилита + фильтр.
**Стало:**
```bash
git diff --name-only origin/main...HEAD | \
  python .claude/skills/cubest/cubest.py -F - --profile loc_counter .
```

## Использование в MR/PR-хуках

Флаг `--files-from -` принимает список путей из stdin (обычно от `git
diff --name-only`):

```bash
# Что затрагивает этот MR — карта каталогов и языков
git diff --name-only origin/main...HEAD | \
  python .claude/skills/cubest/cubest.py -F - --profile mr_impact .

# Быстрый LOC-каунт только по изменённым файлам
git diff --name-only origin/main...HEAD | \
  python .claude/skills/cubest/cubest.py -F - --profile loc_counter .

# Не пропустили ли TODO в изменённых файлах?
git diff --name-only origin/main...HEAD | \
  python .claude/skills/cubest/cubest.py -F - --profile tech_debt .

# Активность за 6 месяцев в MD-таблицу для PR/статуса
git log --numstat --format='COMMIT|%an|%ai' --since=6.months > /tmp/gitlog.txt
python .claude/skills/cubest/cubest.py --profile git_log_activity /tmp/gitlog.txt
```

Интеграция в GitLab CI / GitHub Actions: в 3 строки — прогнать профиль,
сохранить `format: md_table` вывод, запостить в комментарий MR через `gh
pr comment` / `glab mr note`.

## Латентность и SRE-метрики: percentile из коробки

Меры `p50`, `p90`, `p95`, `p99`, `percentile` (с параметром `q: 0.75`)
считаются через **reservoir sampling** (Vitter Algorithm R). Память —
O(k) на leaf-узел (default k=128 семплов = ~1 KB), независимо от объёма
входных данных. Точность ~5% для p95 при 1000+ observations; для точных
квантилей используй t-digest / HDR-hist.

```yaml
measures:
  - {name: dur_p50, type: p50, field: duration}
  - {name: dur_p95, type: p95, field: duration}
  - {name: dur_p99, type: p99, field: duration, sample_size: 512}
  - {name: dur_p75, type: percentile, field: duration, q: 0.75}
```

## Когда применять (агностично)

Общее правило: **есть большой набор строчно-структурированных данных, и
нужен агрегат / карта, а не сами строки.**

### 1. Код и репозитории

- Карта дерева: расширения × топ-каталоги, размер, глубина.
- Инвентаризация: сколько функций/классов на файл, распределение по модулям.
- API-инвентарь: все HTTP-роуты по методу и файлу (FastAPI/Flask/Django,
  Express, Spring MVC — regex по декоратору).
- Технический долг: TODO/FIXME/HACK по типам и локациям.
- React/Vue-компоненты, страницы Next.js, exported symbols.
- Оглавление markdown-документации (заголовки × уровень × файл).
- Импорты: карта зависимостей по модулям.

Хорошее место в цикле: **первый шаг onboarding'а в незнакомый монорепо** —
дать LLM 30-строчную карту вместо 3000 строк листингов.

### 2. Логи веб-серверов и приложений

- **nginx / apache / envoy access-log**: URL-раздел × статус × метод
  с avg(request_time), sum(bytes), max(request_time). Работает прямо с
  `.log.gz`, потоково, без распаковки на диск.
- **CDN-логи** (Cloudflare/Fastly/CloudFront TSV): формат-файла × размер ×
  устройство × регион с avg upstream_response_time — прямой аналог
  perl-скриптов, использующих OLAP-модуль (`cdn_stat.pl`, `cdn_stat_litresFE.pl`).
- **Application logs** (JSON, syslog): уровень × сервис × endpoint,
  распределение ошибок за окно времени.
- **Kubernetes / Docker**: pod × container × log-level, top причины падений.
- **Access reviews**: user × action × resource из audit-log.

### 3. Реклама и веб-аналитика (табличные экспорты)

- **Google Analytics 4 / Universal Analytics export CSV**: source/medium ×
  device с sum(sessions), sum(revenue).
- **Google Ads / AdWords Report** (CSV): campaign × ad_group × device с
  sum(impressions/clicks/cost), avg(ctr).
- **Yandex Metrica logs API export** (TSV): visit-page × utm_source ×
  browser, распределение конверсий.
- **Yandex Direct reports**: keyword × placement × device.
- **Facebook/Meta Ads insights CSV**: campaign × placement × age×gender.
- **TikTok Ads / VK Ads export**: creative × audience.

Ключевой сценарий: **быстро свести отчёт до 30–100 строк**, вместо
загрузки полного CSV на десятки тысяч строк в контекст.

### 4. Колоночные БД и озёра данных (через экспорт)

Сам по себе cubest — не БД. Но идеально комбинируется с колонками:

- **ClickHouse**: `SELECT ... FORMAT TSV` (или `JSONEachRow`) → пайпом в
  `cubest --profile - -` — вторичная агрегация локально, без нагрузки
  на кластер, с фильтрами и rollup за секунды.
- **DuckDB / SQLite**: `duckdb -c "COPY ... TO STDOUT (FORMAT CSV)"` →
  cubest для быстрого exploratory-среза без лишних join'ов.
- **AWS Athena / BigQuery / Snowflake**: экспортированный CSV/Parquet →
  parquet-tools → CSV → cubest.
- **Kafka dump** (jsonl): event × source × schema-версия.
- **Prometheus / VictoriaMetrics** экспорт: метрика × label-set.
- **Elasticsearch scroll dump** (jsonl): index × source_type × severity.

Логика: колоночная БД возвращает уже подготовленные строки, cubest
делает финальный OLAP-cut и печатает в token-эффективном виде.

### 5. Файловые архивы, бэкапы, каталоги

- Инвентаризация огромного диска: тип × top-каталог × размер (`file_tree`).
- Аудит бэкапов: расширение × возраст файла × размер.
- Обзор клиентских выгрузок: сколько файлов какого типа пришло.
- Дедуп: distinct(basename) с count по каталогам.

### 6. Диагностика CI/CD и test reports

- Junit/Allure XML dump: suite × test × status с avg(duration).
- Build-логи: stage × status × длительность.
- Coverage-отчёт: файл × процент × количество непокрытых строк.

### 7. SDD-артефакты и generated-by-methodology коллекции

Когда любая методология (SDD, ADR-first, PRD-driven, RFC-workflow, Design Doc
templates) выпускает файлы по стандартному шаблону с YAML-фронтматтером и
чеклистами, cubest за один запуск сводит весь этот корпус в дашборд.

- **SDD spec catalog** (профиль `spec_status`): `type × status × phase × owner`
  сводится в md-таблицу — видно, сколько спек в draft/approved/deprecated,
  где висят «сироты» без владельца.
- **Каталог агентов** (`agents_inventory`): распределение сабагентов по модели
  (haiku/sonnet/opus), длина description'ов, наличие обязательных полей.
- **Каталог скиллов** (`skills_inventory`): обзор `**/SKILL.md` — фронтматтер
  каждого скилла + top-каталог.
- **Прогресс приёмки** (`sdd_checklist`): пересчёт `- [x]` vs `- [ ]` в
  чеклистах Phase Gates / capability-preflight. Одна строка = один файл =
  «сколько закрыто из скольких».
- **ADR/RFC/Design-Doc lifecycle**: те же frontmatter-поля (`status`,
  `decision`, `supersedes`) → срез по актуальности.
- **Any templated-artefact rollup**: у любой методологии, где артефакты имеют
  общую голову с полями (`sdd-applicability.md`, `capability-profiles.yaml`,
  `artefacts-manifest.yaml`), — тот же паттерн `md_frontmatter` даст
  инвентарь без чтения тел файлов.

Идея: если ты **сам генерируешь** файлы по методологии, добавь пару полей во
frontmatter (`status`, `phase`, `owner`) — и получишь готовый дашборд одним
запуском cubest.

### 8. XML / YAML / structured configs

Скилл читает эти форматы «из коробки» через regex-пресеты — YAML/JSON парсеры
не нужны, если задача сводится к инвентарю ключей или тегов:

- **XML/HTML/SVG/POM/AndroidManifest/OPML/RSS/Atom** (`xml_tags`) — топ-теги
  по документу и файлу. Работает на любом XML-диалекте, потому что это
  regex по `<tag>`.
- **YAML/JSON top-level keys** (`yaml_keys`) — `key × file`. Хорошо для
  быстрого «что вообще есть в этой куче конфигов»: k8s-манифесты, docker-
  compose, GitHub Actions, GitLab CI, Ansible playbooks, Terraform *.yaml.
- **Kubernetes** (`k8s_resources`) — `kind × namespace × name` по helm-chart
  или kustomize-дереву; content_match отсеивает не-манифестные YAML.
- **OpenAPI / Swagger** (`openapi_endpoints`) — `method × path`, работает
  и на YAML, и на JSON-спеках.
- **Docker-compose services** — быстро через inline-профиль:
  ```yaml
  extract: [{type: regex, multiline: true, pattern: '^\s{2}(?P<service>[\w-]+):\s*\n\s+image:\s*(?P<image>\S+)'}]
  dimensions: [service, image]
  ```
- **GitHub Actions workflows** — распределение `uses:` action'ов, matrix-
  комбинации; тем же inline-регексом.
- **Terraform** — `resource "kind" "name" {` через regex.
- **Ansible** — модули по вхождению `- name:` / `<module_name>:`.
- **XLIFF/PO/TS** (переводы) — теги `<trans-unit>` для аудита локалей.
- **CSV/TSV с шапкой** — inline-профиль с регексом по колонкам.

Идея: если формат текстовый и структурированный, дальше вопрос двух
сроок regex. Полный YAML-парсинг с nested keys — вне scope (нужен yq/jq);
cubest закрывает 80% inventory-задач.

### 9. Автодокументация кода и топ-язык

Профиль `code_atlas` строит карту символов на 15 языках (`.py .js .ts .jsx
.tsx .go .rs .java .rb .php .kt .swift .c .cpp .sh`). Для Python определяет
вложенность через indent-stack — в каждом record есть `parent` и `depth`,
можно строить дерево `file → class → method → nested_function`. Для
остальных языков — плоский список символов.

- `code_atlas` — атлас функций и классов по языку × файлу × родителю.
- `sql_functions` — все функции в файлах, где есть raw SQL (SELECT/INSERT/
  UPDATE/DELETE/CREATE TABLE/WITH). Использует `content_match` для
  префильтра, чтобы не парсить все файлы репо, а только те, где SQL.
- Комбинация с `content_match` даёт быстрый ответ на «какие функции
  трогают Redis», «какие модули используют pandas», «в каких сервисах
  есть отсылки к legacy-таблице `t_users`».

### 10. Call-graph и рекурсивные проходы + GraphViz

Скилл может вывести граф вызовов в формате GraphViz DOT: пресет `calls`
эмитит пары `(caller, callee)`, формат `dot` собирает `digraph`. Точность
эвристическая (indent-stack + `\bname\(` — без AST), для 100% AST-точности
используй tree-sitter-based инструменты типа Graphify. Но для быстрого
скетча «кто кого зовёт в этом модуле» — один запуск и всё.

Готовый профиль:

```bash
python .claude/skills/cubest/cubest.py --profile call_graph src/ \
  > /tmp/calls.dot
dot -Tsvg /tmp/calls.dot > /tmp/calls.svg
```

#### Рекомендация агенту: как собрать полный граф за 2–3 запуска

Когда одного прохода мало (например, `callee` определён в другом модуле,
и агенту нужно достроить недостающие ноды), используй такой рецепт:

1. **Собрать рёбра** по модулям — можно параллельно:
   ```bash
   for M in src/api src/core src/util; do
     python .claude/skills/cubest/cubest.py -p '{
       "dimensions":["caller","callee"],
       "extract":[{"type":"preset","preset":"calls"}],
       "filters":["caller != callee"],
       "output":{"format":"json"}
     }' "$M" > /tmp/edges_$(basename $M).json
   done
   ```

2. **Собрать все определённые символы** (чтобы автодоставить ноды-листья,
   которые никто не вызывает, но которые важно показать):
   ```bash
   python .claude/skills/cubest/cubest.py -p '{
     "dimensions":["name"],
     "extract":[{"type":"preset","preset":"funcs"}],
     "output":{"format":"json"}
   }' src/ > /tmp/defs.json
   ```

3. **Слить в один DOT** с автоподключением нод, подсветкой хабов и
   sink'ов:
   ```bash
   python .claude/skills/cubest/tools/callgraph_merge.py \
     --calls /tmp/edges_*.json \
     --defs  /tmp/defs.json \
     --out   /tmp/callgraph.dot
   dot -Tsvg /tmp/callgraph.dot > /tmp/callgraph.svg
   ```

Merger сам:

- объединяет веса рёбер (сколько раз функция A зовёт B);
- декларирует **все** узлы, включая те, которые пришли только из `--defs`
  (уединённые функции не теряются);
- красит **хабы** (топ по in+out degree) жёлтым, **entrypoints** (только
  исходящие) синим, **sinks** (только входящие) зелёным.

Рекурсивное разрастание графа за N шагов реализуется в цикле: сохранил
DOT → распарсил ноды с out-degree=0 → запустил cubest на других модулях
с `content_match: ["\\bНАЗВАНИЕ\\("]` → домержил рёбра. Скилл при этом
сам ничего не помнит, но за счёт единого JSON-выхода легко компонуется в
пайплайн любой глубины.

### 11. Уборка диска / disk-usage аудит

Профиль `disk_usage` использует `paths`-preset + `path_1..path_5` для
агрегации по N-й глубине директорий с `sum(size)` и `count(files)`:

```bash
# «Что жрёт место на диске в /mnt/drive до глубины 2?»
python .claude/skills/cubest/cubest.py --profile disk_usage /mnt/drive

# только те подкаталоги, где есть файлы, содержащие TODO
python .claude/skills/cubest/cubest.py -p '{
  "dimensions":["path_1","path_2"],
  "measures":[{"name":"files","type":"count"},{"name":"bytes","type":"sum","field":"size"}],
  "extract":[{"type":"preset","preset":"paths"}],
  "scan":{"content_match":["TODO"],"content_scan_bytes":65536},
  "output":{"format":"flat","human_bytes":true,"top_n":15}
}' /mnt/drive
```

Комбинация `content_match` + `paths` позволяет отвечать на нетривиальные
вопросы: «сколько места занимают старые кампании» (регекс по маркеру
устаревания в файле), «где хранятся notebook'и с BigQuery-запросами»
(regex по SQL-паттерну), «в каких папках дампы содержат кириллицу».

## Когда **не** применять

- Одиночный поиск в конкретном файле → `Grep`/`Read`.
- Нужен исходный текст строки, не агрегат → `Grep`.
- Данных < 100 строк / <10 файлов → быстрее прочитать напрямую.
- Требуется семантический граф зависимостей между функциями/файлами (кто
  что вызывает, blast radius) → это задача **Graphify** / code-review-graph /
  ast-grep, не cubest.

## Сравнение с Graphify и другими инструментами

| Аспект                    | cubest                                | Graphify                                       | grep -c / awk                    |
|---------------------------|-----------------------------------------|------------------------------------------------|----------------------------------|
| Тип                       | Aggregator (OLAP-cube)                  | Knowledge graph (AST + LLM)                    | Простой счётчик                  |
| Backend                   | regex + presets                         | tree-sitter (20 языков) + LLM inference        | regex                            |
| LLM требуется             | нет                                     | да, для inferred edges и multimodal            | нет                              |
| Персистентность           | stateless                               | graph.json на диске + PreToolUse-хуки          | stateless                        |
| Тип запросов              | «сколько чего где», группировка         | «какая функция вызывает что», blast radius     | сколько совпадений               |
| Логи / CSV / метрики      | подходит                                | нет (только код + docs + media)                | подходит для одного среза        |
| Многоуровневая аггрегация | да (иерархия dimensions)                | косвенно (обход графа)                         | нет                              |
| Multimodal (PDF/images)   | нет                                     | да (Claude Vision)                             | нет                              |
| Скорость                  | миллисекунды/файл, single-pass          | секунды/файл при первом проходе (LLM-инференс) | миллисекунды/файл                |
| Инсталляция               | один py-файл + `pyyaml`                 | пакет + tree-sitter grammars + LLM             | встроено в POSIX                 |
| Sweet spot                | быстрая карта, agg-срезы, потоки данных | глубокая семантика, cross-file навигация       | ad-hoc подсчёт в одном каталоге  |
| Экономия токенов          | тысячи → десятки строк за один запуск   | заявлено ×71.5 за счёт графа                   | зависит от запроса               |

**cubest и Graphify — не конкуренты**. Graphify отвечает на вопросы
типа «какие компоненты зависят от `AuthService.verify`?» — там нужен
семантический AST-граф. cubest отвечает на «сколько 5xx по эндпоинтам
за последний час», «какие 20 самых больших папок в бэкапе», «топ
кампаний по CTR из CSV» — для этого граф-БД избыточен, достаточно
regex + агрегата. Они хорошо комбинируются в одном проекте.

## Профили из коробки

| Профиль             | Что делает                                                    |
|---------------------|---------------------------------------------------------------|
| `file_tree`         | Дерево проекта: top-каталог × расширение, размер файлов       |
| `disk_usage`        | Аудит диска: `path_1 × path_2` → sum(size) + count(files)     |
| `code_stats`        | Функции/классы по файлам                                      |
| `api_routes`        | FastAPI/Flask/Django HTTP-эндпоинты                           |
| `tech_debt`         | TODO/FIXME/HACK по типу и файлу                               |
| `react_components`  | React/Vue-компоненты по типу декларации                       |
| `imports`           | Python-импорты по модулям                                     |
| `doc_structure`     | Заголовки Markdown ≤ h3                                       |
| `nginx_access`      | Combined access-log → URL-раздел × статус × метод             |
| `nginx_cdn_covers`  | CDN TSV-логи → size × format × device (порт cdn_stat.pl)      |
| `frontend_geoip`    | Frontend log + GeoIP: фильтр по стране/UA/эндпоинту → ext × p90 |
| `loc_counter`       | LOC-каунт по языкам (drop-in для scc/tokei/cloc)              |
| `mr_impact`         | Impact-map MR/PR по `git diff --name-only` через `-F -`        |
| `git_log_activity`  | Author × month активность из `git log --numstat`               |
| `seo_audit`         | SEO-аудит HTML-краула: title/desc/H1/canonical/schema (md-таблица) |
| `seo_semantic_tree` | Семантическое дерево заголовков H1-H6 → sunburst ECharts       |
| `sitemap_map`       | Инвентарь URL из sitemap.xml → treemap                         |
| `csv_analytics`     | GA4/AdWords/Metrica CSV → campaign × device                   |
| `jsonl_events`      | JSONL/NDJSON события → event × source                         |
| `sdd_specs`         | Каталог спек: `type × status × name` из md-фронтматтера       |
| `sdd_checklist`     | Прогресс чеклистов: done vs todo per file                     |
| `spec_status`       | SDD lifecycle: `phase × status × owner` → md-таблица          |
| `agents_inventory`  | Каталог Claude subagents (model × name)                       |
| `skills_inventory`  | Каталог Claude skills: `**/SKILL.md` из фронтматтера          |
| `code_atlas`        | Атлас функций/классов для 15 языков (parent+depth для Python) |
| `sql_functions`     | Функции в файлах с raw SQL                                    |
| `call_graph`        | Approximate call graph → DOT (для рендера в SVG/PNG)          |
| `xml_tags`          | XML/HTML/SVG/POM/AndroidManifest inventory                    |
| `yaml_keys`         | Top-level keys для YAML/JSON конфигов                         |
| `k8s_resources`     | Kubernetes manifests: kind × namespace × name                 |
| `openapi_endpoints` | OpenAPI/Swagger: method × path                                |

## Форматы вывода

Текстовые / табличные:

| Формат          | Когда выбирать                                        |
|-----------------|-------------------------------------------------------|
| `tree` (default)| Иерархия с отступами, читаемо человеку                |
| `flat`          | `a>b>c\tN` — компактно, ~30% меньше токенов чем tree  |
| `compact`       | `k: N` — только верхний уровень, сортировка по счёту  |
| `csv`           | Импорт в таблицу, парсинг, пайп                       |
| `md_table`      | Готовый отчёт в Markdown (для PR/Confluence/README)   |
| `yaml`          | Дальнейшая обработка YAML-инструментами               |
| `json`          | Полный дамп куба для программной обработки            |
| `xml`           | Общий XML-дамп куба (integration с XML-пайплайнами)   |

Диаграммы (требуют dimensions=[src, dst] или больше):

| Формат              | Что выдаёт                                                     |
|---------------------|----------------------------------------------------------------|
| `dot` / `graphviz`  | GraphViz DOT (`dot -Tsvg` → SVG/PDF)                           |
| `mermaid` / `mmd`   | Mermaid `flowchart LR` — рендерит GitHub, GitLab, Notion       |
| `plantuml` / `puml` | PlantUML `@startuml` component-диаграмма                       |
| `drawio` / `diagrams` | draw.io / diagrams.net XML (`File → Import` в приложении)    |
| `echarts` / `html`  | Интерактивный HTML с Apache ECharts (CDN, данные inline)       |

### ECharts HTML

`echarts` (`html`) выдаёт **один автономный HTML-файл**, который открывается
в браузере и работает без сети (после первой загрузки CDN echarts.min.js).
Все данные встроены inline. В хедере есть переключатель между 6 типами
диаграмм — cubest подбирает совместимые под форму данных автоматически,
несовместимые кнопки disabled:

| Тип       | Хорош для                                                              |
|-----------|------------------------------------------------------------------------|
| Sunburst  | Иерархии ≥3 dimensions (пример: `lang × file × parent × name`)         |
| Tree      | Глубокие иерархии с раскрытием узлов (call-tree, файловые деревья)     |
| Treemap   | Пропорции размеров (disk_usage, code_atlas, file_tree)                 |
| Sankey    | 2 dimensions как поток (API-роуты `method → path_root`, call_graph)    |
| Graph     | Force-directed граф связей (call_graph, dependency-graph)              |
| Bar       | Одномерный топ-N (`compact` в интерактиве)                             |

Autodetect (`chart_type: auto` — дефолт):

- 1 dim → **bar**
- 2 dims с малым fan-out → **treemap**, с большим → **sankey**
- ≥3 dims → **sunburst**, для очень глубоких (>4) → **tree**

Явный выбор через `output.chart_type`:

```yaml
output:
  format: echarts
  chart_type: sankey     # или sunburst | tree | treemap | graph | bar | auto
  top_n: 100
  min_count: 2
  title: "API traffic by section"
```

CDN зафиксирован на `echarts@5.5.1` (jsDelivr). HTML полностью standalone —
можно сохранить в артефакт CI, приложить к PR, открыть в браузере без
локального сервера.

## Установка

```bash
pip install -r requirements.txt          # с pip
uv pip install -r requirements.txt       # с uv
uv run --with pyyaml cubest.py -p file_tree .   # ad-hoc через uv без венва
```

Единственная опциональная зависимость — `PyYAML`. Только-JSON-профили работают
без неё, стандартной библиотеки Python 3.8+ достаточно.

## Быстрый старт

```bash
# карта репо (без чтения содержимого)
python .claude/skills/cubest/cubest.py --profile file_tree .

# nginx access-log прямо с .gz
python .claude/skills/cubest/cubest.py \
  --profile nginx_access /var/log/nginx/access.log.gz

# ClickHouse → cubest по пайпу
clickhouse-client -q "SELECT event, source, cnt FROM ... FORMAT TSV" > /tmp/e.tsv
python .claude/skills/cubest/cubest.py --profile jsonl_events /tmp/e.tsv

# Inline-профиль под свой формат
cat <<'EOF' | python .claude/skills/cubest/cubest.py --profile - ./data
dimensions: [dir, ext]
measures: [{name: files, type: count}, {name: bytes, type: sum, field: size}]
extract: [{type: preset, preset: paths}]
scan: {exclude: ["node_modules/", "*.tmp"]}
output: {format: flat, top_n: 20, human_bytes: true, max_lines: 40}
EOF
```

## Экономия токенов в выводе

- `output.format: flat` — breadcrumb-строки короче tree-иерархии на ~30%.
- `output.top_n: N` — оставить только N веток на каждом уровне.
- `output.min_count: N` — не показывать хвосты <N.
- `output.max_lines: N` — жёсткий cap с суффиксом `… (+K more)`.
- `output.max_depth: N` — обрезать глубину дерева.
- `output.human_bytes: true` — `2.1MiB` вместо `2202009.0`.
- `output.format: csv` — минимум «водянки», удобно для последующей вставки
  в таблицу или markdown.

## Тесты

```bash
python3 .claude/skills/cubest/tests/run_tests.py     # 38 unit-тестов
python3 .claude/skills/cubest/tests/bench.py         # быстрый нагрузочный
HEAVY=1 python3 .claude/skills/cubest/tests/bench.py # 5M records, 200k файлов
```

Unit-тесты (38 шт.) покрывают: pattern-matching, scan/prune, OLAP-rollup
(count/sum/avg/min/max), форматы (tree/flat/compact/csv/md_table/yaml/json),
`max_lines` cap, все presets (paths/funcs/headers/md_checklist/md_frontmatter),
stream-режим, gzip, `content_match`/`content_not`, filter-eval sandbox
(builtins-leak protection).

Bench-цели (light-mode на CPython 3.8):

| Сценарий                        | Метрика                                       |
|---------------------------------|-----------------------------------------------|
| Cube insert                     | ~200k записей/сек, RSS ~25 MiB на 500k        |
| Scan 10k мелких файлов          | ~14k файлов/сек (paths preset, без чтения)    |
| Streaming gzip access-log       | ~43k строк/сек, **ΔRSS <200 KiB на 500k**     |
| Format flat из 50k ячеек        | ~1 мс                                         |

Streaming держит константную память — так что 10 ТБ логов обрабатываются
за счёт I/O, а не памяти. `HEAVY=1` — 5 M записей / 200k файлов, требует
~30 с и ~500 MiB RSS.

## Похожие open-source проекты (для честности)

Проверка через GitHub search по нескольким комбинациям («OLAP cube +
CLI + Python + regex», «grep aggregator group-by», «"group-by" regex log
aggregator CLI») дала **0 репозиториев прямых аналогов**. Есть частичные
пересечения:

| Проект                                                                 | Стек   | Что делает                                            | Чего нет из cubest                             |
|------------------------------------------------------------------------|--------|-------------------------------------------------------|--------------------------------------------------|
| [rholder/grepby](https://github.com/rholder/grepby)                    | Go     | group-by count для потока grep-совпадений             | нет OLAP-иерархии, форматов, пресетов, диаграмм  |
| [john-sterling/LogScraper](https://github.com/john-sterling/LogScraper) | Python | wrapper регексов + agg по named groups для логов      | только для логов, только count/sum, нет форматов |
| [KarnerTh/xogs](https://github.com/KarnerTh/xogs)                      | Go     | YAML-профили + regex для live-log-агрегации           | live-only, нет диаграмм, code/SDD-пресетов       |
| [ReagentX/Logria](https://github.com/ReagentX/Logria)                  | Rust   | live-log с filter/aggregate                           | TUI-фокус, не CLI-агрегатор для batch            |
| [sancau/sherlog](https://github.com/sancau/sherlog)                    | Python | worker в отдельном процессе, льёт в PostgreSQL        | не in-process OLAP, требует БД                   |
| [Wolfsrudel/dev-scc](https://github.com/boyter/scc)                    | Go     | быстрый LOC-каунтер                                    | только код, нет regex/logs/dimensions            |
| [xioTechnologies/tokei](https://github.com/XAMPPRocky/tokei)           | Rust   | быстрый LOC-каунтер                                    | только код                                       |
| [allinurl/goaccess](https://github.com/allinurl/goaccess)              | C      | web-log analyzer c HTML-отчётом                        | только nginx/apache, свой parser                 |
| [saulpw/visidata](https://github.com/saulpw/visidata)                  | Python | интерактивный TUI-explorer таблиц                     | TUI-only, не CLI-агрегатор для тс агентам        |
| [multiprocessio/dsq](https://github.com/multiprocessio/dsq)            | Go     | SQL-запросы по CSV/JSON/logs                          | SQL, а не regex; нет диаграмм из коробки         |

**Ниша cubest:** `single-pass OLAP-агрегатор для *любого* строчного
потока (не только логов, не только кода) + сразу-в-визуализацию`. Ни
одна из перечисленных утилит не совмещает regex/preset-based extraction,
многоуровневый OLAP (dimensions × measures × rollup), 12 форматов вывода
(включая ECharts/GraphViz/PlantUML/Mermaid/draw.io) и native-поддержку
LLM-агентных workflow (files-from, machine-readable JSON/YAML/CSV).

## Бизнес-эффекты (ориентиры)

Числа взяты из отраслевых benchmark'ов OLAP / AIOps / MTTR-снижения
(Forrester, Research Square, Rootly benchmark 2025, incident.io ROI
calc). Для cubest не заменяют полную AIOps-платформу, но покрывают
80% случаев «быстрого агрегата без клика по десятку дашбордов».

### 1. Расследование инцидентов и MTTR

- **Manual investigation** обычно съедает 60-80% MTTR в распределённых
  системах — engineer вручную коррелирует логи и метрики
- Auto-aggregate + готовые визуализации сокращают этот этап в разы:
  Forrester фиксирует **до 50% снижения MTTR** при добавлении
  observability + аналитического слоя, Rootly benchmark 2025 — до 70%
  на первом ответе
- Кейс BT Group: MTTR от 2 часов до 85 секунд (97%) — крайний, но
  показательный пример того, как быстрый агрегат вместо ручного
  раскопа меняет числа
- Nudgebee: снижение MTTR с 60 → 30 минут для mid-size enterprise даёт
  экономию **~$250k+/год** при downtime cost $10k/час

cubest вписывается в «первые 5 минут инцидента»: `nginx_access.gz` →
топ-20 endpoint'ов по 5xx + p95(duration) в одну команду, без spin-up
дашборда.

### 2. Post-mortem и документирование

- Manual post-mortem reconstruction: **60-90 min per incident**
  (Slack-архивы, дашборды, звонки)
- При 18 incident/month → 27 часов документарной археологии
- В $110/hr fully-loaded SRE: **~$35k/год** только на post-mortem
  writing (incident.io ROI calc)

cubest-профиль поверх нужных логов + `--format md_table` даёт готовый
таймлайн-фрагмент для post-mortem за минуту вместо часа.

### 3. LLM-агенты и стоимость токенов

Основной value для AI-агентных workflow:

- **Замена 20-40 read/grep tool-вызовов одним** — типичный onboarding-
  проход агента съедает 30-60k input tokens только на листинги; агрегат
  через cubest — 500-2000 tokens
- **На тысяче сессий в день** (SaaS с встроенным AI-помощником) это
  экономит десятки миллионов input tokens и переводит долгие сессии
  из «упирается в лимит контекста» в «делает больше за тот же бюджет»
- Стоимостной ориентир: при $3-15 per M input tokens (Claude Opus/Sonnet)
  и 50k → 1k токенов экономии на сессию — снижение стоимости AI-запроса
  на нужную операцию в **20-50 раз**

### 4. Экономия compute на data-warehouse

- OLAP-pre-aggregation в целом снижает runtime querying cost (ответы
  на BI-запросы уже свёрнуты) — общий industry-принцип
- Для cubest: локальный OLAP-cut над экспортом ClickHouse/DuckDB
  выполняется без нагрузки на кластер — экономия compute BigQuery/
  Snowflake/Athena за счёт того, что второй-третий срез делается
  на инженерной машине, а не в облаке ($0 vs $-per-TB-scanned)

### 5. Consolidation of tooling

- Отраслевой тренд 2026: **all-in-one incident tools** снижают tool
  sprawl (SigNoz/OpenObserve/Rootly comparisons)
- cubest закрывает 15+ утилит одной установкой: scc, tokei, cloc,
  GoAccess, jq-агрегаты, yq-инвентарь, pyan (call-graph), самописные
  awk-скрипты, Graphviz-обвязки, `du -sh` — всё через один YAML/JSON
  профиль

### 6. Developer productivity в PR-workflow

- PR-preflight автоматика (impact map, LOC-delta, TODO-статистика)
  снижает review latency (типовые данные: `-30% review turnaround` при
  готовых summary в PR-описании)
- Формат `md_table` → `gh pr comment` — интеграция в 2 строки

**Дисклеймер:** цифры выше — это индустриальные benchmark'ы для
observability/AIOps в целом, а не измеренный эффект от cubest.
Скилл — не replacement Datadog/New Relic; это lightweight-агрегатор,
который занимает нишу «между grep и BigQuery».

## Ограничения

- Regex-фильтры `filters:` выполняются через `eval` в изолированной песочнице
  (`__builtins__` — только `len/min/max/abs/int/float/str/bool/any/all/sum/sorted/round`).
  Не запускай chart profiles от недоверенных пользователей.
- Streaming не поддерживает `multiline: true` regex — сработает только по
  одной строке. Для мульти-line паттернов используй batch mode
  (файл <10 MiB и не `.gz`).
- Дефолтные `exclude` при переопределении **заменяются целиком** — добавляй
  нужные обратно.
- Overwrite поля `size` в extract: preset `paths` вычисляет через `os.stat`;
  если добавить своё `size` из regex, дублирования не будет — победит regex-
  правило, если оно применяется после `paths`.

## Источники (о Graphify)

- [Graphify — knowledge graph for AI coding assistants](https://graphify.com/)
- [Knowledge Graphs for Codebases: A Complete Guide to Graphify (Emelia)](https://emelia.io/hub/knowledge-graph-graphify-guide)
- [10 Best Graphify Alternatives (Knolli)](https://www.knolli.ai/post/graphify-alternatives)
- [Graphify + code-review-graph (dev.to)](https://dev.to/mir_mursalin_ankur/graphify-code-review-graph-build-a-self-updating-knowledge-graph-for-claude-code-and-other-ai-j1m)
