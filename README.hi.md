# cubest

[English](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · **हिन्दी** · [العربية](README.ar.md) · [বাংলা](README.bn.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [日本語](README.ja.md) · [ਪੰਜਾਬੀ](README.pa.md)

> **AI एजेंट के हर रिपॉज़िटरी स्कैन पर 7–22× कम टोकन।**
> सिंगल-पास OLAP एग्रीगेटर जो किसी भी टेक्स्ट स्ट्रीम — कोड, लॉग, CSV, JSONL,
> XML, HTML, SDD आर्टिफ़ैक्ट्स — को कॉम्पैक्ट क्यूब में समेट देता है।
> **Claude Code, Cursor, Codex, Aider, Windsurf, Cline, Continue.dev** और
> हर AI कोडिंग एजेंट के लिए बनाया गया है जो इनपुट टोकन के हिसाब से बिल करता है।

<p align="left">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.8%2B-blue.svg">
  <img src="https://img.shields.io/badge/deps-stdlib%20only-green.svg">
  <img src="https://img.shields.io/badge/tests-57%20passing-brightgreen.svg">
</p>

## 🧠 AI एजेंट को क्यों परवाह करनी चाहिए

7 वास्तविक परिदृश्यों पर मापा गया (देखें [`examples/`](examples/)):

| # | परिदृश्य                                    | Naive tokens | Cubest tokens | अनुपात    |
|---|---------------------------------------------|:------------:|:-------------:|:---------:|
| 1 | nginx लॉग में 5xx जाँच (5000 पंक्तियाँ)     | 3,590        | 158           | **22.7×** |
| 2 | रिपॉज़िटरी ऑनबोर्डिंग (40 फ़ाइलें)         | 1,256        | 175           | 7.2×      |
| 3 | `git diff` से MR इम्पैक्ट मैप              | 280          | 16            | **17.5×** |
| 4 | छोटा CSV रोलअप (300 पंक्तियाँ)             | 280          | 368           | 0.8× ❌   |
| 5 | 10 HTML पेजों का SEO ऑडिट                  | 382          | 49            | 7.8×      |
| 6 | डिस्क उपयोग ऑडिट (300 फ़ाइलें)            | 338          | 68            | 5.0×      |
| 7 | RSS श्रेणी रोलअप (3×30 आइटम)                | 1,692        | 265           | 6.4×      |
|   | **मध्यक (median)**                          |              |               | **7.2×**  |

Cubest **बड़े प्रवाह और श्रेणीबद्ध डेटा** पर जीतता है। बहुत छोटे टेबल डेटा
(300-पंक्ति CSV) पर एक साधारण `awk` पाइपलाइन पहले से ही कॉम्पैक्ट है और
यहाँ cubest हार भी सकता है। मुख्य परिदृश्यों — लॉग, कोड ट्री, sitemap
क्रॉल — पर एजेंट के कॉन्टेक्स्ट में गिरने वाले टोकन 5–25× कम होते हैं।

## 🚀 इंस्टॉलेशन

```bash
# सादा डाउनलोड (JSON प्रोफ़ाइल के लिए कोई dependency नहीं)
curl -O https://raw.githubusercontent.com/BaryshevS/cubest/main/cubest.py
python3 cubest.py --profile file_tree .

# PyPI से pip के ज़रिये (PyYAML शामिल)
pip install cubest
cubest --profile file_tree .

# npm रैपर के ज़रिये
npx cubest --profile file_tree .
```

## 🔌 AI एजेंट में इंस्टॉलेशन

हर harness के लिए **दो तरीके**:

- **तरीका A — केवल CLI:** binary इंस्टॉल करो (`pip install cubest`),
  प्रॉम्प्ट में cubest का नाम लो। सरल, हर जगह चलता है।
- **तरीका B — skill / rule के रूप में (अनुशंसित):** साथ ही harness की
  **यूज़र-ग्लोबल** config में rule फ़ाइल डालो — एजेंट खुद ही cubest चुनेगा
  जब प्रॉम्प्ट मेल खाए।

| Harness | तरीका B का इंस्टॉलेशन कमांड |
|---|---|
| **Claude Code** | `git clone --depth 1 https://github.com/BaryshevS/cubest ~/.claude/skills/cubest` |
| **Cursor** | `~/.cursor/rules/cubest.mdc` बनाएँ (MDC rule) |
| **OpenAI Codex CLI** | `~/.codex/AGENTS.md` में hint जोड़ें |
| **Aider** | `~/.aider/cubest-hint.md` + `~/.aider.conf.yml` में रजिस्टर करें |
| **Windsurf (Codeium)** | `~/.codeium/windsurf/memories/global_rules.md` में जोड़ें |
| **Cline (VS Code)** | Settings → Cline → Custom Instructions |
| **Continue.dev** | `~/.continue/config.json` में customCommand जोड़ें |
| **OpenCode** | `~/.config/opencode/opencode.json` `instructions` या `~/AGENTS.md` में जोड़ें |

पूर्ण copy-paste snippets + हर harness के लिए verify prompts:
👉 [अंग्रेज़ी README — Install once, use in every AI agent](README.md#-install-once--use-in-every-ai-agent)

**यूनिवर्सल स्मोक-टेस्ट** — किसी भी एजेंट के चैट में paste करें:

> cubest से इस directory का file tree दिखाओ — top dirs × ext × size।

अगर एजेंट `count=…, bytes=…` वाला ASCII tree देता है — cubest connected है।

## ⚡ त्वरित शुरुआत

```bash
# अनजान रिपॉज़िटरी का नक्शा (3000 के बजाय 30 लाइनें)
cubest --profile file_tree .

# nginx.gz लॉग — top URL × status × p95 latency
cubest --profile nginx_access /var/log/nginx/access.log.gz

# प्रति भाषा LOC गिनना
cubest --profile loc_counter .

# CSV → OLAP → इंटरैक्टिव ECharts डैशबोर्ड (एक HTML फ़ाइल)
cubest -p '{
  "dimensions": ["campaign", "device"],
  "measures": [{"name":"impressions","type":"sum","field":"impressions"}],
  "extract": [{"type":"preset","preset":"csv"}],
  "output": {"format":"echarts","chart_type":"sankey"}
}' report.csv > dashboard.html
```

## 📊 आउटपुट प्रारूप

13 प्रारूप: `tree`, `flat`, `compact`, `csv`, `md_table`, `yaml`, `json`,
`xml`, `dot`, `mermaid`, `plantuml`, `drawio`, `echarts`.

31 बिल्ट-इन प्रोफ़ाइल — कोड, लॉग, CSV, SEO, K8s, OpenAPI, SDD के लिए।
पूरी सूची [अंग्रेज़ी README](README.md#-what-you-get) में।

## 📜 लाइसेंस

Apache License 2.0 — [LICENSE](LICENSE) और [NOTICE](NOTICE) देखें।

**एट्रिब्यूशन आवश्यकता (Apache 2.0 §4d):** यदि आप cubest को पुनर्वितरित करते हैं,
तो NOTICE फ़ाइल को अपस्ट्रीम URL सुरक्षित रखते हुए शामिल करना अनिवार्य है:

> https://github.com/BaryshevS/cubest

## 💖 सहयोग

अगर cubest आपके दैनिक एजेंट वर्कफ़्लो में टोकन बचाता है या किसी घटना को कम
करता है, तो प्रायोजक बनने पर विचार करें — यह सीधे roadmap (t-digest,
streaming CSV, एजेंट स्निपेट्स) और इन्फ़्रास्ट्रक्चर को फंड करता है:

- **GitHub Sponsors** → https://github.com/sponsors/BaryshevS
- **Open Collective** → https://opencollective.com/baryshevsv

महीने के $3 भी प्रोजेक्ट चलाते रहते हैं। प्रायोजक issue triage में
प्राथमिकता पाते हैं और रिलीज़ नोट्स में उल्लेखित होते हैं।

## ⭐ रिपॉज़िटरी को स्टार दें

यदि cubest आपके AI बजट का हिस्सा बचाता है या किसी SRE घटना को एक घंटे कम
करता है — एक स्टार दूसरों को इसे खोजने में मदद करता है। बस यही अनुरोध है।

<a href="https://github.com/BaryshevS/cubest/stargazers">
  <img src="https://img.shields.io/github/stars/BaryshevS/cubest?style=social" alt="Star">
</a>
