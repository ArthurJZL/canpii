# Entities, formats and sources

Every rule implemented in `canpii` is listed here with the source it
comes from and a confidence level. **If a rule is not in this table, it should
not be in the code.**

Confidence levels:

| Level | Meaning | How the code uses it |
|---|---|---|
| **official** | Published by the issuing authority (federal / provincial government, Payments Canada). | Failing the rule **rejects** the match. |
| **secondary** | Published by a reputable third party (e.g. Microsoft Purview DLP documentation, Wikipedia), not by the issuer. | Used for the regex shape only; no rejection beyond shape. |
| **community** | Widely implemented in open-source / EMR software, no authoritative publication found. *Community-sourced / unverified.* | A pass adds a small score bonus; a failure is **ignored** unless the recognizer is built with `strict=True`. |

Sources were checked on 2026-11-05.

## CA_HEALTH_NUMBER

| Recognizer | Province | Rule | Confidence | Source |
|---|---|---|---|---|
| `CaOnOhipRecognizer` | ON | Health number is a 10-digit lifetime identifier | official | Ontario Ministry of Health, *Health Card Validation Reference Manual* (Oct 2024), pp. 6, 22, 39 — <https://www.ontario.ca/files/2024-10/moh-health-card-validation-reference-manual-en-2024-10-10.pdf> |
| `CaOnOhipRecognizer` | ON | Optional version code of one or two letters | official | Same manual, p. 8 and Appendix D p. 34 |
| `CaOnOhipRecognizer` | ON | 4-3-3 digit grouping as printed (`1234-567-890`) | community | Common print/EMR convention; not specified by MOH |
| `CaOnOhipRecognizer` | ON | Luhn (mod 10) check digit over the 10 digits | **community / unverified** | Implemented by Ontario EMR/billing software; the MOH manual does not describe any check-digit algorithm. Used as a bonus only. |
| `CaQcRamqRecognizer` | QC | NAM = 3 letters of surname + 1 letter of given name + YY + MM (+50 if biological sex female) + DD + 2-digit RAMQ administrative code | official | Gouvernement du Québec (MSSS), *Carte d'assurance maladie avec le marqueur de genre X* — <https://cdn-contenu.quebec.ca/cdn-contenu/sante/documents/Systeme_et_services_de_sante/regimes-assurance/feuillet_marqueur_X.pdf>; also INSPQ response 2024-63 — <https://www.inspq.qc.ca/sites/default/files/2024-11/Reponse_2024-63_DOCS.pdf> |
| `CaQcRamqRecognizer` | QC | NAM is 12 alphanumeric characters | official | RAMQ, *Manuel ASDP*, s. 1.2.1 — <https://www.ramq.gouv.qc.ca/SiteCollectionDocuments/professionnels/manuels/280-deficience-physique/01_Manuel_ASDP_Onglet1_PersonneAssuree.pdf> |
| `CaQcRamqRecognizer` | QC | Day must exist in the month (Feb 29 always accepted: century unknown) | derived from official structure | — |
| `CaQcRamqRecognizer` | QC | Uppercase letters as printed on the card (bonus) | community | — |
| `CaBcPhnRecognizer` | BC | 10 digits, first digit always 9 | official | BC Ministry of Health, *Conformance Standards Vol. 4B — Client Registry application rules*, s. 1.3 — <https://www2.gov.bc.ca/assets/gov/health/practitioner-pro/software-development-guidelines/conformance-standards/vol-4b-app-rules-client-registry.pdf> |
| `CaBcPhnRecognizer` | BC | MOD-11 check digit: weights 2,4,8,5,10,9,7,3 on digits 2–9, sum of (product mod 11), check = 11 − (sum mod 11); 10 or 11 → invalid | official | Same document, s. 1.3, Table 13 |
| `CaAbPhnRecognizer` | AB | Personal Health Number is 9 digits | official | Government of Alberta, *AHCIP Patient Information Update* form — <https://www.alberta.ca/system/files/custom_downloaded_images/ahcip-patient-information-update-form.pdf> |
| `CaAbPhnRecognizer` | AB | `12345-6789` grouping | **community / unverified** | Seen in practice; Alberta asks for the number "without spaces or dashes". Same (very low) score as the bare form. |
| `CaAbPhnRecognizer` | AB | Check digit | not used | No public algorithm found → context-only recognizer |

## CA_PASSPORT

| Recognizer | Rule | Confidence | Source |
|---|---|---|---|
| `CaPassportRecognizer` | Two uppercase letters followed by six digits; no checksum | secondary | Microsoft Purview, *Canada passport number* — <https://learn.microsoft.com/en-us/purview/sit-defn-canada-passport-number>. IRCC's *Features of the passport* page does not describe the number format. |

## CA_BN

