"""Precision/recall of canpii on a synthetic bilingual corpus.

Usage::

    uv run python benchmarks/run_benchmark.py [--n 10] [--seed 2026] [--threshold 0.4]

The corpus comes from :func:`canpii.synthetic.build_corpus`:
template sentences in English and French with fake identifiers, with and
without context words, plus generic numbers (phones, dates, order IDs,
amounts) and near-miss identifiers as negatives.

It prints two things:

1. Precision/recall of canpii per entity, for Presidio's two context matching
   modes (substring vs whole-word).
2. A head-to-head recall comparison of stock Presidio (default recognizers
   only) against Presidio + canpii on the same sentences. See
   :func:`head_to_head` for how a "hit" is counted.

Caveat: this measures behaviour on *synthetic, template-based* text. It is a
regression benchmark, not an estimate of real-world accuracy.
"""

from __future__ import annotations

import argparse
import time
from collections import Counter, defaultdict
from pathlib import Path

import presidio_analyzer
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

from canpii import create_analyzer
from canpii.registry import SPACY_MODELS
from canpii.synthetic import LabeledExample, build_corpus

ENTITIES = [
    "CA_HEALTH_NUMBER",
    "CA_PASSPORT",
    "CA_BN",
    "CA_BANK_ACCOUNT",
    "CA_DRIVER_LICENSE",
    "CA_SIN",
]

#: Entities that only canpii provides (CA_SIN ships with Presidio, disabled by default).
CANPII_ENTITIES = ENTITIES[:-1]

#: Columns of the head-to-head table: key -> header.
H2H_COLUMNS = {
    "stock_same": "Stock: same type",
    "stock_any": "Stock: any type",
    "stock_any_full": "Stock: any type, full span",
    "stock_any_t0": "Stock: any type, threshold 0",
    "canpii_same": "canpii: same type",
    "canpii_any": "canpii: any type",
}


def create_stock_analyzer(languages: tuple[str, ...] = ("en", "fr")) -> AnalyzerEngine:
    """Stock Presidio: default recognizers, default NER mapping, default context matching.

    The only change from ``AnalyzerEngine()`` is the spaCy models: the same small English
    and French models canpii's analyzer uses, so that both engines see the same NLP
    output and French sentences can be analyzed at all. The score threshold is left at
    Presidio's default (0); :func:`head_to_head` applies the threshold itself.
    """
    conf_file = Path(presidio_analyzer.__file__).parent / "conf" / "default.yaml"
    conf = yaml.safe_load(conf_file.read_text()) if conf_file.exists() else {}
    conf["nlp_engine_name"] = "spacy"
    conf["models"] = [{"lang_code": lang, "model_name": SPACY_MODELS[lang]} for lang in languages]
    nlp_engine = NlpEngineProvider(nlp_configuration=conf).create_engine()
    return AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=list(languages))


