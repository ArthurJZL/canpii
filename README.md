# canpii

**Canadian PII recognizers for [Microsoft Presidio](https://github.com/data-privacy-stack/presidio):
provincial health numbers, passport, CRA Business Number, bank routing and driver's
licences, with English and French context, LiteLLM / MCP-gateway exports and
PIPEDA / PHIPA / Quebec Law 25 presets.**

[![CI](https://github.com/ArthurJZL/canpii/actions/workflows/ci.yml/badge.svg)](https://github.com/ArthurJZL/canpii/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-green)
![Status](https://img.shields.io/badge/status-alpha-orange)

## Why this exists

Presidio is the de-facto open-source PII detector (the `presidio-analyzer` package has
millions of monthly downloads), but for Canada it ships only two recognizers —
`CA_SIN` and `CA_POSTAL_CODE` — and both are disabled by default. Canadian
health numbers, driver's licences, passports, Business Numbers and bank details are
not covered, while closed products (Microsoft Purview's PIPEDA/PHIPA templates, AWS
Bedrock Guardrails' `CA_HEALTH_NUMBER`) do cover them.

New country recognizers are merged into Presidio slowly, and that is reasonable for a
project of its size. This package lets you **use Canadian recognizers today**, written
in Presidio's own style, and we **upstream what Presidio accepts**.

## Quickstart

```bash
pip install canpii
python -m spacy download en_core_web_sm
python -m spacy download fr_core_news_sm
```

```python
from canpii import create_analyzer, get_preset

analyzer = create_analyzer(languages=["en", "fr"])  # spaCy *_sm models, threshold 0.4
text = "Carte RAMQ ZZZX 8812 2512, numéro d'entreprise 123456782 RT 0001."
for r in analyzer.analyze(text, language="fr", entities=get_preset("quebec_law25").entity_list()):
    print(r.entity_type, text[r.start : r.end], round(r.score, 2))
```

```text
CA_BN 123456782 RT 0001 1.0
CA_HEALTH_NUMBER ZZZX 8812 2512 0.85
```

Already have an `AnalyzerEngine`? Add the recognizers to its registry:

```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from canpii import register_all

analyzer = AnalyzerEngine()  # your existing engine (Presidio's default uses en_core_web_lg)
register_all(analyzer.registry, languages=("en",))
text = "Patient OHIP 1234-567-897 AB, BC PHN 9000 000 018."
results = analyzer.analyze(text, language="en", score_threshold=0.4)
print(AnonymizerEngine().anonymize(text=text, analyzer_results=results).text)
# Patient OHIP <CA_HEALTH_NUMBER>, BC PHN <CA_HEALTH_NUMBER>.
```

`register_all()` also enables Presidio's own `CaSinRecognizer` and
`CaPostalCodeRecognizer`. Use a **score threshold of about 0.4**: weak,
context-dependent patterns are scored well below it and only cross it when a
context word ("OHIP", "carte santé", "permis de conduire", …) is nearby.

No-code / YAML setup with Presidio's `RecognizerRegistryProvider`:

```python
import canpii  # registers the classes so `type: predefined` entries resolve
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

registry = RecognizerRegistryProvider(
    conf_file=canpii.recognizer_registry_yaml()
).create_recognizer_registry()
```

## Supported entities

| Entity | Province | Format | Validation | Format source | Languages |
|---|---|---|---|---|---|
| `CA_HEALTH_NUMBER` | ON (OHIP) | 10 digits + optional 1–2 letter version code | structure; Luhn as bonus only (community-sourced) | official | en, fr |
| `CA_HEALTH_NUMBER` | QC (RAMQ / NAM) | 4 letters + 8 digits with embedded birth date | structure + birth-date check | official | en, fr |
| `CA_HEALTH_NUMBER` | BC (PHN) | 10 digits starting with 9 | MOD-11 checksum | official | en, fr |
| `CA_HEALTH_NUMBER` | AB (AHCIP) | 9 digits | context-only | official | en, fr |
| `CA_PASSPORT` | federal | 2 letters + 6 digits | context-only | secondary | en, fr |
| `CA_BN` | federal | 9 digits, or BN + RT/RP/RC/… + 4 digits | program id check; Luhn as bonus only (community-sourced) | official | en, fr |
| `CA_BANK_ACCOUNT` | federal | `TTTTT-III` transit, `0IIITTTTT` routing, 7–12 digit account | context-only | official / secondary | en, fr |
| `CA_DRIVER_LICENSE` | ON | 1 letter + 14 digits (`A1234-56789-01234`) | structure; birth date as bonus only | secondary | en, fr |
| `CA_DRIVER_LICENSE` | QC | 1 letter + 12 digits | context-only | secondary | en, fr |
| `CA_DRIVER_LICENSE` | BC | 7 digits | context-only (very weak) | secondary | en, fr |
| `CA_SIN`, `CA_POSTAL_CODE` | federal | — | upstream Presidio recognizers, enabled by `register_all()` | — | en, fr |

Every rule, with its source URL and confidence level, is in
[`docs/entities.md`](docs/entities.md). Rules that are only **secondary** or
**community-sourced** never reject a match on their own; they raise the score when
they pass (pass `strict=True` to also reject on failure). Rules from **official**
sources reject matches that fail them.

Other provinces and territories are tracked in [`docs/roadmap.md`](docs/roadmap.md).

## Gateways: LiteLLM, ContextForge and others

```bash
# LiteLLM presidio_ad_hoc_recognizers JSON (one copy per language)
canpii export --format litellm --preset pipeda -l en,fr -o canpii_ad_hoc.json
# LiteLLM config.yaml guardrail snippet (pii_entities_config for the preset, MASK)
canpii export --format litellm-config --preset pipeda
# IBM ContextForge PIIFilterPlugin custom_patterns (distinctive formats only)
canpii export --format contextforge --preset phipa
# Gateway-neutral regex + entity + score + context JSON
canpii export --format generic
# Presidio RecognizerRegistryProvider YAML (keeps full validation)
canpii export --format presidio-yaml --preset quebec_law25
```

**Regex-only exports lose validation.** LiteLLM's ad-hoc recognizers and gateway
custom patterns are plain regular expressions: BC's MOD-11 checksum, the RAMQ
birth-date check, the Luhn bonuses and the negative-context filter do not travel with
them. Expect more false positives than with the Python package. The ContextForge
export keeps only patterns with a base score ≥ 0.3, because gateways without context
support would otherwise redact every 7- to 12-digit number. All exported regexes avoid
look-arounds and back-references so they also compile in Rust's `regex` crate.

For LiteLLM, the Presidio analyzer server must have a French spaCy model loaded to use
`presidio_language: fr`. If you can run your own analyzer image, `pip install
canpii` into it and load the `presidio-yaml` export instead: you keep every
check.

## Policy presets

| Preset | Law | Highlights |
|---|---|---|
| `pipeda` | PIPEDA (federal private sector) | identity, government and financial numbers, contact details |
| `phipa` | Ontario PHIPA (health) | health numbers, names, contact details, dates and locations |
| `quebec_law25` | Quebec P-39.1 as amended by Law 25 | as `pipeda` + dates; French first |

```python
from canpii import get_preset

get_preset("phipa").entity_list()
```

Presets are **a starting point, not legal advice** — see [`docs/presets.md`](docs/presets.md).

## Benchmark

`benchmarks/run_benchmark.py` generates a labeled bilingual synthetic corpus (1,740
sentences: 740 positives with and without context words, 1,000 negatives including
phone numbers, dates, order IDs, amounts, near-miss identifiers and "hard negatives"
that put a context word next to an unrelated number) and reports precision/recall at
threshold 0.4.

Positives **with context words** (seed 2026, `presidio-analyzer` 2.2.366, spaCy `*_sm`):

| Entity | Gold | P (substring) | R (substring) | P (whole-word) | R (whole-word) |
|---|---:|---:|---:|---:|---:|
| CA_HEALTH_NUMBER | 160 | 0.870 | 1.000 | 0.870 | 1.000 |
| CA_PASSPORT | 40 | 1.000 | 1.000 | 1.000 | 1.000 |
| CA_BN | 40 | 1.000 | 1.000 | 1.000 | 1.000 |
| CA_BANK_ACCOUNT | 100 | 0.714 | 1.000 | 0.714 | 1.000 |
| CA_DRIVER_LICENSE | 120 | 0.909 | 1.000 | 0.909 | 1.000 |
| CA_SIN (upstream) | 20 | 0.526 | 1.000 | 1.000 | 1.000 |

All positives, including sentences **without** context words:

| Entity | Gold | P (substring) | R (substring) | P (whole-word) | R (whole-word) |
|---|---:|---:|---:|---:|---:|
| CA_HEALTH_NUMBER | 240 | 0.896 | 0.863 | 0.896 | 0.863 |
| CA_PASSPORT | 60 | 1.000 | 0.667 | 1.000 | 0.667 |
| CA_BN | 60 | 1.000 | 0.933 | 1.000 | 0.933 |
| CA_BANK_ACCOUNT | 160 | 0.714 | 0.625 | 0.714 | 0.625 |
| CA_DRIVER_LICENSE | 180 | 0.921 | 0.778 | 0.921 | 0.778 |
| CA_SIN (upstream) | 40 | 0.679 | 0.950 | 1.000 | 0.950 |

How to read this:

* **This is a regression benchmark on template sentences we wrote, not a real-world
  accuracy estimate.** Scores and negative-context words were tuned on part of the
  negatives; the remaining false positives come from an "untuned" set ("Patient chart
  1234567890", "Bank statement page …", "Driver ID …") where a context word sits next
  to an unrelated number — something no pattern recognizer can resolve.
* Context-only identifiers (Alberta PHN, BC licence, bank account, passport) are
  intentionally missed without context words; that is what lowers recall in the second
  table.
* "substring" vs "whole-word" is Presidio's context matching mode.
  `create_analyzer()` defaults to whole-word: in substring mode, upstream `CA_SIN`'s
  context word "sin" matches inside "**busin**ess", so every Business Number next to the
  word "business" is also reported as a SIN.

Reproduce with `uv run python benchmarks/run_benchmark.py --show-errors`.

## Relationship to upstream Presidio

* This is an independent community package, **not affiliated with Microsoft or the
  Presidio maintainers**. It builds on Presidio's public APIs (`PatternRecognizer`,
  `RecognizerRegistry`, `RecognizerRegistryProvider`) and follows its contribution
  conventions: one recognizer class per file, `COUNTRY_CODE = "ca"`, per-language
  instances, `invalidate_result` for checks, source URLs in docstrings.
* Credit to the Presidio maintainers and to the upstream Canadian contributors:
  `CA_SIN`, and `CA_POSTAL_CODE` (presidio#2204, by GitHub user watsos). We use those recognizers as
  they are rather than reimplementing them.
* **Business Number:** upstream issue presidio#2206 proposes a `CA_BN` recognizer and
  PR presidio#2207 by GitHub user Joey239716 implements it (open since 2026-07-29). Our
  `CA_BN` recognizer is an independent implementation written from the CRA
  documentation and deliberately uses the same entity name, so switching is seamless.
  **Once #2207 (or an equivalent) is merged, we will defer to upstream**: deprecate ours
  for one minor release, then delegate.
* Upstreaming plan: recognizers whose formats are backed by official sources (BC PHN,
  RAMQ first) will be proposed to Presidio as individual PRs, in Presidio's code style,
  once they have had real-world use here. See [`docs/roadmap.md`](docs/roadmap.md).

## Disclaimer

* **Not legal advice.** Presets and documentation describe engineering starting points.
  Compliance with PIPEDA, PHIPA, Law 25 or any other law is your responsibility.
* **Detection is probabilistic.** Pattern recognizers miss identifiers and flag
  unrelated numbers. Do not rely on this package alone to protect sensitive data.
* **Synthetic data only.** All identifiers in this repository, its tests and its
  documentation are generated or obviously fake. Randomly generated values can still
  coincide with issued identifiers; never use them as real identifiers. **Never commit,
  paste or upload real identifiers** — not in issues, PRs, fixtures, screenshots or
  logs. See [`SECURITY.md`](SECURITY.md).
* Government programs and agencies are named only to describe the identifiers they
  issue; no endorsement is implied.

## Contributing

Adding a province or identifier is a well-defined task — see
[`CONTRIBUTING.md`](CONTRIBUTING.md) and the drafted good-first-issues in
[`docs/issues/`](docs/issues/). Commits must be signed off (DCO).

## License

[Apache-2.0](LICENSE). Presidio is MIT-licensed; see [`NOTICE`](NOTICE).
