---
name: cubest
description: >-
  USE WHEN нужно быстро получить структурированный срез большой кодовой базы
  или дерева файлов (роуты, TODO, компоненты, заголовки, структура каталогов)
  БЕЗ чтения всех файлов в контекст. Возвращает компактное OLAP-дерево или
  плоский список вместо десятков `cat`/`grep`. Экономит токены на длинных
  сессиях и больших циклах обработки.
  Триггеры: "покажи структуру", "сколько где", "найди все X по проекту",
  "map the codebase", "все endpoint'ы", "все TODO", "все компоненты",
  "оглавление md", "какие расширения", "куда сложены Y-файлы".
---

# cubest — Single-pass OLAP indexer

Сканирует каталог за один проход, извлекает записи регулярками/пресетами,
агрегирует в in-memory OLAP-куб и печатает компактное дерево. **Не тянет
исходники файлов в контекст Claude** — только агрегаты.

## Когда вызывать (экономия токенов)

Используй `cubest` **вместо**:

- цепочки `grep -rn` + `cat` по 20+ файлам, чтобы понять, где что лежит;
- ручного обхода `ls -R` + `wc -l` по большому дереву;
- открывания десятка файлов только чтобы «прикинуть, сколько там endpoint'ов /
  TODO / компонентов»;
- «загляну в каждый md, чтобы построить оглавление проекта».

Особенно уместен когда:

1. **Длинный цикл рефакторинга/аудита** и нужно удержать контекст — вместо
   чтения файлов держи в контексте компактный индекс.
2. **Незнакомый монорепо** — первым шагом строим `file_tree` + `code_stats`,
   получаем карту за один запуск.
3. **Периодическая сверка** («сколько сейчас TODO?», «какие новые роуты?») —
   вывод в 20–200 строк вместо тысяч строк `grep`.
4. **Планирование правок** — прежде чем начать, узнай распределение (сколько
   файлов затронуто, какие каталоги, какие расширения).

Когда **не** нужен:

- Одиночный поиск в конкретном файле — используй `Read` / `Grep`.
- Нужен исходник строк, а не агрегат — используй `Grep`/`Read`.
- Дерево <10 файлов — быстрее прочитать напрямую.

## Быстрый старт

```bash
# Дерево проекта: top-каталоги × расширения (без чтения содержимого)
python .claude/skills/cubest/cubest.py --profile file_tree .

# HTTP-эндпоинты FastAPI/Flask
python .claude/skills/cubest/cubest.py --profile api_routes ./src

# TODO/FIXME/HACK по типам и файлам
python .claude/skills/cubest/cubest.py --profile tech_debt .

# Оглавление md-документации
python .claude/skills/cubest/cubest.py --profile doc_structure ./docs
```

## Inline-профили

JSON одной строкой:

```bash
python .claude/skills/cubest/cubest.py \
  --profile '{"dimensions":["kind","file"],"measures":[{"name":"count","type":"count"}],"extract":[{"type":"preset","preset":"funcs"}],"scan":{"include":["*.py"]}}' \
  ./src
```

YAML через stdin:

```bash
cat <<'EOF' | python .claude/skills/cubest/cubest.py --profile - ./src
dimensions: [ext, file]
measures: [{name: count, type: count}]
extract: [{type: preset, preset: paths}]
output: {format: compact}
EOF
```

## Формат профиля

```yaml
name: my_profile              # optional
description: "..."            # optional
scan:
  include: ["*.py", "docs/**/*.md"]
  exclude: [".git/", "node_modules/", "*.lock", "!keep.lock"]
dimensions:                   # порядок = иерархия дерева
  - kind
  - file
measures:
  - name: count
    type: count
  - name: bytes
    type: sum
    field: size
extract:
  - type: preset
    preset: paths | funcs | headers | lines
  - type: regex
    pattern: '(?P<status>\d{3})\s+(?P<duration>[0-9.]+)'
    multiline: true
    ignorecase: false
filters:                      # безопасный eval с len/min/max/any/all
  - "status >= 200"
  - "'test' not in file.lower()"
output:
  format: tree | compact | json
  top_n: 15
  min_count: 2
```

## Пресеты (`type: preset`)

| Preset            | Что даёт (поля записи)                                       | Читает файл?    |
|-------------------|--------------------------------------------------------------|-----------------|
| `paths`           | `dir, basename, name, ext, depth, top, size, path_1..path_5` | нет             |
| `funcs`           | `kind` (def/class), `name`                                   | да              |
| `headers`         | `level`, `title` (Markdown)                                  | да              |
| `lines`           | `line`, `length`                                             | да              |
| `md_checklist`    | `state` (done/todo), `title`                                 | да (или stream) |
| `md_frontmatter`  | все `key: value` из YAML-фронтматтера (type, status, phase…) | да (batch)      |
| `csv` / `tsv`     | все колонки из header-строки CSV/TSV (нормализованные имена) | да (batch)      |
| `calls`           | пары `(caller, callee)` — approximate call-graph (Python)    | да              |

