# cubest

[English](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md) · **বাংলা** · [Português](README.pt.md) · [Русский](README.ru.md) · [日本語](README.ja.md) · [ਪੰਜਾਬੀ](README.pa.md)

> **AI এজেন্টের প্রতিটি রিপোজিটরি স্ক্যানে ৭–২২× কম টোকেন।**
> সিঙ্গেল-পাস OLAP অ্যাগ্রিগেটর যা যেকোনো টেক্সট স্ট্রিম — কোড, লগ, CSV,
> JSONL, XML, HTML, SDD আর্টিফ্যাক্ট — একটি কমপ্যাক্ট মাল্টি-ডাইমেনশনাল
> কিউবে ভাঁজ করে দেয়। **Claude Code, Cursor, Codex, Aider, Windsurf,
> Cline, Continue.dev** এবং ইনপুট টোকেন অনুসারে বিলিং করা যেকোনো AI
> কোডিং এজেন্টের জন্য তৈরি।

<p align="left">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.8%2B-blue.svg">
  <img src="https://img.shields.io/badge/deps-stdlib%20only-green.svg">
  <img src="https://img.shields.io/badge/tests-57%20passing-brightgreen.svg">
</p>

## 🧠 AI এজেন্টের কেন গুরুত্ব দেওয়া উচিত

৭টি বাস্তব পরিস্থিতিতে পরিমাপ করা হয়েছে (দেখুন [`examples/`](examples/)):

| # | পরিস্থিতি                                    | Naive tokens | Cubest tokens | অনুপাত    |
|---|----------------------------------------------|:------------:|:-------------:|:---------:|
| 1 | nginx লগে 5xx তদন্ত (৫০০০ লাইন)              | 3,590        | 158           | **22.7×** |
| 2 | রিপোজিটরি অনবোর্ডিং (৪০টি ফাইল)              | 1,256        | 175           | 7.2×      |
| 3 | `git diff` থেকে MR ইমপ্যাক্ট ম্যাপ           | 280          | 16            | **17.5×** |
| 4 | ছোট CSV রোলআপ (৩০০ সারি)                     | 280          | 368           | 0.8× ❌   |
| 5 | ১০টি HTML পৃষ্ঠার SEO অডিট                   | 382          | 49            | 7.8×      |
| 6 | ডিস্ক ব্যবহার অডিট (৩০০টি ফাইল)              | 338          | 68            | 5.0×      |
| 7 | RSS বিভাগ রোলআপ (৩×৩০ আইটেম)                 | 1,692        | 265           | 6.4×      |
|   | **মধ্যক (median)**                           |              |               | **7.2×**  |

Cubest **বড় স্ট্রিম ও শ্রেণিবদ্ধ ডেটাতে** জেতে। খুব ছোট টেবিল ডেটার
(৩০০ সারির CSV) জন্য সহজ `awk` পাইপলাইন ইতিমধ্যেই কমপ্যাক্ট এবং সেখানে
cubest হারতেও পারে। মূল পরিস্থিতিগুলিতে — লগ, কোড ট্রি, sitemap
ক্রল — এজেন্টের কনটেক্সটে পড়া টোকেন ৫–২৫× কমে যায়।

## 🚀 ইনস্টলেশন

```bash
# সাধারণ ডাউনলোড (JSON প্রোফাইলের জন্য কোনো dependency নেই)
curl -O https://raw.githubusercontent.com/BaryshevS/cubest/main/cubest.py
python3 cubest.py --profile file_tree .

# PyPI থেকে pip-এর মাধ্যমে (PyYAML অন্তর্ভুক্ত)
pip install cubest
cubest --profile file_tree .

# npm র‍্যাপারের মাধ্যমে
npx cubest --profile file_tree .
```

## 🔌 AI এজেন্টে ইনস্টলেশন

প্রতিটি harness-এর জন্য **দুটি উপায়**:

- **উপায় A — শুধু CLI:** binary ইনস্টল করুন (`pip install cubest`),
  প্রম্পটে cubest-এর নাম বলুন। সহজতম, সব জায়গায় কাজ করে।
- **উপায় B — skill / rule হিসেবে (সুপারিশকৃত):** সেই সাথে harness-এর
  **ইউজার-গ্লোবাল** কনফিগে rule ফাইল রাখুন — এজেন্ট নিজেই cubest বেছে
  নেবে যখন প্রম্পট মেলে।

