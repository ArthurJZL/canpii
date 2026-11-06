"""Command-line interface: ``canpii export|generate|presets|entities``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from canpii import __version__
from canpii.exporters import FORMATS, export
from canpii.presets import PRESETS, get_preset


def _cmd_export(args: argparse.Namespace) -> int:
    preset = get_preset(args.preset) if args.preset else None
    languages = args.languages.split(",") if args.languages else None
    text = export(args.format, preset=preset, languages=languages, min_score=args.min_score)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    from canpii.synthetic import generate

    for value in generate(args.kind, n=args.n, seed=args.seed, formatted=not args.compact):
        print(value)
    return 0


def _cmd_presets(args: argparse.Namespace) -> int:
    for p in PRESETS.values():
        print(f"{p.name:14} {p.title}")
        print(f"{'':14} {', '.join(p.entities)}")
    print("\nPresets are starting points, not legal advice.")
    return 0


def _cmd_entities(args: argparse.Namespace) -> int:
    from canpii.catalog import CATALOG

    for e in CATALOG:
        print(
            f"{e.entity:20} {e.province:8} {e.recognizer.__name__:30} "
            f"{e.validation:40} source={e.source_confidence}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="canpii",
        description="Canadian PII recognizers for Microsoft Presidio.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_exp = sub.add_parser("export", help="export recognizers for gateways / Presidio YAML")
    p_exp.add_argument("--format", "-f", required=True, choices=FORMATS)
    p_exp.add_argument("--preset", "-p", choices=sorted(PRESETS), help="restrict to a preset")
    p_exp.add_argument("--languages", "-l", help="comma-separated, e.g. en,fr")
    p_exp.add_argument("--min-score", type=float, default=None, help="drop weaker patterns")
    p_exp.add_argument("--output", "-o", help="write to file instead of stdout")
    p_exp.set_defaults(func=_cmd_export)

    p_gen = sub.add_parser("generate", help="print synthetic (fake) identifiers")
    p_gen.add_argument("kind", help="e.g. ohip, ramq, bc_phn, bn, on_dl, phone ...")
    p_gen.add_argument("-n", type=int, default=5)
    p_gen.add_argument("--seed", type=int, default=None)
    p_gen.add_argument("--compact", action="store_true", help="no separators")
    p_gen.set_defaults(func=_cmd_generate)

    p_pre = sub.add_parser("presets", help="list policy presets")
    p_pre.set_defaults(func=_cmd_presets)

    p_ent = sub.add_parser("entities", help="list recognizers and validation levels")
    p_ent.set_defaults(func=_cmd_entities)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``canpii`` console script."""
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
