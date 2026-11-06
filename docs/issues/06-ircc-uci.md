---
title: "Add IRCC Unique Client Identifier (UCI) recognizer"
labels: ["good first issue", "new identifier", "federal"]
---

## Summary

IRCC's Unique Client Identifier (UCI, "client ID") appears on study/work
permits, PR documents and IRCC correspondence. Add a `CA_IRCC_UCI` entity.

## Tasks

- [ ] Cite an IRCC page that states the length/format (commonly described as
      8 or 10 digits, sometimes written `0000-0000`). Mark anything not on an
      IRCC page as community-sourced.
- [ ] Decide the entity name in the PR description (check whether Presidio
      has an open proposal first).
- [ ] Context words in English and French: "UCI", "client ID", "IRCC",
      "numéro de client", "IUC" (identificateur unique de client).
- [ ] Tests for collisions with phone numbers and dates.

**Never post a real UCI; they are tied to immigration files.**
