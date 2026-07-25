# cubest

[English](README.md) · **简体中文** · [Русский](README.ru.md) · [Español](README.es.md) · [日本語](README.ja.md)

> **AI 代理每次仓库扫描节省 7–22 倍 token。** 单遍 OLAP 聚合器，把任意文本流
> —— 代码、日志、CSV、JSONL、XML、HTML、SDD 制品 —— 折叠成紧凑的多维立方体。
> 专为 **Claude Code、Cursor、Codex、Aider、Windsurf、Cline、Continue.dev**
> 以及任何按输入 token 计费的 AI 编码代理设计。

<p align="left">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License Apache 2.0"></a>
  <img src="https://img.shields.io/badge/python-3.8%2B-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/deps-仅标准库-green.svg" alt="stdlib only">
  <img src="https://img.shields.io/badge/tests-57%20通过-brightgreen.svg" alt="57 tests passing">
  <img src="https://img.shields.io/badge/profiles-31%20个内置-purple.svg" alt="31 profiles">
  <img src="https://img.shields.io/badge/输出格式-13-orange.svg" alt="13 output formats">
</p>

## 🧠 为什么 AI 代理应该关心

在 7 个真实场景中测得(见 [`examples/`](examples/)):

| # | 场景                                     | 朴素工具响应 | Cubest 响应 | 比率        |
|---|------------------------------------------|:-----------:|:-----------:|:-----------:|
| 1 | 5000 行 nginx 日志 5xx 排查              | 3,590 tok   | 158 tok     | **22.7×**   |
| 2 | 仓库入门(40 文件)                        | 1,256 tok   | 175 tok     | 7.2×        |
| 3 | 从 `git diff` 生成 MR 影响图             | 280 tok     | 16 tok      | **17.5×**   |
| 4 | 小型 CSV 汇总(300 行)                    | 280 tok     | 368 tok     | 0.8× ❌     |
| 5 | 10 页 HTML 的 SEO 审计                   | 382 tok     | 49 tok      | 7.8×        |
| 6 | 300 文件的磁盘使用审计                   | 338 tok     | 68 tok      | 5.0×        |
| 7 | RSS 分类汇总(3 源 × 30 项)               | 1,692 tok   | 265 tok     | 6.4×        |
|   | **中位数**                               |             |             | **7.2×**    |
|   | **峰值(流式日志)**                       |             |             | **22.7×**   |

Cubest 在**大流量和层次化数据**上占优。对于极小的表格数据(300 行 CSV),
朴素的 `awk` 管道已经足够紧凑,cubest 反而输了。在关键场景 —— 日志、代码树、
sitemap 爬虫 —— 落入代理上下文的 token 减少 5–25 倍。

按 Claude Sonnet 4.6 / Opus 4.7 的 3–15 美元每百万输入 token 计算,
每天 1000 个代理会话可节省**每月数千美元**的工具响应摄入费用 ——
而且长会话不再撞上下文墙。

## ⚡ 快速开始

```bash
# 选项 A —— 纯下载(无依赖,JSON 配置文件可直接使用)
curl -O https://raw.githubusercontent.com/BaryshevS/cubest/main/cubest.py
python3 cubest.py --profile file_tree .

# 选项 B —— 通过 pip 安装(PyPI 即将发布)
pip install cubest
cubest --profile file_tree .

# 选项 C —— 通过 uv 临时运行,不需要 venv
uv run --with pyyaml \
  https://raw.githubusercontent.com/BaryshevS/cubest/main/cubest.py \
  --profile file_tree .

# 选项 D —— npm 包装器(委托给 python3)
npx cubest --profile file_tree .
```

## 🎯 核心功能

一个 Python 文件(`cubest.py`,约 1800 行,`PyYAML` 可选),它:

