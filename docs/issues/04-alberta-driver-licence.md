---
title: "Add Alberta driver's licence recognizer (CA_DRIVER_LICENSE, AB)"
labels: ["good first issue", "new identifier", "driver-licence"]
---

## Summary

Add `CaAbDriverLicenseRecognizer`.

## What we know (needs verification)

Microsoft Purview lists two Alberta shapes: `NNNNNN-NNN` (6 digits, hyphen,
3 digits) or 5–9 bare digits (secondary source:
<https://learn.microsoft.com/en-us/purview/sit-defn-canada-drivers-license-number>).

## Tasks

- [ ] Look for an Alberta Registries / Alberta Transportation source.
- [ ] The dashed `6-3` form can have a modest score (~0.2); bare 5–9 digits
      must be context-only (≤ 0.01) like `CaBcDriverLicenseRecognizer`.
- [ ] Context words: "Alberta", "registry", "licence", "permis de conduire".
- [ ] Tests: confirm the dashed form does not collide with SIN (`3-3-3`).
- [ ] Docs row + roadmap update.

**Never include a real licence number.**
