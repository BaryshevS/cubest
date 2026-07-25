<!--
Thanks for the PR!
Please keep the description focused on WHY, not WHAT (the diff shows what).
-->

## What & why

<!-- 1-2 sentences on the change and the motivating scenario. -->

## Type

- [ ] Bug fix
- [ ] New feature (CLI flag / output format / measure)
- [ ] New profile (in `profiles/`)
- [ ] Docs
- [ ] Refactor / cleanup
- [ ] Performance

## Checklist

- [ ] Tests pass locally (`python3 tests/run_tests.py` — 57 tests).
- [ ] Added / updated a test for the change.
- [ ] Documented the change in `SKILL.md` and the main `README.md` if it
      changes behavior visible to end-users or agents.
- [ ] If a new profile: dropped a `profiles/<name>.yaml` + a sample
      command in the "Cookbook" section of `README.md`.
- [ ] No new runtime dependencies beyond stdlib + `PyYAML` (or, if you
      really need one, argued for it above).