| Harness | ইনস্টল কমান্ড (উপায় B) |
|---|---|
| **Claude Code** | `git clone --depth 1 https://github.com/BaryshevS/cubest ~/.claude/skills/cubest` |
| **Cursor** | `~/.cursor/rules/cubest.mdc` তৈরি করুন (MDC rule) |
| **OpenAI Codex CLI** | `~/.codex/AGENTS.md`-এ hint যোগ করুন |
| **Aider** | `~/.aider/cubest-hint.md` + `~/.aider.conf.yml`-এ রেজিস্টার করুন |
| **Windsurf (Codeium)** | `~/.codeium/windsurf/memories/global_rules.md`-এ যোগ করুন |
| **Cline (VS Code)** | Settings → Cline → Custom Instructions |
| **Continue.dev** | `~/.continue/config.json`-এ customCommand যোগ করুন |
| **OpenCode** | `~/.config/opencode/opencode.json` `instructions` বা `~/AGENTS.md`-এ যোগ করুন |

সম্পূর্ণ copy-paste snippets + প্রতিটি harness-এর জন্য verify prompts:
👉 [ইংরেজি README — Install once, use in every AI agent](README.md#-install-once--use-in-every-ai-agent)

**ইউনিভার্সাল স্মোক-টেস্ট** — যেকোনো এজেন্টের চ্যাটে paste করুন:

> cubest দিয়ে এই directory-র file tree দেখাও — top dirs × ext × size।

যদি এজেন্ট `count=…, bytes=…` সহ ASCII tree ফিরিয়ে দেয় — cubest connected।

## ⚡ দ্রুত শুরু

```bash
# অপরিচিত রিপোজিটরির ম্যাপ (৩০০০-এর বদলে ৩০ লাইন)
cubest --profile file_tree .

# nginx.gz লগ — top URL × status × p95 latency
cubest --profile nginx_access /var/log/nginx/access.log.gz

# প্রতি ভাষায় LOC গণনা
cubest --profile loc_counter .

# CSV → OLAP → ইন্টারঅ্যাকটিভ ECharts ড্যাশবোর্ড (একটি HTML ফাইল)
cubest -p '{
  "dimensions": ["campaign", "device"],
  "measures": [{"name":"impressions","type":"sum","field":"impressions"}],
  "extract": [{"type":"preset","preset":"csv"}],
  "output": {"format":"echarts","chart_type":"sankey"}
}' report.csv > dashboard.html
```

## 📊 আউটপুট ফরম্যাট

১৩টি ফরম্যাট: `tree`, `flat`, `compact`, `csv`, `md_table`, `yaml`, `json`,
`xml`, `dot`, `mermaid`, `plantuml`, `drawio`, `echarts`।

৩১টি বিল্ট-ইন প্রোফাইল — কোড, লগ, CSV, SEO, K8s, OpenAPI, SDD-এর জন্য।
সম্পূর্ণ তালিকা [ইংরেজি README](README.md#-what-you-get)-এ।

## 📜 লাইসেন্স

Apache License 2.0 — [LICENSE](LICENSE) ও [NOTICE](NOTICE) দেখুন।

**অ্যাট্রিবিউশন শর্ত (Apache 2.0 §4d):** cubest পুনর্বণ্টন করলে, NOTICE
ফাইল আপস্ট্রিম URL সংরক্ষণ করে অন্তর্ভুক্ত করতে হবে:

> https://github.com/BaryshevS/cubest

## 💖 সমর্থন

cubest যদি আপনার প্রতিদিনের এজেন্ট ওয়ার্কফ্লোতে টোকেন সাশ্রয় করে বা কোনো
ঘটনার সময় কমায়, তবে স্পনসর হওয়ার কথা ভাবুন — অর্থ সরাসরি roadmap
(t-digest, স্ট্রিমিং CSV, এজেন্ট স্নিপেট) ও ইনফ্রাস্ট্রাকচারে যায়:

- **GitHub Sponsors** → https://github.com/sponsors/BaryshevS
- **Open Collective** → https://opencollective.com/baryshevsv

মাসে $৩ও প্রকল্পটি সচল রাখে। স্পনসররা issue triage-এ অগ্রাধিকার পান
এবং রিলিজ নোটে উল্লেখিত হন।

## ⭐ রিপোজিটরিতে স্টার দিন

cubest যদি আপনার AI বাজেটের একটি অংশ বাঁচায় বা কোনো SRE ঘটনা এক ঘণ্টা
কমায় — একটি স্টার অন্যদের এটি খুঁজে পেতে সাহায্য করে। এটাই একমাত্র অনুরোধ।

<a href="https://github.com/BaryshevS/cubest/stargazers">
  <img src="https://img.shields.io/github/stars/BaryshevS/cubest?style=social" alt="Star">
</a>
