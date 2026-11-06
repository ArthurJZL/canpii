# Contributing to canpii

Thanks for helping! This project is small on purpose: every recognizer must be
**sourced, tested and documented**. The rules below exist so that a reviewer can
check a contribution without having to trust it.

## Ground rules

1. **No real identifiers, ever.** Not in code, tests, issues, PRs, commit messages,
   screenshots or logs. Use `canpii generate <kind>` or obviously fake values
   (`1234-567-897`, `ZZZX 8812 2512`). PRs containing anything that looks like a real
   identifier will be closed and the history rewritten.
2. **Every format rule needs a source.** Official (government / regulator / payments
   network) sources are preferred. Secondary sources (vendor DLP docs, Wikipedia) and
   community sources (open-source validators, EMR forums) are acceptable only if marked
   as such in `docs/entities.md` — and then the rule may *raise* a score but must not
   *reject* a match (see `CanadianPatternRecognizer.unverified_check`).
3. **Follow Presidio's conventions** so recognizers can be upstreamed:
   one class per file, `COUNTRY_CODE = "ca"`, `PATTERNS` / `CONTEXT` class attributes,
   the standard `__init__(patterns, context, supported_language, supported_entity, name)`
   signature, a docstring with the format and a reference URL.
4. **Portable regexes.** No look-arounds and no back-references, so that exports work
   in Rust-based gateways (`check_contextforge_pattern` enforces this in tests).

## Development setup

```bash
git clone https://github.com/ArthurJZL/canpii
cd canpii
uv sync
uv pip install en_core_web_sm@https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl \
               fr_core_news_sm@https://github.com/explosion/spacy-models/releases/download/fr_core_news_sm-3.8.0/fr_core_news_sm-3.8.0-py3-none-any.whl
uv run ruff check . && uv run ruff format --check .
uv run pytest
uv run python benchmarks/run_benchmark.py
```

Tests that need spaCy models are marked `nlp` and are skipped automatically when the
models are not installed; pattern-level tests always run.

## Recipe: add a province or identifier

Example: Manitoba PHIN (`CA_HEALTH_NUMBER`, province `MB`).

1. **Source.** Find the format in an official document. Save the URL, the page/section,
   and the exact wording. Decide the confidence level for each rule (official /
   secondary / community).
2. **Validator.** Add pure functions to `src/canpii/validators.py` — standard
   library only, no Presidio import — with the provenance in the docstring, e.g.
   `"""9 digits. [official]"""`.
3. **Recognizer.** Create `src/canpii/recognizers/ca_mb_phin_recognizer.py`:
   * subclass `CanadianPatternRecognizer`; set `ENTITY`, `PROVINCE`, `LABEL`,
     `PATTERNS`, `CONTEXT` (English **and** French, single tokens, see `_context.py`);
   * implement `verified_check` for official rules and `unverified_check` for the rest;
   * choose base scores: ≥ 0.4 only for formats that are distinctive *and* validated,
     0.05–0.3 for plausible formats, ≤ 0.01 for "any N digits" shapes (context-only).
4. **Register.** Add the class to `ALL_RECOGNIZERS` in `recognizers/__init__.py` and a
   `CatalogEntry` in `catalog.py`; run `uv run python scripts/generate_docs.py`.
5. **Synthetic data.** Add a generator (and, if there is a checksum, a near-miss
   generator) to `synthetic.py`, plus English and French templates.
6. **Tests.** At minimum: valid / invalid / checksum cases at pattern level, English and
   French sentences end-to-end, and collisions with phone numbers, dates, SIN and other
   identifiers of the same length.
7. **Docs.** Add a row to `docs/entities.md` (rule, confidence, source URL), update the
   matrix in `docs/roadmap.md` and the table in `README.md`, and add a line to the
   `Unreleased` section of `CHANGELOG.md`.
8. **Benchmark.** Run `benchmarks/run_benchmark.py` and paste the table for your entity
   into the PR description.

## Pull request checklist

- [ ] No real identifiers anywhere in the diff (including test data and docs).
- [ ] Every new rule has a row in `docs/entities.md` with a source URL and confidence.
- [ ] Unofficial rules only add score; they do not reject (unless `strict=True`).
- [ ] English and French context words, and tests in both languages.
- [ ] `uv run ruff check . && uv run ruff format --check .` passes.
- [ ] `uv run pytest` passes (with spaCy models installed).
- [ ] `CHANGELOG.md` updated under `Unreleased`.
- [ ] Commits are signed off (`git commit -s`).

## Developer Certificate of Origin (DCO)

All commits must carry a `Signed-off-by:` line certifying the
[Developer Certificate of Origin 1.1](https://developercertificate.org/): that you wrote
the change or otherwise have the right to submit it under the project's license.

```bash
git commit -s -m "Add Manitoba PHIN recognizer"
```

The CI `dco` job checks every commit in a pull request. To fix a missing sign-off:
`git commit --amend -s` (last commit) or `git rebase --signoff main` (several).

**Do not copy code from other projects with incompatible licenses**, and do not copy
code from open upstream Presidio pull requests: write your own implementation from the
public specification and link the upstream PR in the description instead.

## Upstreaming

If your recognizer is backed by official sources and has been released here, consider
proposing it to Presidio (`presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/canada/`),
following Presidio's `CONTRIBUTING.md`. Mention it in our issue tracker so we can
deprecate the duplicate once it is merged.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
