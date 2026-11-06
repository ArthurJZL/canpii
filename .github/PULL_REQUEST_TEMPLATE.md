## What does this change?

<!-- e.g. "Adds Manitoba PHIN (CA_HEALTH_NUMBER, MB)". Link the issue: Closes #... -->

## Sources

<!-- For new or changed format rules: URL + section, and the confidence level
     (official / secondary / community). -->

## Benchmark

<!-- Paste the relevant rows from `uv run python benchmarks/run_benchmark.py`. -->

## Checklist

- [ ] No real identifiers anywhere in the diff (code, tests, docs, screenshots).
- [ ] New/changed rules documented in `docs/entities.md` with source and confidence.
- [ ] Unofficial rules only add score (no rejection unless `strict=True`).
- [ ] English and French context words and tests.
- [ ] `uv run ruff check . && uv run ruff format --check .`
- [ ] `uv run pytest` (with spaCy models installed)
- [ ] `CHANGELOG.md` updated under `Unreleased`.
- [ ] All commits signed off (`git commit -s`, DCO).
- [ ] No code copied from other projects or open upstream PRs.