`paths` — один record на файл, работает даже для пустых файлов и бинарников;
идеален для «карты дерева» без чтения контента. Поля `path_1..path_5` — префиксы
директорий до N-й глубины (`path_2 = "src/api"`), удобны для disk-usage-агрегации.

`md_checklist` / `md_frontmatter` — для SDD-артефактов (спецификации, PRD, ADR,
чеклисты приёмки, каталоги скиллов/агентов).

## Фильтрация путей (`scan.include` / `scan.exclude`) — gitignore-like

Правила матчинга паттерна:

- `*.py`, `README.*` — glob по basename файла;
- `docs/**/*.md`, `src/*/api.py` — glob по относительному пути (`**` — любая
  глубина);
- `node_modules/`, `.git/`, `*cache*/` — **директория целиком**, пропускается на
  уровне обхода (быстро);
- `/README.md` — якорь к корню сканирования;
- `!pattern` — negation: сохранить, даже если совпало с exclude / отбросить,
  даже если совпало с include.

Дефолтные `exclude` (если не указано своё):
`.git/ node_modules/ __pycache__/ .venv/ venv/ dist/ build/ .claude/ *.lock *.pyc`.

При переопределении `exclude` в профиле дефолты **заменяются целиком** — не
забудь добавить нужные обратно.

## Типы мер

| Type   | Как считает                                    | Rollup                        |
|--------|------------------------------------------------|-------------------------------|
| `count`| +1 за каждую запись                            | сумма по детям                |
| `sum`  | +record[field] за каждую запись                | сумма по детям                |
| `avg`  | среднее record[field] по всем записям в листе  | weighted avg по count детей   |

## Форматы вывода

Текстовые: `tree` (default), `flat` (breadcrumb), `compact`, `csv`, `md_table`
(`md`/`markdown`), `yaml` (`yml`), `json`, `xml`.

Диаграммы (dimensions должны быть `[src, dst]` или больше):

- `dot` / `graphviz` — DOT-syntax, рендер через `dot -Tsvg`;
- `mermaid` / `mmd` — `flowchart LR`, рендерит GitHub/GitLab/Notion/Obsidian;
- `plantuml` / `puml` — `@startuml` component diagram;
- `drawio` / `diagrams` — draw.io / diagrams.net XML (`File → Import`);
- `echarts` / `html` — интерактивный standalone-HTML с 6 переключаемыми
  типами (sunburst / tree / treemap / sankey / graph / bar), CDN + inline-
  data. Тип выбирается через `output.chart_type: auto|sunburst|...`.

Пример: получить call-graph как Mermaid одной командой —
```
python .claude/skills/cubest/cubest.py -p call_graph src/ -p '{"output":{"format":"mermaid","top_n":30}}'
```
или отредактировать `output.format` в профиле `call_graph.yaml`.

## Фильтр по содержимому файлов

Помимо glob-фильтров пути можно требовать, чтобы файл содержал (или НЕ содержал)
конкретные regex — префильтр применяется до основной обработки:

```yaml
scan:
  content_match: ["TODO", "@deprecated"]   # файл должен содержать оба
  content_not:   ["generated by tool X"]   # и не должен содержать это
  content_scan_bytes: 65536                # проверять только первые 64 KiB
```

Полезно для disk-usage: «покажи размер только тех папок, где есть файлы с TODO».

## Флаги

```
--profile / -p   built-in имя | путь к файлу | inline JSON/YAML | '-' (stdin)
--verbose / -v   печатать "# Scanned N files" в stderr
path             корень сканирования (по умолчанию '.')
```

## Установка

Скрипт зависит только от опциональной PyYAML (для YAML-профилей/YAML-вывода).
JSON-профили работают без зависимостей.

```bash
pip install -r requirements.txt        # с pip
uv pip install -r requirements.txt     # с uv
uv run --with pyyaml cubest.py -p file_tree .   # ad-hoc через uv без венва
```

## Тесты

```bash
python3 .claude/skills/cubest/tests/run_tests.py     # 38 unit-тестов
python3 .claude/skills/cubest/tests/bench.py         # быстрый нагрузочный
HEAVY=1 python3 .claude/skills/cubest/tests/bench.py # тяжёлый: 5M records
```

Bench-цели: >100k rec/s на insert, streaming gzip держит **константную память**
(ΔRSS <200 KiB на 500k строк) — это то, что позволяет обрабатывать
терабайтные логи без OOM.

См. [README.md](README.md) для полного списка применений и сравнения с Graphify.
