---
title: "Add Saskatchewan Health Services Number recognizer (CA_HEALTH_NUMBER, SK)"
labels: ["good first issue", "new identifier", "health"]
---

## Summary

Add a recognizer for Saskatchewan's Health Services Number (HSN).

## Tasks

- [ ] Find an official eHealth Saskatchewan / Ministry of Health source
      describing the length and any check digit. If a check digit is
      officially documented, implement it as a `verified_check`; otherwise
      do not reject on it.
- [ ] Recognizer file, validator, synthetic generator, en/fr templates.
- [ ] Tests including collisions with SIN (9 digits) and OHIP/BC PHN
      (10 digits), whichever applies.
- [ ] `docs/entities.md` row with source URL and confidence level.

**Do not use real HSNs anywhere. Use `canpii generate` output only.**
