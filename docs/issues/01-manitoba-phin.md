---
title: "Add Manitoba PHIN recognizer (CA_HEALTH_NUMBER, MB)"
labels: ["good first issue", "new identifier", "health"]
---

## Summary

Add a recognizer for Manitoba's Personal Health Identification Number (PHIN),
emitting `CA_HEALTH_NUMBER` with `PROVINCE = "MB"`.

## What we know (needs verification)

* Microsoft Purview lists a "Canada personal health identification number
  (PHIN)" type with a 9-digit format (secondary source).
* No checksum is known.

## Tasks

- [ ] Find an **official** Manitoba Health source for the format (form,
      registration page, data standard). Link it in the PR.
- [ ] Add `src/canpii/recognizers/ca_mb_phin_recognizer.py`
      following `ca_ab_phn_recognizer.py` (9 digits, context-only unless a
      checksum is officially documented).
- [ ] Add a structure validator to `validators.py` (no Presidio import).
- [ ] Add a synthetic generator to `synthetic.py` and templates (en + fr).
- [ ] Tests: positive/negative, en + fr sentences, SIN/BN collision test.
- [ ] Add a row to `docs/entities.md` and update `docs/roadmap.md`.

## Notes

A bare 9-digit number collides with SIN, BN and Alberta PHN, so the base
score must stay very low (≤ 0.05) and rely on context words such as
"PHIN", "Manitoba Health", "carte santé".

**Never paste a real PHIN in this issue, the PR, or the tests.**
