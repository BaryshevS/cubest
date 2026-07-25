# Security policy

## Supported versions

Only the latest minor release on PyPI / npm receives security fixes.
Older versions are best-effort — please upgrade before reporting.

## Reporting a vulnerability

**Do not** open a public GitHub issue for security problems.

Instead, email **baryshevs@gmail.com** with:

- A short description of the issue.
- The minimal command / input that reproduces it.
- The `cubest --version` output and how you installed it (pip / npm /
  curl).
- Your assessment of impact (crash, arbitrary write, information leak,
  code execution, denial of service).

You will get an acknowledgement within **72 hours** and, if the report
is valid, a patched release within **14 days**. If the issue is not
reproducible or falls outside cubest's threat model, you will get an
explanation instead.

## Scope

Cubest is a **single-pass aggregator over untrusted text input**. The
threat model treats every input file as untrusted (adversarial log
lines, malformed CSV, giant sitemaps, etc.). In-scope issues include:

- Reading a file causes cubest to write outside its output stream, spawn
  a subprocess, hang, or consume unbounded memory.
- A crafted profile causes the aggregator to escape its sandbox and
  execute arbitrary Python. Note: `filters:` uses a restricted `eval`
  with a minimal builtin allow-list — see `_eval` in `cubest.py`. Any
  path that lets a user-supplied `filters:` expression call outside
  that allow-list is a bug.
- A crafted profile YAML causes YAML parser code execution — cubest
  uses `yaml.safe_load`, so any escape from that is upstream (PyYAML)
  but still worth reporting.
- A crafted regex causes catastrophic backtracking (ReDoS) beyond
  reasonable expectations for the input size.

Out of scope:

- Running an untrusted `--profile` file that intentionally chews CPU —
  users are expected to review profiles they run.
- Overriding built-in profile behavior via `--profile` inline JSON /
  YAML — this is the design.
- Third-party YAML rendering issues in downstream consumers.

## Disclosure

Once fixed, the vulnerability will be disclosed in a GitHub security
advisory and mentioned in the release notes. Reporters are credited by
name unless they prefer to stay anonymous.
