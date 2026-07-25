# cubest

[English](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md) · [বাংলা](README.bn.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [日本語](README.ja.md) · **ਪੰਜਾਬੀ**

> **AI ਏਜੰਟ ਦੇ ਹਰ ਰਿਪੋਜ਼ਟਰੀ ਸਕੈਨ ਉੱਤੇ 7–22× ਘੱਟ ਟੋਕਨ।**
> ਸਿੰਗਲ-ਪਾਸ OLAP ਐਗਰੀਗੇਟਰ ਜੋ ਕਿਸੇ ਵੀ ਟੈਕਸਟ ਸਟ੍ਰੀਮ — ਕੋਡ, ਲੌਗ, CSV,
> JSONL, XML, HTML, SDD ਆਰਟੀਫੈਕਟਸ — ਨੂੰ ਇੱਕ ਸੰਖੇਪ ਬਹੁ-ਪੱਖੀ ਕਿਊਬ ਵਿੱਚ
> ਸਮੇਟ ਦਿੰਦਾ ਹੈ। **Claude Code, Cursor, Codex, Aider, Windsurf, Cline,
> Continue.dev** ਅਤੇ ਹਰ ਉਸ AI ਕੋਡਿੰਗ ਏਜੰਟ ਲਈ ਬਣਾਇਆ ਗਿਆ ਹੈ ਜੋ ਇਨਪੁਟ
> ਟੋਕਨ ਦੇ ਹਿਸਾਬ ਨਾਲ ਬਿਲ ਕਰਦਾ ਹੈ।

<p align="left">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.8%2B-blue.svg">
  <img src="https://img.shields.io/badge/deps-stdlib%20only-green.svg">
  <img src="https://img.shields.io/badge/tests-57%20passing-brightgreen.svg">
</p>

## 🧠 AI ਏਜੰਟ ਨੂੰ ਕਿਉਂ ਪਰਵਾਹ ਕਰਨੀ ਚਾਹੀਦੀ ਹੈ

7 ਅਸਲੀ ਸਥਿਤੀਆਂ ਉੱਤੇ ਮਾਪਿਆ ਗਿਆ (ਵੇਖੋ [`examples/`](examples/)):

| # | ਸਥਿਤੀ                                        | Naive tokens | Cubest tokens | ਅਨੁਪਾਤ    |
|---|----------------------------------------------|:------------:|:-------------:|:---------:|
| 1 | nginx ਲੌਗ ਵਿੱਚ 5xx ਜਾਂਚ (5000 ਲਾਈਨਾਂ)         | 3,590        | 158           | **22.7×** |
| 2 | ਰਿਪੋਜ਼ਟਰੀ ਓਨਬੋਰਡਿੰਗ (40 ਫਾਈਲਾਂ)              | 1,256        | 175           | 7.2×      |
| 3 | `git diff` ਤੋਂ MR ਇੰਪੈਕਟ ਮੈਪ                 | 280          | 16            | **17.5×** |
| 4 | ਛੋਟਾ CSV ਰੋਲਅੱਪ (300 ਕਤਾਰਾਂ)                  | 280          | 368           | 0.8× ❌   |
| 5 | 10 HTML ਪੰਨਿਆਂ ਦਾ SEO ਆਡਿਟ                    | 382          | 49            | 7.8×      |
| 6 | ਡਿਸਕ ਵਰਤੋਂ ਆਡਿਟ (300 ਫਾਈਲਾਂ)                 | 338          | 68            | 5.0×      |
| 7 | RSS ਸ਼੍ਰੇਣੀ ਰੋਲਅੱਪ (3×30 ਆਈਟਮਾਂ)              | 1,692        | 265           | 6.4×      |
|   | **ਮੱਧਕ (median)**                            |              |               | **7.2×**  |

Cubest **ਵੱਡੀਆਂ ਸਟ੍ਰੀਮਾਂ ਅਤੇ ਲੜੀਬੱਧ ਡਾਟੇ** ਉੱਤੇ ਜਿੱਤਦਾ ਹੈ। ਬਹੁਤ ਛੋਟੇ
ਟੇਬਲ ਡਾਟੇ (300-ਕਤਾਰ CSV) ਲਈ ਇੱਕ ਸਧਾਰਨ `awk` ਪਾਈਪਲਾਈਨ ਪਹਿਲਾਂ ਹੀ ਸੰਖੇਪ
ਹੁੰਦੀ ਹੈ, ਉੱਥੇ cubest ਹਾਰ ਵੀ ਸਕਦਾ ਹੈ। ਮੁੱਖ ਸਥਿਤੀਆਂ — ਲੌਗ, ਕੋਡ ਟ੍ਰੀ,
sitemap ਕ੍ਰੌਲ — ਵਿੱਚ ਏਜੰਟ ਦੇ ਸੰਦਰਭ ਵਿੱਚ ਡਿੱਗਣ ਵਾਲੇ ਟੋਕਨ 5–25× ਘੱਟ
ਹੁੰਦੇ ਹਨ।

## 🚀 ਇੰਸਟਾਲੇਸ਼ਨ

```bash
# ਸਾਧਾਰਣ ਡਾਊਨਲੋਡ (JSON ਪ੍ਰੋਫਾਈਲਾਂ ਲਈ ਕੋਈ ਡਿਪੈਂਡੈਂਸੀ ਨਹੀਂ)
curl -O https://raw.githubusercontent.com/BaryshevS/cubest/main/cubest.py
python3 cubest.py --profile file_tree .

# pip ਰਾਹੀਂ (PyPI ਉੱਤੇ ਜਲਦੀ ਹੀ)
pip install cubest
cubest --profile file_tree .

# npm ਰੈਪਰ ਰਾਹੀਂ
npx cubest --profile file_tree .
```

## ⚡ ਤੇਜ਼ ਸ਼ੁਰੂਆਤ

```bash
# ਅਣਜਾਣ ਰਿਪੋਜ਼ਟਰੀ ਦਾ ਨਕਸ਼ਾ (3000 ਦੀ ਬਜਾਏ 30 ਲਾਈਨਾਂ)
cubest --profile file_tree .

# nginx.gz ਲੌਗ — top URL × status × p95 latency
cubest --profile nginx_access /var/log/nginx/access.log.gz

# ਹਰ ਭਾਸ਼ਾ ਲਈ LOC ਗਿਣਨਾ
cubest --profile loc_counter .

# CSV → OLAP → ਇੰਟਰਐਕਟਿਵ ECharts ਡੈਸ਼ਬੋਰਡ (ਇੱਕ HTML ਫਾਈਲ)
cubest -p '{
  "dimensions": ["campaign", "device"],
  "measures": [{"name":"impressions","type":"sum","field":"impressions"}],
  "extract": [{"type":"preset","preset":"csv"}],
  "output": {"format":"echarts","chart_type":"sankey"}
}' report.csv > dashboard.html
```

## 📊 ਆਉਟਪੁੱਟ ਫਾਰਮੈਟ

13 ਫਾਰਮੈਟ: `tree`, `flat`, `compact`, `csv`, `md_table`, `yaml`, `json`,
`xml`, `dot`, `mermaid`, `plantuml`, `drawio`, `echarts`।

31 ਬਿਲਟ-ਇਨ ਪ੍ਰੋਫਾਈਲਾਂ — ਕੋਡ, ਲੌਗ, CSV, SEO, K8s, OpenAPI, SDD ਲਈ।
ਪੂਰੀ ਸੂਚੀ [ਅੰਗਰੇਜ਼ੀ README](README.md#-what-you-get) ਵਿੱਚ।

## 📜 ਲਾਇਸੰਸ

Apache License 2.0 — [LICENSE](LICENSE) ਅਤੇ [NOTICE](NOTICE) ਵੇਖੋ।

**ਏਟ੍ਰੀਬਿਊਸ਼ਨ ਸ਼ਰਤ (Apache 2.0 §4d):** ਜੇਕਰ ਤੁਸੀਂ cubest ਨੂੰ ਮੁੜ-ਵੰਡਦੇ
ਹੋ, ਤਾਂ ਅਪਸਟ੍ਰੀਮ URL ਬਰਕਰਾਰ ਰੱਖਦੇ ਹੋਏ NOTICE ਫਾਈਲ ਸ਼ਾਮਲ ਕਰਨੀ ਲਾਜ਼ਮੀ ਹੈ:

> https://github.com/BaryshevS/cubest

## 💖 ਸਹਿਯੋਗ

ਜੇਕਰ cubest ਤੁਹਾਡੇ ਰੋਜ਼ਾਨਾ ਏਜੰਟ ਵਰਕਫਲੋ ਵਿੱਚ ਟੋਕਨ ਬਚਾਉਂਦਾ ਹੈ ਜਾਂ ਕਿਸੇ
ਘਟਨਾ ਨੂੰ ਛੋਟਾ ਕਰਦਾ ਹੈ, ਤਾਂ ਸਪਾਂਸਰ ਬਣਨ ਬਾਰੇ ਸੋਚੋ — ਫੰਡਿੰਗ ਸਿੱਧੀ
roadmap ਦੀਆਂ ਚੀਜ਼ਾਂ (t-digest, ਸਟ੍ਰੀਮਿੰਗ CSV, ਏਜੰਟ ਸਨਿੱਪਟ) ਅਤੇ
ਬੁਨਿਆਦੀ ਢਾਂਚੇ ਵਿੱਚ ਜਾਂਦੀ ਹੈ:

- **GitHub Sponsors** → https://github.com/sponsors/BaryshevS
- **Open Collective** → https://opencollective.com/baryshevsv

ਮਹੀਨੇ ਦੇ $3 ਵੀ ਪ੍ਰੋਜੈਕਟ ਨੂੰ ਚਲਦਾ ਰੱਖਦੇ ਹਨ। ਸਪਾਂਸਰਾਂ ਨੂੰ issue triage
ਵਿੱਚ ਪਹਿਲ ਮਿਲਦੀ ਹੈ ਅਤੇ ਰਿਲੀਜ਼ ਨੋਟਸ ਵਿੱਚ ਉਹਨਾਂ ਦਾ ਜ਼ਿਕਰ ਹੁੰਦਾ ਹੈ।

## ⭐ ਰਿਪੋਜ਼ਟਰੀ ਨੂੰ ਸਟਾਰ ਦਿਓ

ਜੇਕਰ cubest ਤੁਹਾਡੇ AI ਬਜਟ ਦਾ ਹਿੱਸਾ ਬਚਾਉਂਦਾ ਹੈ ਜਾਂ ਕਿਸੇ SRE ਘਟਨਾ ਨੂੰ
ਇੱਕ ਘੰਟੇ ਲਈ ਘਟਾਉਂਦਾ ਹੈ — ਇੱਕ ਸਟਾਰ ਹੋਰਾਂ ਨੂੰ ਇਸਨੂੰ ਲੱਭਣ ਵਿੱਚ ਮਦਦ ਕਰਦਾ
ਹੈ। ਇਹੀ ਸਭ ਬੇਨਤੀ ਹੈ।

<a href="https://github.com/BaryshevS/cubest/stargazers">
  <img src="https://img.shields.io/github/stars/BaryshevS/cubest?style=social" alt="Star">
</a>
