"""Precision/recall of canpii on a synthetic bilingual corpus.

Usage::

    uv run python benchmarks/run_benchmark.py [--n 10] [--seed 2026] [--threshold 0.4]

The corpus comes from :func:`canpii.synthetic.build_corpus`:
template sentences in English and French with fake identifiers, with and
without context words, plus generic numbers (phones, dates, order IDs,
amounts) and near-miss identifiers as negatives.

Caveat: this measures behaviour on *synthetic, template-based* text. It is a
regression benchmark, not an estimate of real-world accuracy.
"""

from __future__ import annotations

import argparse
import time
from collections import defaultdict

from canpii import create_analyzer
from canpii.synthetic import LabeledExample, build_corpus

ENTITIES = [
    "CA_HEALTH_NUMBER",
    "CA_PASSPORT",
    "CA_BN",
    "CA_BANK_ACCOUNT",
    "CA_DRIVER_LICENSE",
    "CA_SIN",
]


def evaluate(
    analyzer,
    corpus: list[LabeledExample],
    context_only: bool,
    errors: list[str] | None = None,
) -> dict[str, list[int]]:
    """Return {entity: [tp, fp, fn]}; optionally collect false positives."""
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for ex in corpus:
        if context_only and ex.spans and not ex.has_context:
            continue
        preds = analyzer.analyze(ex.text, language=ex.language, entities=ENTITIES)
        unmatched = list(ex.spans)
        for p in preds:
            hit = next(
                (
                    g
                    for g in unmatched
                    if g.entity == p.entity_type and p.start < g.end and g.start < p.end
                ),
                None,
            )
            if hit is not None:
                counts[p.entity_type][0] += 1
                unmatched.remove(hit)
            else:
                counts[p.entity_type][1] += 1
                if errors is not None:
                    errors.append(
                        f"FP {p.entity_type} {ex.text[p.start : p.end]!r} "
                        f"score={p.score:.2f} [{ex.kind}] {ex.text!r}"
                    )
        for g in unmatched:
            counts[g.entity][2] += 1
    return counts


def _fmt(tp: int, fp: int, fn: int) -> tuple[str, str, str]:
    p = tp / (tp + fp) if tp + fp else float("nan")
    r = tp / (tp + fn) if tp + fn else float("nan")
    f = 2 * p * r / (p + r) if p + r else float("nan")
    return f"{p:.3f}", f"{r:.3f}", f"{f:.3f}"


def table(sub: dict[str, list[int]], whole: dict[str, list[int]]) -> str:
    """Markdown table comparing substring vs whole-word context matching."""
    lines = [
        "| Entity | Gold | P (substring) | R (substring) | P (whole-word) | R (whole-word) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for e in ENTITIES:
        tp, fp, fn = sub.get(e, [0, 0, 0])
        tp2, fp2, fn2 = whole.get(e, [0, 0, 0])
        p, r, _ = _fmt(tp, fp, fn)
        p2, r2, _ = _fmt(tp2, fp2, fn2)
        lines.append(f"| {e} | {tp + fn} | {p} | {r} | {p2} | {r2} |")
    return "\n".join(lines)


def main() -> None:
    """Run the benchmark and print Markdown tables."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="examples per template")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--threshold", type=float, default=0.4)
    ap.add_argument("--show-errors", action="store_true", help="print false positives")
    args = ap.parse_args()

    corpus = build_corpus(n_per_template=args.n, seed=args.seed)
    n_pos = sum(1 for ex in corpus if ex.spans)
    print(
        f"Corpus: {len(corpus)} sentences ({n_pos} positive, {len(corpus) - n_pos} negative), "
        f"en+fr, seed={args.seed}, threshold={args.threshold}\n"
    )
    t0 = time.perf_counter()
    sub = create_analyzer(score_threshold=args.threshold, context_matching_mode="substring")
    whole = create_analyzer(score_threshold=args.threshold, context_matching_mode="whole_word")
    for label, context_only in (("with context words only", True), ("all positives", False)):
        errors: list[str] = []
        s = evaluate(sub, corpus, context_only, errors)
        w = evaluate(whole, corpus, context_only)
        print(f"### Positives {label}\n")
        print(table(s, w))
        print()
        if args.show_errors and not context_only:
            print("\n".join(sorted(errors)))
            print()
    print(f"_elapsed: {time.perf_counter() - t0:.1f}s_")


if __name__ == "__main__":
    main()
