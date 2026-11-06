---
title: "Review French context words and test sentences (Québec usage)"
labels: ["good first issue", "french", "quality"]
---

## Summary

French context words were written by a bilingual contributor but have not
been reviewed by a native francophone familiar with Québec administrative
vocabulary.

## Tasks

- [ ] Review `src/canpii/recognizers/_context.py` and the `CONTEXT`
      lists in each recognizer. Suggest missing terms (e.g. "carte soleil",
      "NAS", "TVQ", "numéro de succursale", "folio") and flag unnatural ones.
- [ ] Check what lemma `fr_core_news_sm` produces for each suggestion (the
      context matcher compares lemmas): `python -c "import spacy; ..."`.
- [ ] Review the French templates in `synthetic.py`.
- [ ] Re-run `benchmarks/run_benchmark.py` and paste the before/after table.

Remember that Presidio matches context words by substring by default: avoid
short words that occur inside other words.
