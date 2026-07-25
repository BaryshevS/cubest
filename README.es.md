# cubest

[English](README.md) · [简体中文](README.zh-CN.md) · **Español** · [हिन्दी](README.hi.md) · [العربية](README.ar.md) · [বাংলা](README.bn.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [日本語](README.ja.md) · [ਪੰਜਾਬੀ](README.pa.md)

> **7–22× menos tokens por escaneo de repositorio para agentes de IA.**
> Agregador OLAP de un solo paso que convierte cualquier flujo de texto
> (código, logs, CSV, JSONL, XML, HTML, artefactos SDD) en un cubo compacto.
> Diseñado para **Claude Code, Cursor, Codex, Aider, Windsurf, Cline,
> Continue.dev** y cualquier agente de IA que pague por token de entrada.

<p align="left">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.8%2B-blue.svg">
  <img src="https://img.shields.io/badge/deps-solo%20stdlib-green.svg">
  <img src="https://img.shields.io/badge/tests-57%20pasando-brightgreen.svg">
</p>

## 🧠 Por qué a un agente de IA le importa

Medido en 7 escenarios reales (ver [`examples/`](examples/)):

| # | Escenario                                | Tokens naive | Cubest tokens | Ratio     |
|---|------------------------------------------|:------------:|:-------------:|:---------:|
| 1 | Investigación 5xx en log nginx (5000 líneas) | 3.590      | 158           | **22.7×** |
| 2 | Onboarding a un repo (40 archivos)      | 1.256        | 175           | 7.2×      |
| 3 | Mapa de impacto de MR desde `git diff`  | 280          | 16            | **17.5×** |
| 4 | Rollup pequeño de CSV (300 filas)       | 280          | 368           | 0.8× ❌   |
| 5 | Auditoría SEO de 10 páginas HTML        | 382          | 49            | 7.8×      |
| 6 | Auditoría de uso de disco (300 archivos)| 338          | 68            | 5.0×      |
| 7 | Rollup de categorías RSS (3×30 items)   | 1.692        | 265           | 6.4×      |
|   | **Mediana**                             |              |               | **7.2×**  |

Cubest gana en **flujos grandes y datos jerárquicos**. Para tablas muy pequeñas
(CSV de 300 filas), una cadena `awk` ya es compacta y cubest incluso pierde.

## 🚀 Instalación

```bash
# Descarga simple (sin deps para perfiles JSON)
curl -O https://raw.githubusercontent.com/BaryshevS/cubest/main/cubest.py
python3 cubest.py --profile file_tree .

# Vía pip desde PyPI (PyYAML incluido)
pip install cubest
cubest --profile file_tree .

# Vía npm wrapper
npx cubest --profile file_tree .
```

## ⚡ Uso rápido

```bash
# Mapa de un repo desconocido (30 líneas en vez de 3000)
cubest --profile file_tree .

# Log nginx.gz — top URLs × status × latencia p95
cubest --profile nginx_access /var/log/nginx/access.log.gz

# Conteo de líneas de código por lenguaje
cubest --profile loc_counter .

# CSV → OLAP → dashboard ECharts interactivo (un solo HTML)
cubest -p '{
  "dimensions": ["campaign", "device"],
  "measures": [{"name":"impressions","type":"sum","field":"impressions"}],
  "extract": [{"type":"preset","preset":"csv"}],
  "output": {"format":"echarts","chart_type":"sankey"}
}' informe.csv > dashboard.html
```

## 📊 Formatos de salida

13 formatos: `tree`, `flat`, `compact`, `csv`, `md_table`, `yaml`, `json`,
`xml`, `dot`, `mermaid`, `plantuml`, `drawio`, `echarts`.

31 perfiles integrados — código, logs, CSV, SEO, K8s, OpenAPI, SDD.
Lista completa en el [README en inglés](README.md#-what-you-get).

## 📜 Licencia

Apache License 2.0 — ver [LICENSE](LICENSE) y [NOTICE](NOTICE).

**Requisito de atribución (Apache 2.0 §4d):** si redistribuye cubest,
debe incluir el archivo NOTICE preservando la URL upstream:

> https://github.com/BaryshevS/cubest

## 💖 Apoyo

Si cubest te ahorra tokens en tus flujos diarios con agentes o acorta
un incidente, considera patrocinar el proyecto — la financiación va
directamente al roadmap (t-digest, CSV en streaming, snippets para
agentes) y a la infraestructura:

- **GitHub Sponsors** → https://github.com/sponsors/BaryshevS
- **Open Collective** → https://opencollective.com/baryshevsv

Incluso 3 $/mes mantienen el proyecto en marcha. Los patrocinadores
tienen prioridad en la clasificación de issues y aparecen en las notas
de cada versión.

## ⭐ Dale una estrella

Si cubest te ahorra parte del presupuesto de IA o acorta un incidente
SRE por una hora, una estrella ayuda a otros a encontrarlo.

<a href="https://github.com/BaryshevS/cubest/stargazers">
  <img src="https://img.shields.io/github/stars/BaryshevS/cubest?style=social" alt="Star">
</a>
