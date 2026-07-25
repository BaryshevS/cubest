# Contributing to cubest

Thanks for opening the repo! Cubest is small and pragmatic — the code
lives in a single file, dependencies are optional, and the profile
catalog is intentionally simple. Contributions are welcome; the guide
below is short by design.

## Ways to help

- **Report bugs** or unexpected behavior — open an issue with the
  smallest reproducer you can (a snippet of input + the profile + the
  command you ran).
- **Propose new profiles** — see `profiles/*.yaml` for the format. If
  a profile solves a real recurring problem (log rollup, code metric,
  audit), open a "Profile request" issue and paste a sample.
- **Improve the docs** — the 10 language READMEs are hand-written; any
  clarification or accurate translation fix is welcome, especially for
  the non-English variants.
- **Add scenarios to `examples/`** — with measured token savings via
  `examples/*/measure.sh`. Empirical numbers are the whole selling
  point; more scenarios strengthen the case.

## Development setup

```bash
git clone git@github.com:BaryshevS/cubest.git
cd cubest
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"       # includes PyYAML
python3 tests/run_tests.py     # 57 unit tests
```

The whole engine is `cubest.py`. Profiles are YAML/JSON in `profiles/`.
No build step, no code generation.

## Pull request checklist

- [ ] Tests pass locally (`python3 tests/run_tests.py`).
- [ ] New behavior has a test — add one to `tests/run_tests.py`.
- [ ] New CLI flag / profile field is documented in `SKILL.md` and the
      main `README.md`.
- [ ] If you touched `cubest.py`, run one of the `examples/` scenarios
      end-to-end to confirm nothing regressed.
- [ ] Commits follow Conventional Commits style (`feat:`, `fix:`,
      `docs:`, `chore:`, `examples:`) — see recent `git log` for
      examples.
- [ ] The PR description explains **why**, not just what — the diff
      shows the what.

## Style

- Keep `cubest.py` self-contained: no runtime dependency outside the
  standard library except `PyYAML`. If you need something else, argue
  for it in the PR description.
- Prefer flat functions over classes; the existing style is procedural
  by choice.
- Comments explain **why** (a subtle invariant, a workaround) not
  **what** (the code already says what).
- New profiles: aim for one clear purpose per profile. Cross-referenced
  presets are fine (`type: preset, preset: paths` etc.) — reuse before
  inventing.

## License

All contributions are accepted under Apache License 2.0, matching the
rest of the project (see [LICENSE](LICENSE)). By opening a PR you agree
that your contribution can be redistributed under that license.

## Security issues

Do **not** open a public issue for security problems. See
[SECURITY.md](SECURITY.md) for the disclosure process.
