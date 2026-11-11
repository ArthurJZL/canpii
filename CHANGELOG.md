# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/) (0.x: minor versions may break APIs).

## [Unreleased]

### Added

- `demo/`: Gradio demo app, ready to publish as a Hugging Face Space.
- `examples/cohere_rag_redaction/`: redact with canpii, then RAG with Cohere Embed and
  Chat; reversible pseudonymization, outgoing-payload leak check, `--dry-run`. New
  optional extra `canpii[examples]` (installs `cohere`).
- Benchmark: head-to-head recall of stock Presidio vs Presidio + canpii in
  `benchmarks/run_benchmark.py`, `benchmarks/RESULTS.md` and the README.
- `docs/blog/`: draft article "What Presidio misses for Canadian PII".

## [0.1.0] - 2026-11-05

### Added

- Recognizers (English and French instances): `CaOnOhipRecognizer`,
  `CaQcRamqRecognizer`, `CaBcPhnRecognizer`, `CaAbPhnRecognizer`
  (`CA_HEALTH_NUMBER`); `CaPassportRecognizer` (`CA_PASSPORT`);
  `CaBusinessNumberRecognizer` (`CA_BN`); `CaBankAccountRecognizer`
  (`CA_BANK_ACCOUNT`); `CaOnDriverLicenseRecognizer`, `CaQcDriverLicenseRecognizer`,
  `CaBcDriverLicenseRecognizer` (`CA_DRIVER_LICENSE`).
- Two-tier validation: official rules reject, secondary/community rules only add score
  (`strict=True` to reject on them too); negative context for weak matches.
- Pure-Python `canpii.validators` module (no Presidio dependency).
- `register_all()`, `get_recognizers()`, `create_analyzer()` and a bundled
  `RecognizerRegistryProvider` YAML; enables upstream `CA_SIN` / `CA_POSTAL_CODE`.
- Policy presets `pipeda`, `phipa`, `quebec_law25`.
- CLI `canpii export` for LiteLLM (`presidio_ad_hoc_recognizers` JSON and
  guardrail config), ContextForge `custom_patterns`, generic regex JSON and Presidio YAML.
- Synthetic data generator, labeled bilingual benchmark, docs with sourced format table.

[Unreleased]: https://github.com/ArthurJZL/canpii/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ArthurJZL/canpii/releases/tag/v0.1.0