1. **流式读取**文本源 —— 文件、目录、`.gz` 归档、stdin
2. 通过正则或 10 个内置预设**提取**记录
3. **聚合**到内存中的层次化 OLAP 立方体
   (维度 × 度量:`count`、`sum`、`avg`、`min`、`max`、`p50`、
   `p90`、`p95`、`p99`,通过蓄水池采样实现)
4. 以 13 种格式**渲染**立方体 —— 从紧凑树到独立的交互式 HTML 仪表板

零数据库、零 LLM、零 tree-sitter、零外部服务。

## 🔌 AI 代理集成

Cubest 与代理无关。已测试并支持:

| 代理                        | 接入方法                                                    |
|-----------------------------|-------------------------------------------------------------|
| **Claude Code**             | 作为 `.claude/skills/cubest/` 技能发布;见 [SKILL.md](SKILL.md) |
| **Cursor**                  | 在 Cursor 规则中将 `cubest` 添加为允许的 shell 工具         |
| **OpenAI Codex CLI**        | 直接在 shell 中使用 —— Codex 会通过 `--help` 发现它          |
| **Aider**                   | `/run cubest ...` 或添加到 `--command` 别名                 |
| **Windsurf (Codeium)**      | 在 `windsurf.rules` 中允许 `cubest`                         |
| **Cline (VS Code)**         | 启用命令执行;代理按需调用                                  |
| **Continue.dev**            | 在 `~/.continue/config.json` 中添加为自定义斜杠命令         |
| **任何支持工具调用的代理**   | 将 `cubest -p '<inline JSON>' <path>` 包装成一个工具        |

魔法所在:代理**自己生成** `<inline JSON>` 配置文件,针对用户提问动态定制。
无预设提示,无固定 API —— 一个工具就能适应任何查询。

## 🚀 常用命令

```bash
# 快速摸清陌生仓库(30 行代替 3000 行)
cubest --profile file_tree .

# Nginx access.log.gz —— 顶部 URL × 状态 × 平均耗时 + p95/p99
cubest --profile nginx_access /var/log/nginx/access.log.gz

# 按语言统计代码行数(scc/tokei/cloc 的直接替代)
cubest --profile loc_counter .

# 近似调用图 → 交互式 HTML 仪表板
cubest --profile call_graph src/ > graph.html && open graph.html

# CSV → OLAP → ECharts 仪表板(一个 HTML 文件,无需服务器)
cubest -p '{
  "dimensions": ["campaign", "device"],
  "measures": [{"name":"impressions","type":"sum","field":"impressions"}],
  "extract": [{"type":"preset","preset":"csv"}],
  "output": {"format":"echarts","chart_type":"sankey"}
}' ads.csv > ads.html

# 从 git diff 生成 MR/PR 影响图
git diff --name-only origin/main...HEAD | \
  cubest -F - --profile mr_impact .
```

## 📊 输出格式

**13 种输出格式** —— 选择匹配您受众的:

| 格式               | 适合场景                                          |
|--------------------|---------------------------------------------------|
| `tree` (默认)      | 人眼阅读,终端                                    |
| `flat`             | ~30% 更少 token(面包屑行)                       |
| `compact`          | 仅顶层,按计数排序                                |
| `csv` / `tsv`      | 电子表格,下游工具                                |
| `md_table`         | PR/Confluence/README                              |
| `yaml` / `json`    | 程序化消费                                        |
| `xml`              | XML 管道                                          |
| `dot`              | GraphViz → SVG/PDF                                |
| `mermaid`          | GitHub/GitLab/Notion 内联                         |
| `plantuml`         | 企业文档栈                                        |
| `drawio`           | draw.io / diagrams.net 导入                       |
| `echarts`          | 独立交互式 HTML,内嵌 6 种图表类型                |

**31 个内置配置文件** —— 直接使用或自定义:

