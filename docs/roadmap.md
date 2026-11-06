# Roadmap

## Coverage matrix

Legend: ✅ shipped (v0.1) · ⬆️ shipped upstream in Presidio · 🟡 candidate good-first-issue (drafted in `docs/issues/`) · ⬜ candidate, not yet drafted · — not applicable

### Province / territory identifiers

| Province / territory | Health number (`CA_HEALTH_NUMBER`) | Driver's licence (`CA_DRIVER_LICENSE`) |
|---|---|---|
| Ontario (ON) | ✅ OHIP | ✅ |
| Quebec (QC) | ✅ RAMQ / NAM | ✅ |
| British Columbia (BC) | ✅ PHN | ✅ (context-only) |
| Alberta (AB) | ✅ PHN (context-only) | 🟡 [#issue](issues/04-alberta-driver-licence.md) |
| Manitoba (MB) | 🟡 [PHIN](issues/01-manitoba-phin.md) | 🟡 [#issue](issues/05-manitoba-driver-licence.md) |
| Saskatchewan (SK) | 🟡 [HSN](issues/02-saskatchewan-hsn.md) | ⬜ |
| Nova Scotia (NS) | 🟡 [MSI](issues/03-nova-scotia-health-card.md) | ⬜ |
| New Brunswick (NB) | ⬜ | ⬜ |
| Prince Edward Island (PE) | ⬜ | ⬜ |
| Newfoundland and Labrador (NL) | ⬜ MCP | ⬜ |
| Yukon (YT) | ⬜ | ⬜ |
| Northwest Territories (NT) | ⬜ | ⬜ |
| Nunavut (NU) | ⬜ | ⬜ |

### Federal identifiers

| Identifier | Entity | Status |
|---|---|---|
| Social Insurance Number | `CA_SIN` | ⬆️ upstream (`CaSinRecognizer`), enabled by `register_all()` |
| Postal code | `CA_POSTAL_CODE` | ⬆️ upstream (presidio#2204) |
| Passport | `CA_PASSPORT` | ✅ (context-dependent) |
| CRA Business Number / program accounts | `CA_BN` | ✅ — upstream proposal presidio#2206 / PR #2207 (`CA_BN`) pending |
| Bank transit / institution / account | `CA_BANK_ACCOUNT` | ✅ (context-dependent) |
| IRCC Unique Client Identifier (UCI) | `CA_IRCC_UCI` | 🟡 [issue](issues/06-ircc-uci.md) |
| Quebec enterprise number (NEQ) | `CA_QC_NEQ` | ⬜ |
| Ontario CPSO / provincial physician numbers | `CA_MEDICAL_LICENSE` | ⬜ |

### Quality and tooling

| Item | Status |
|---|---|
| French context review by a native francophone (Québec usage) | 🟡 [issue](issues/07-french-context-review.md) |
| Benchmark on non-template text (e.g. presidio-research generators) | 🟡 [issue](issues/08-benchmark-realistic-corpus.md) |
| Whole-word context matching as the documented default for `register_all` users | ⬜ |
| Upstream CA_SIN context: "sin" matches inside "business" (report to Presidio) | ⬜ |

## Upstreaming plan

1. Keep each recognizer self-contained and in Presidio's style (one class per
   file, `COUNTRY_CODE = "ca"`, `PATTERNS`/`CONTEXT` class attributes, docstring
   with a source URL) so it can be proposed to Presidio with minimal changes.
2. Only propose recognizers whose formats are **official** in
   `docs/entities.md`: BC PHN (MOD-11) and RAMQ (structure) first.
3. When Presidio merges an equivalent recognizer (e.g. PR #2207 for `CA_BN`),
   deprecate ours for one minor release, then delegate to upstream.