def head_to_head(
    stock: AnalyzerEngine,
    canpii_analyzer: AnalyzerEngine,
    corpus: list[LabeledExample],
    context_only: bool,
    threshold: float,
) -> tuple[dict[str, Counter], dict[str, Counter]]:
    """Count, per gold entity, how many gold spans each engine finds.

    Both engines analyze every positive sentence with *all* their recognizers. A gold
    span counts as found when a prediction with score >= ``threshold`` overlaps it:

    * ``*_same``: the prediction has the gold entity type.
    * ``*_any``: the prediction has any entity type (stock Presidio has no Canadian
      health/passport/BN/bank/licence recognizer, but may tag the same characters as
      PHONE_NUMBER, DATE_TIME, US_DRIVER_LICENSE, ...).
    * ``stock_any_full``: as ``stock_any``, but one prediction must cover the whole
      gold span (a partial overlap leaves part of the identifier in the text).
    * ``stock_any_t0``: as ``stock_any`` at threshold 0, Presidio's default.

    Returns ``(counts, labels)``: ``counts[entity]`` holds ``gold`` plus the keys above;
    ``labels[entity]`` counts the entity types stock Presidio assigned to gold spans.
    """
    counts: dict[str, Counter] = defaultdict(Counter)
    labels: dict[str, Counter] = defaultdict(Counter)
    for ex in corpus:
        if not ex.spans or (context_only and not ex.has_context):
            continue
        stock_all = stock.analyze(ex.text, language=ex.language, score_threshold=0.0)
        stock_preds = [p for p in stock_all if p.score >= threshold]
        canpii_preds = canpii_analyzer.analyze(
            ex.text, language=ex.language, score_threshold=threshold
        )
        for g in ex.spans:

            def overlaps(p, g=g) -> bool:
                return p.start < g.end and g.start < p.end

            c = counts[g.entity]
            c["gold"] += 1
            c["stock_same"] += any(overlaps(p) and p.entity_type == g.entity for p in stock_preds)
            c["stock_any"] += any(overlaps(p) for p in stock_preds)
            c["stock_any_full"] += any(p.start <= g.start and p.end >= g.end for p in stock_preds)
            c["stock_any_t0"] += any(overlaps(p) for p in stock_all)
            c["canpii_same"] += any(overlaps(p) and p.entity_type == g.entity for p in canpii_preds)
            c["canpii_any"] += any(overlaps(p) for p in canpii_preds)
            for label in {p.entity_type for p in stock_preds if overlaps(p)}:
                labels[g.entity][label] += 1
    return counts, labels


def head_to_head_table(counts: dict[str, Counter]) -> str:
    """Markdown recall table: stock Presidio vs Presidio + canpii."""
    lines = [
        "| Entity | Gold | " + " | ".join(H2H_COLUMNS.values()) + " |",
        "|---|---:|" + "---:|" * len(H2H_COLUMNS),
    ]

    def row(name: str, c: Counter) -> str:
        cells = [f"{c[k] / c['gold']:.3f}" if c["gold"] else "nan" for k in H2H_COLUMNS]
        return f"| {name} | {c['gold']} | " + " | ".join(cells) + " |"

    total: Counter = Counter()
    for e in CANPII_ENTITIES:
        lines.append(row(e, counts[e]))
        total.update(counts[e])
    lines.append(row("**All five canpii entities**", total))
    lines.append(row("CA_SIN (upstream, off by default)", counts["CA_SIN"]))
    return "\n".join(lines)


def stock_labels_table(counts: dict[str, Counter], labels: dict[str, Counter]) -> str:
    """Markdown table of the entity types stock Presidio gave to gold spans."""
    lines = ["| Gold entity | Gold | Stock Presidio labels (spans) |", "|---|---:|---|"]
    for e in ENTITIES:
        ranked = sorted(labels[e].items(), key=lambda item: (-item[1], item[0]))
        found = ", ".join(f"{label} ({n})" for label, n in ranked) or "none"
        lines.append(f"| {e} | {counts[e]['gold']} | {found} |")
    return "\n".join(lines)


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
    stock = create_stock_analyzer()
    print("## Stock Presidio vs Presidio + canpii\n")
    print(
        "Recall only. Stock Presidio = `AnalyzerEngine` with its default recognizers and the "
        "same spaCy small models; canpii = `create_analyzer()`. Both run all their "
        f"recognizers. A gold span is found when a prediction with score >= {args.threshold} "
        'overlaps it. "same type": the prediction has the gold entity type. "any type": any '
        'entity type at all. "full span": one prediction covers the whole gold span. '
        '"threshold 0": Presidio\'s default threshold instead.\n'
    )
    for context_only in (True, False):
        counts, labels = head_to_head(stock, whole, corpus, context_only, args.threshold)
        scope = "sentences with context words" if context_only else "all positive sentences"
        print(f"### Head-to-head recall, {scope}\n")
        print(head_to_head_table(counts))
        print()
    print(f"### What stock Presidio calls the gold spans (all positives, >= {args.threshold})\n")
    print(stock_labels_table(counts, labels))
    print()
    print(f"_elapsed: {time.perf_counter() - t0:.1f}s_")


if __name__ == "__main__":
    main()
