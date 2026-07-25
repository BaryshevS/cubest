# examples/ci/ — CI snippets

Drop-in configuration fragments for common CI systems.

## GitHub Actions — PR impact comment

`github-actions-pr-impact.yml`

On every pull request:
1. Snapshot tech-debt (TODO/FIXME/HACK counts) on the base branch
2. Snapshot the head branch
3. `cubest --diff` between the two → markdown table of who grew / shrank
4. `mr_impact` map of changed files → md table
5. Post the combined report as a PR comment

Copy to `.github/workflows/cubest-pr-impact.yml`.

## GitLab CI — nightly audit

`gitlab-ci-nightly-audit.yml`

Scheduled job that produces artefacts on a rolling 30-day retention:
- `loc.txt` — lines of code by language
- `tech_debt.md` — TODO/FIXME table
- `tree.txt` — project tree text form
- `callgraph.svg` — approximate call graph rendered via GraphViz
- `tree.html` — interactive ECharts treemap of file sizes

Include the fragment in your `.gitlab-ci.yml`.
