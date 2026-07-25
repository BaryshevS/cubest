# cubest

[English](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md) · [বাংলা](README.bn.md) · **Português** · [Русский](README.ru.md) · [日本語](README.ja.md) · [ਪੰਜਾਬੀ](README.pa.md)

> **7–22× menos tokens por varredura de repositório para agentes de IA.**
> Agregador OLAP de passagem única que dobra qualquer fluxo de texto —
> código, logs, CSV, JSONL, XML, HTML, artefatos SDD — em um cubo
> multidimensional compacto. Projetado para **Claude Code, Cursor,
> Codex, Aider, Windsurf, Cline, Continue.dev** e qualquer agente de IA
> que cobre por token de entrada.

<p align="left">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.8%2B-blue.svg">
  <img src="https://img.shields.io/badge/deps-stdlib%20only-green.svg">
  <img src="https://img.shields.io/badge/tests-57%20passing-brightgreen.svg">
</p>

## 🧠 Por que um agente de IA deveria se importar

Medido em 7 cenários reais (veja [`examples/`](examples/)):

| # | Cenário                                       | Naive tokens | Cubest tokens | Razão     |
|---|-----------------------------------------------|:------------:|:-------------:|:---------:|
| 1 | Investigação de 5xx no log nginx (5000 linhas)| 3.590        | 158           | **22,7×** |
| 2 | Onboarding em um repositório (40 arquivos)    | 1.256        | 175           | 7,2×      |
| 3 | Mapa de impacto de MR a partir de `git diff`  | 280          | 16            | **17,5×** |
| 4 | Rollup pequeno de CSV (300 linhas)            | 280          | 368           | 0,8× ❌   |
| 5 | Auditoria SEO de 10 páginas HTML              | 382          | 49            | 7,8×      |
| 6 | Auditoria de uso de disco (300 arquivos)      | 338          | 68            | 5,0×      |
| 7 | Rollup de categorias RSS (3×30 itens)         | 1.692        | 265           | 6,4×      |
|   | **Mediana**                                   |              |               | **7,2×**  |

Cubest vence em **fluxos grandes e dados hierárquicos**. Para dados
tabulares muito pequenos (CSV de 300 linhas), um pipeline `awk` simples
já é compacto e cubest pode até perder. Nos cenários principais — logs,
árvores de código, crawls de sitemap — os tokens que caem no contexto
do agente diminuem entre 5–25×.

## 🚀 Instalação

```bash
# Download simples (sem deps para perfis JSON)
curl -O https://raw.githubusercontent.com/BaryshevS/cubest/main/cubest.py
python3 cubest.py --profile file_tree .

# Via pip (em breve no PyPI)
pip install cubest
cubest --profile file_tree .

# Via wrapper npm
npx cubest --profile file_tree .
```

## ⚡ Início rápido

```bash
# Mapa de um repositório desconhecido (30 linhas em vez de 3000)
cubest --profile file_tree .

# Log nginx.gz — top URLs × status × latência p95
cubest --profile nginx_access /var/log/nginx/access.log.gz

# Contagem de LOC por linguagem
cubest --profile loc_counter .

# CSV → OLAP → dashboard ECharts interativo (um único HTML)
cubest -p '{
  "dimensions": ["campaign", "device"],
  "measures": [{"name":"impressions","type":"sum","field":"impressions"}],
  "extract": [{"type":"preset","preset":"csv"}],
  "output": {"format":"echarts","chart_type":"sankey"}
}' relatorio.csv > dashboard.html
```

## 📊 Formatos de saída

13 formatos: `tree`, `flat`, `compact`, `csv`, `md_table`, `yaml`, `json`,
`xml`, `dot`, `mermaid`, `plantuml`, `drawio`, `echarts`.

31 perfis integrados — código, logs, CSV, SEO, K8s, OpenAPI, SDD.
Lista completa no [README em inglês](README.md#-what-you-get).

## 📜 Licença

Apache License 2.0 — veja [LICENSE](LICENSE) e [NOTICE](NOTICE).

**Requisito de atribuição (Apache 2.0 §4d):** ao redistribuir cubest, é
obrigatório incluir o arquivo NOTICE preservando a URL de origem:

> https://github.com/BaryshevS/cubest

## 💖 Apoio

Se cubest economiza tokens nos seus fluxos diários com agentes ou
encurta um incidente, considere patrocinar — o financiamento vai
direto para itens do roadmap (t-digest, CSV em streaming, snippets
para agentes) e para a infraestrutura:

- **GitHub Sponsors** → https://github.com/sponsors/BaryshevS
- **Open Collective** → https://opencollective.com/baryshevsv

Até 3 USD/mês mantêm o projeto vivo. Os patrocinadores têm prioridade
na triagem de issues e são creditados nas notas de cada versão.

## ⭐ Marque com estrela

Se cubest economiza parte do seu orçamento de IA ou encurta um incidente
SRE em uma hora — uma estrela ajuda os outros a encontrá-lo. É só isso.

<a href="https://github.com/BaryshevS/cubest/stargazers">
  <img src="https://img.shields.io/github/stars/BaryshevS/cubest?style=social" alt="Star">
</a>
