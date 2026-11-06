---
title: "Add Manitoba driver's licence recognizer (CA_DRIVER_LICENSE, MB)"
labels: ["good first issue", "new identifier", "driver-licence"]
---

## Summary

Add `CaMbDriverLicenseRecognizer`.

## What we know (needs verification)

Purview describes an alphanumeric Manitoba shape built from letter pairs and
digits with optional hyphens (secondary source). This shape is distinctive,
which makes it a good candidate for a medium score.

## Tasks

- [ ] Find an MPI (Manitoba Public Insurance) source for the format.
- [ ] Write a portable regex (no look-arounds or back-references — see
      `check_contextforge_pattern`) and a structure validator.
- [ ] Generator, en/fr tests, docs row.

**Synthetic values only.**
