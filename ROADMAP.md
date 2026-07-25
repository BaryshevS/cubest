# cubest — Roadmap

Post-0.1 items (nice to have, not blocking release).

## Accuracy

- [ ] Wire the optional `tdigest` package into `OlapCube` for exact
      percentile aggregation (currently only the import is scaffolded;
      when installed via `pip install tdigest` cubest should transparently
      switch from reservoir sampling to t-digest).

## Streaming coverage

- [ ] Streaming CSV / TSV parser (current implementation is batch-only —
      the whole file is read into memory to parse the header). Target:
      handle CSV / TSV > 1 GiB with constant memory.
- [ ] Streaming JSONL with schema inference — auto-generate dimensions
      from the first N lines.

## Presets

- [ ] `xml_native` preset — real `xml.etree` walk with XPath-like queries
      instead of regex over tags (needed for deeply nested XML).
- [ ] `pdf_text` preset — extract text from PDFs via `pdfplumber` if
      installed.
- [ ] `sqlite` preset — treat a `.sqlite` file as a set of tables and
      pivot on column names.

## Output

- [ ] `format: html` — a simple standalone dashboard on plain Canvas /
      inline SVG (no ECharts CDN required — for air-gapped environments).
- [ ] `format: parquet` — for handing off aggregates to a data pipeline.
- [ ] `format: prometheus` — Prometheus text exposition, so cubest output
      can feed a `/metrics` endpoint.

## Ergonomics

- [ ] `cubest completion bash|zsh|fish` — shell completions for profile
      names and flags.
- [ ] `cubest lint <profile>` — validate a YAML profile against the
      schema before running.
- [ ] `--watch` mode — rerun the same profile on file-tree change.

## Distribution

- [ ] Publish `cubest` to PyPI + npm on first tagged release.
- [ ] Homebrew formula once the repo reaches ~30 stars.
- [ ] Docker Hub image `baryshevs/cubest:latest`.

## Documentation

- [ ] Landing page `cubest.dev` (GitHub Pages) with the interactive
      ECharts demo baked in.
- [ ] Full end-to-end tutorial: "Onboard a monorepo with cubest in 5 min".

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) when it
lands, or just open an issue / PR.
