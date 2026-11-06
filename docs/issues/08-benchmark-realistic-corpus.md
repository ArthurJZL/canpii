---
title: "Benchmark on a less template-like synthetic corpus"
labels: ["good first issue", "benchmark", "quality"]
---

## Summary

`benchmarks/run_benchmark.py` uses short template sentences written by the
maintainers, so its numbers are optimistic. Build a harder corpus.

## Ideas

- [ ] Use presidio-research's data generator
      (<https://github.com/data-privacy-stack/presidio-research>) with custom
      providers backed by `canpii.synthetic`.
- [ ] Longer documents: referral letters, invoices, payroll stubs, bilingual
      forms, OCR-like noise (line breaks inside numbers, `O` vs `0`).
- [ ] Report per-entity precision/recall at thresholds 0.3/0.4/0.5.

**Synthetic data only. Do not use real documents, even "anonymized" ones.**