完整列表见 [English README](README.md#-what-you-get) 或
[`profiles/`](profiles/) 目录。

## 🧪 基准测试

在 CPython 3.8、笔记本级硬件上测量(2026 年 7 月):

| 场景                          | 指标                                          |
|-------------------------------|-----------------------------------------------|
| Cube 插入                     | ~200k 记录/秒,50 万条时占用 25 MiB RSS       |
| 扫描 1 万个小文件             | ~14k 文件/秒(`paths` 预设,不读内容)         |
| 流式 gzip access log 处理     | ~43k 行/秒,**每 50 万行 ΔRSS <200 KiB**      |
| 从 5 万个单元格生成 `flat`    | ~1 毫秒                                       |
| 与朴素读取相比的 token 节省   | **中位数 7.2×,峰值 22.7×**                   |

流式处理保持恒定内存 —— 10 TB 的日志受 I/O 限制,而非内存。

## 🔁 替代常见工具

不是完全替代,但用一个文件覆盖 80% 的典型场景,无需安装工具动物园:

| 工具                          | 由...替代                                        |
|-------------------------------|--------------------------------------------------|
| `scc` / `tokei` / `cloc`      | `loc_counter`                                    |
| `du -sh */`                   | `disk_usage`                                     |
| `find + wc -l`                | `file_tree`                                      |
| GoAccess                      | `nginx_access` + `format: echarts`               |
| `jq | sort | uniq -c`         | `jsonl_events`                                   |
| `yq` / `kubectl get`          | `k8s_resources`                                  |
| `swagger-cli`                 | `openapi_endpoints`                              |
| `git log --stat | awk`        | `git_log_activity`                               |
| `ctags` + grep                | `code_atlas`                                     |
| awk 直方图 + 百分位数         | `p50/p90/p95/p99` 度量                           |
| Screaming Frog (SEO)          | `seo_audit` + `seo_semantic_tree` + `sitemap_map`|
| `pyan` / `graphviz-ast`       | `call_graph` + `format: dot`                     |

## 👥 角色

| 角色                | 主要用例                                                        |
|---------------------|-----------------------------------------------------------------|
| **AI 代理**         | 紧凑仓库地图、机器可读 JSON/CSV/DOT 用于工具链、长会话上下文经济 |
| **开发者**          | 入门、API/组件/技术债务清单、PR 预飞行                          |
| **SRE / on-call**   | 对 `.gz` 日志进行事件调查、延迟百分位数                         |
| **DevOps**          | CI 报告、K8s 清单库存、git 活动仪表板                           |
| **数据工程师**      | 对数据仓库导出进行二次 OLAP、分析汇总                           |
| **SEO / 内容**      | 站点审计、语义标题树、sitemap 分类法                            |

## 📜 许可证与归属

Apache License 2.0 —— 见 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。

**归属要求(Apache 2.0 §4d)**:如果您重新分发 cubest —— 在派生作品中、
嵌入到您的产品中、作为托管服务、容器镜像、CLI 包装器、IDE 插件或代理模板 ——
您**必须**包含 NOTICE 文件(或其可读内容),保留上游 URL:

> https://github.com/BaryshevS/cubest

放置选项:分发中的 `NOTICE` / `THIRD_PARTY_NOTICES` / `ATTRIBUTION` 文件、
您的文档,或"关于" / "致谢" / "由...支持"屏幕。

## 🗺️ 路线图

见 [ROADMAP.md](ROADMAP.md)。

## 🤝 贡献

欢迎问题和 PR。对于实质性更改,请先开启讨论。
所有贡献均在 Apache 2.0 许可证下接受。

## ⭐ 收藏此仓库

如果 cubest 为您节省了一部分 AI 预算,或将 SRE 事件缩短了一小时 ——
一颗星帮助他人找到它。这就是全部请求。

<p align="left">
  <a href="https://github.com/BaryshevS/cubest/stargazers">
    <img src="https://img.shields.io/github/stars/BaryshevS/cubest?style=social" alt="Star cubest on GitHub">
  </a>
</p>