| Recognizer | Rule | Confidence | Source |
|---|---|---|---|
| `CaBusinessNumberRecognizer` | BN is 9 digits | official | CRA, *Program accounts you may need* — <https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/business-registration/business-number-program-account/need-program-accounts.html> |
| `CaBusinessNumberRecognizer` | Program account = BN + 2-letter program identifier + 4-digit reference number (e.g. `123456789 RT 0001`) | official | Same page |
| `CaBusinessNumberRecognizer` | Program identifiers RT, RP, RC, RZ, RR, RG, RD, RE, RM, RN, LT, RU, PT | official | Same page (RM is administered by CBSA since 2024-10-21) |
| `CaBusinessNumberRecognizer` | Luhn check digit on the 9-digit root | **community / unverified** | Used by open-source validators (e.g. python-stdnum `ca.bn`) and by upstream proposal presidio#2206; not published by CRA. Bonus only. |

## CA_BANK_ACCOUNT

| Recognizer | Rule | Confidence | Source |
|---|---|---|---|
| `CaBankAccountRecognizer` | MICR transit field: 5-digit branch number, dash, 3-digit institution number | official | Payments Canada, *Standard 006*, s. 4.4.3 — <https://www.payments.ca/sites/default/files/standard006eng.pdf> |
| `CaBankAccountRecognizer` | Electronic routing number `0IIITTTTT` (leading zero + institution + transit) | secondary | Wikipedia, *Routing number (Canada)* — <https://en.wikipedia.org/wiki/Routing_number_(Canada)>; not found in a Payments Canada document we could access |
| `CaBankAccountRecognizer` | Account number 7–12 digits | secondary | Microsoft Purview, *Canada bank account number* (7 or 12 digits) — <https://learn.microsoft.com/en-us/purview/sit-defn-canada-bank-account-number>; Standard 006 leaves the layout to each institution. Context-only (score 0.01). |

## CA_DRIVER_LICENSE

| Recognizer | Province | Rule | Confidence | Source |
|---|---|---|---|---|
| `CaOnDriverLicenseRecognizer` | ON | One letter + 14 digits, printed `A1234-56789-01234` | secondary | Microsoft Purview, *Canada driver's license number* — <https://learn.microsoft.com/en-us/purview/sit-defn-canada-drivers-license-number> |
| `CaOnDriverLicenseRecognizer` | ON | Last six digits = birth date YYMMDD, month +50 for women | **community / unverified** | Widely repeated; consistent with Purview's digit constraints ([0156] month tens digit, [0-3] day tens digit); not published by the Ministry of Transportation. Bonus only. |
| `CaQcDriverLicenseRecognizer` | QC | One letter + 12 digits | secondary | Microsoft Purview (same page) |
| `CaQcDriverLicenseRecognizer` | QC | `A1234-123456-12` grouping | **community / unverified** | Seen on SAAQ cards; not published by SAAQ |
| `CaBcDriverLicenseRecognizer` | BC | 7 digits | secondary | Microsoft Purview (same page). Context-only (score 0.01). |

## Upstream entities (not reimplemented)

| Entity | Upstream recognizer | Notes |
|---|---|---|
| `CA_SIN` | `CaSinRecognizer` | Shipped by Presidio, disabled by default. `register_all()` enables it. |
| `CA_POSTAL_CODE` | `CaPostalCodeRecognizer` | Shipped by Presidio (presidio#2204), disabled by default. `register_all()` enables it. |

## Context words

Context words are bilingual (English and French) and are matched by Presidio
against single-token lemmas near the match. Multi-word phrases ("health
card") never match as a whole, so the lists contain distinctive single
tokens. Short tokens that occur inside common words are avoided because
Presidio's default matching is by substring (`dl` ⊂ "handle", `nam` ⊂
"name", `tps` ⊂ "https", `cra` ⊂ "democracy"). See
`src/canpii/recognizers/_context.py`.

Weak matches (base score ≤ 0.3) are dropped when a *negative* context word
such as "phone", "call", "order", "téléphone", "appelez" or "commande"
appears within 48 characters before them.

## Deliberately deferred

| Identifier | Why deferred |
|---|---|
| Manitoba PHIN, Saskatchewan HSN, Nova Scotia, New Brunswick, PEI, NL health numbers | No authoritative format source checked yet. Candidate good-first-issues (see `docs/roadmap.md`). |
| Territories (YT, NT, NU) health numbers | Same. |
| Other provinces' driver's licences (AB, MB, SK, NS, NB, PE, NL) | Only secondary sources (Purview) found so far; need corroboration. |
| OHIP version-code letter restrictions | The MOH IVR table omits some letters, but the manual does not state a rule. |
| Passport MRZ check digit | Not present in free text. |
| Quebec enterprise number (NEQ), IRCC UCI / client ID, PR card number | Not in v0.1 scope; sources needed. |
