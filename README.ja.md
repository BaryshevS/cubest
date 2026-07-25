# cubest

[English](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md) · [বাংলা](README.bn.md) · [Português](README.pt.md) · [Русский](README.ru.md) · **日本語** · [ਪੰਜਾਬੀ](README.pa.md)

> **AI エージェントのリポジトリスキャンあたり 7–22 倍のトークン節約。**
> あらゆるテキストストリーム(コード、ログ、CSV、JSONL、XML、HTML、
> SDD 成果物)をコンパクトな OLAP キューブに畳み込むシングルパス
> アグリゲーター。**Claude Code、Cursor、Codex、Aider、Windsurf、Cline、
> Continue.dev**、そして入力トークンごとに課金されるあらゆる AI
> コーディングエージェント向けに設計されています。

<p align="left">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.8%2B-blue.svg">
  <img src="https://img.shields.io/badge/deps-stdlib%20のみ-green.svg">
  <img src="https://img.shields.io/badge/tests-57%20通過-brightgreen.svg">
</p>

## 🧠 なぜ AI エージェントが気にすべきか

7 つの実際的なシナリオで計測(詳細は [`examples/`](examples/) を参照):

| # | シナリオ                              | ナイーブ tokens | Cubest tokens | 比率      |
|---|---------------------------------------|:---------------:|:-------------:|:---------:|
| 1 | 5000 行の nginx ログの 5xx 調査       | 3,590           | 158           | **22.7×** |
| 2 | リポジトリのオンボーディング(40 files)| 1,256           | 175           | 7.2×      |
| 3 | `git diff` からの MR 影響マップ       | 280             | 16            | **17.5×** |
| 4 | 小さな CSV ロールアップ(300 行)      | 280             | 368           | 0.8× ❌   |
| 5 | 10 ページの SEO 監査                  | 382             | 49            | 7.8×      |
| 6 | 300 ファイルのディスク使用監査        | 338             | 68            | 5.0×      |
| 7 | RSS カテゴリロールアップ(3×30)        | 1,692           | 265           | 6.4×      |
|   | **中央値**                            |                 |               | **7.2×**  |

Cubest は**大きなストリームと階層データ**で勝ちます。非常に小さな表形式データ
(300 行の CSV)では素朴な `awk` パイプラインで既に十分コンパクトで、cubest は
むしろ負けます。

## 🚀 インストール

```bash
# シンプルなダウンロード(JSON プロファイルは deps 不要)
curl -O https://raw.githubusercontent.com/BaryshevS/cubest/main/cubest.py
python3 cubest.py --profile file_tree .

# PyPI から pip 経由(PyYAML 同梱)
pip install cubest
cubest --profile file_tree .

# npm ラッパー経由
npx cubest --profile file_tree .
```

## 🔌 AI エージェントへのインストール

各 harness に対して**2 つの方法**:

- **方法 A — CLI のみ:** バイナリをインストール(`pip install cubest`)
  し、プロンプトで cubest を明示する。最もシンプル、どこでも動作。
- **方法 B — スキル / ルールとして(推奨):** さらに harness の
  **ユーザーグローバル**設定にルールファイルを配置 — プロンプトが
  一致すれば、エージェントが自ら cubest を選択する。

| Harness | インストールコマンド(方法 B) |
|---|---|
| **Claude Code** | `git clone --depth 1 https://github.com/BaryshevS/cubest ~/.claude/skills/cubest` |
| **Cursor** | `~/.cursor/rules/cubest.mdc` を作成(MDC ルール) |
| **OpenAI Codex CLI** | `~/.codex/AGENTS.md` にヒントを追加 |
| **Aider** | `~/.aider/cubest-hint.md` + `~/.aider.conf.yml` に登録 |
| **Windsurf (Codeium)** | `~/.codeium/windsurf/memories/global_rules.md` に追加 |
| **Cline (VS Code)** | Settings → Cline → Custom Instructions |
| **Continue.dev** | `~/.continue/config.json` に customCommand を追加 |
| **OpenCode** | `~/.config/opencode/opencode.json` の `instructions` または `~/AGENTS.md` に追加 |

完全な copy-paste スニペットと harness ごとの検証プロンプト:
👉 [英語 README — Install once, use in every AI agent](README.md#-install-once--use-in-every-ai-agent)

**ユニバーサル・スモークテスト** — 任意のエージェントのチャットに貼り付け:

> cubest でこのディレクトリのファイルツリーを表示 — トップディレクトリ × 拡張子 × サイズ。

エージェントが `count=…, bytes=…` 付きの ASCII ツリーを返せば — cubest は繋がっています。

## ⚡ クイックスタート

```bash
# 見知らぬリポジトリのマップ(3000 行の代わりに 30 行)
cubest --profile file_tree .

# Nginx access.log.gz — トップ URL × ステータス × 平均レイテンシ + p95/p99
cubest --profile nginx_access /var/log/nginx/access.log.gz

# 言語別コード行数(scc/tokei/cloc の代替)
cubest --profile loc_counter .

# CSV → OLAP → インタラクティブ ECharts ダッシュボード
cubest -p '{
  "dimensions": ["campaign", "device"],
  "measures": [{"name":"impressions","type":"sum","field":"impressions"}],
  "extract": [{"type":"preset","preset":"csv"}],
  "output": {"format":"echarts","chart_type":"sankey"}
}' report.csv > report.html
```

## 📊 出力形式

13 の出力形式:`tree`、`flat`、`compact`、`csv`、`md_table`、`yaml`、`json`、
`xml`、`dot`、`mermaid`、`plantuml`、`drawio`、`echarts`。

31 の組み込みプロファイル — コード、ログ、CSV、SEO、K8s、OpenAPI、SDD。
完全なリストは [英語 README](README.md#-what-you-get) をご覧ください。

## 📜 ライセンス

Apache License 2.0 — [LICENSE](LICENSE) と [NOTICE](NOTICE) を参照。

**帰属要件(Apache 2.0 §4d):** cubest を再配布する場合(派生物、製品への
組み込み、ホスト型サービス、コンテナイメージ、CLI ラッパー、IDE プラグイン、
エージェントテンプレートの一部として)、NOTICE ファイル(またはその可読な
内容)を含め、以下のアップストリーム URL を保持する必要があります:

> https://github.com/BaryshevS/cubest

## 💖 サポート

cubest がエージェントの日常ワークフローでトークンを節約したり、
インシデントを短縮したりする場合は、スポンサーになることをご検討ください。
資金はロードマップの項目(t-digest、ストリーミング CSV、エージェント用
スニペット)とインフラに直接使われます:

- **GitHub Sponsors** → https://github.com/sponsors/BaryshevS
- **Open Collective** → https://opencollective.com/baryshevsv

月額 3 ドルでもプロジェクトの継続を支えます。スポンサーは issue の
トリアージで優先され、リリースノートにクレジットされます。

## ⭐ このリポジトリにスターを

cubest が AI 予算の一部を節約したり、SRE インシデントを 1 時間短縮したりした
場合、スターは他の人がこれを見つけるのを助けます。

<a href="https://github.com/BaryshevS/cubest/stargazers">
  <img src="https://img.shields.io/github/stars/BaryshevS/cubest?style=social" alt="Star">
</a>
