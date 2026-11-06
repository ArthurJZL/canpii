"""Export recognizers to formats consumed by LLM / MCP gateways.

**Regex-only exports lose validation.** LiteLLM ad-hoc recognizers and
gateway custom patterns are plain regular expressions: the checksum and
structure checks implemented in :mod:`canpii.validators` do not
travel with them. Expect more false positives than with the Python package
(see the "lost in regex export" column in ``docs/entities.md``). Where you can,
run a Presidio analyzer that has this package installed and use the
``presidio-yaml`` export instead.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

import yaml

from canpii import __version__
from canpii.catalog import CATALOG
from canpii.presets import Preset
from canpii.recognizers import ALL_RECOGNIZERS, CanadianPatternRecognizer

__all__ = [
    "FORMATS",
    "PortablePattern",
    "check_contextforge_pattern",
    "export",
    "iter_portable_patterns",
    "to_contextforge",
    "to_generic",
    "to_litellm_ad_hoc",
    "to_litellm_config",
    "to_presidio_yaml",
]

FORMATS = ("litellm", "litellm-config", "contextforge", "generic", "presidio-yaml")


@dataclass(frozen=True)
class PortablePattern:
    """A regex that works in Python ``re``/``regex`` and Rust ``regex``.

    Portable patterns avoid look-around and back-references, which the Rust
    ``regex`` crate (used by ContextForge's PII filter) does not support.
    """

    entity: str
    recognizer: str
    province: str | None
    name: str
    regex: str
    score: float
    context: tuple[str, ...]


# Upstream Presidio's own Canadian recognizers are disabled by default in a
# Presidio server, so regex exports re-declare their *formats* here. These
# are written from the public format descriptions (ESDC for SIN, Canada Post
# for postal codes); upstream's SIN regex uses a back-reference, which is not
# portable. Luhn validation of SIN is lost in regex-only exports.
_UPSTREAM_PORTABLE: tuple[PortablePattern, ...] = (
    PortablePattern(
        "CA_SIN",
        "CaSinRecognizer",
        None,
        "SIN (medium, dashed)",
        r"\b[1-79]\d{2}-\d{3}-\d{3}\b",
        0.5,
        ("sin", "social", "insurance", "nas", "assurance", "sociale"),
    ),
    PortablePattern(
        "CA_SIN",
        "CaSinRecognizer",
        None,
        "SIN (medium, spaced)",
        r"\b[1-79]\d{2} \d{3} \d{3}\b",
        0.5,
        ("sin", "social", "insurance", "nas", "assurance", "sociale"),
    ),
    PortablePattern(
        "CA_SIN",
        "CaSinRecognizer",
        None,
        "SIN (weak)",
        r"\b[1-79]\d{8}\b",
        0.05,
        ("sin", "social", "insurance", "nas", "assurance", "sociale"),
    ),
    PortablePattern(
        "CA_POSTAL_CODE",
        "CaPostalCodeRecognizer",
        None,
        "CA Postal Code (strict, with space)",
        r"\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z] \d[ABCEGHJ-NPRSTV-Z]\d\b",
        0.3,
        ("postal", "postcode", "zip", "code"),
    ),
)


def _recognizer_patterns(cls: type[CanadianPatternRecognizer]) -> list[PortablePattern]:
    return [
        PortablePattern(
            cls.ENTITY, cls.__name__, cls.PROVINCE, p.name, p.regex, p.score, tuple(cls.CONTEXT)
        )
        for p in cls.PATTERNS
    ]


def iter_portable_patterns(
    entities: Iterable[str] | None = None,
    min_score: float = 0.0,
    include_upstream: bool = True,
) -> list[PortablePattern]:
    """Return portable patterns, optionally filtered by entity and minimum score."""
    wanted = set(entities) if entities is not None else None
    pats: list[PortablePattern] = []
    for cls in ALL_RECOGNIZERS:
        pats.extend(_recognizer_patterns(cls))
    if include_upstream:
        pats.extend(_UPSTREAM_PORTABLE)
    return [p for p in pats if (wanted is None or p.entity in wanted) and p.score >= min_score]


def _group_by_recognizer(pats: Sequence[PortablePattern]) -> dict[str, list[PortablePattern]]:
    grouped: dict[str, list[PortablePattern]] = {}
    for p in pats:
        grouped.setdefault(p.recognizer, []).append(p)
    return grouped


# --------------------------------------------------------------------------
# LiteLLM
# --------------------------------------------------------------------------


def to_litellm_ad_hoc(
    entities: Iterable[str] | None = None,
    languages: Sequence[str] = ("en",),
    min_score: float = 0.0,
) -> list[dict[str, Any]]:
    """Build the JSON list for LiteLLM's ``presidio_ad_hoc_recognizers`` file.

    LiteLLM forwards this list unchanged as ``ad_hoc_recognizers`` in the
    Presidio ``/analyze`` request; each item is deserialized with
    ``PatternRecognizer.from_dict``. Presidio only applies recognizers whose
    ``supported_language`` matches the request language, so one copy is
    emitted per language.
    """
    out: list[dict[str, Any]] = []
    grouped = _group_by_recognizer(iter_portable_patterns(entities, min_score))
    for lang in languages:
        for recognizer, pats in grouped.items():
            out.append(
                {
                    "name": f"{recognizer} ({lang}, canpii {__version__})",
                    "supported_language": lang,
                    "patterns": [
                        {"name": p.name, "regex": p.regex, "score": p.score} for p in pats
                    ],
                    "context": list(pats[0].context),
                    "supported_entity": pats[0].entity,
                }
            )
    return out


def to_litellm_config(
    preset: Preset,
    ad_hoc_path: str = "./canpii_ad_hoc.json",
    language: str | None = None,
    action: str = "MASK",
    score_threshold: float = 0.4,
) -> str:
    """Build a LiteLLM ``config.yaml`` guardrail snippet for a preset."""
    lang = language or preset.languages[0]
    conf = {
        "guardrails": [
            {
                "guardrail_name": f"canpii-{preset.name}",
                "litellm_params": {
                    "guardrail": "presidio",
                    "mode": "pre_call",
                    "presidio_language": lang,
                    "presidio_ad_hoc_recognizers": ad_hoc_path,
                    "presidio_score_thresholds": {"ALL": score_threshold},
                    "pii_entities_config": {e: action for e in preset.entities},
                },
            }
        ]
    }
    header = (
        f"# LiteLLM guardrail generated by canpii {__version__} "
        f"for preset '{preset.name}'.\n"
        "# Starting point only - not legal advice. Regex-only: checksum validation is lost.\n"
        "# Set PRESIDIO_ANALYZER_API_BASE / PRESIDIO_ANONYMIZER_API_BASE in the environment.\n"
    )
    return header + yaml.safe_dump(conf, sort_keys=False, allow_unicode=True)


# --------------------------------------------------------------------------
# ContextForge (cpex-pii-filter) and generic gateways
# --------------------------------------------------------------------------

# Limits enforced by cpex-pii-filter's validate_custom_pattern (v0.3.x).
_CF_MAX_LEN = 256
_CF_MAX_ALTERNATIONS = 16
_CF_MAX_QUANTIFIERS = 24


def check_contextforge_pattern(regex: str) -> str | None:
    """Return an error message if ``regex`` exceeds cpex-pii-filter's limits."""
    if len(regex) > _CF_MAX_LEN:
        return f"longer than {_CF_MAX_LEN} characters"
    if regex.count("|") > _CF_MAX_ALTERNATIONS:
        return f"more than {_CF_MAX_ALTERNATIONS} alternations"
    quantifiers = sum(regex.count(c) for c in "*+?") + regex.count("{")
    if quantifiers > _CF_MAX_QUANTIFIERS:
        return f"more than {_CF_MAX_QUANTIFIERS} quantifiers"
    for token in ("(?=", "(?!", "(?<=", "(?<!", "\\1"):
        if token in regex:
            return f"uses unsupported construct {token!r}"
    return None


def to_contextforge(entities: Iterable[str] | None = None, min_score: float = 0.3) -> str:
    """Build a ``PIIFilterPlugin`` config snippet with ``custom_patterns``.

    Gateways like ContextForge apply custom patterns *without* context words
    or scores, so only patterns with a base score >= ``min_score`` (default
    0.3: the distinctive formats) are exported. Weak, context-dependent
    patterns (bare 7-12 digit numbers) would otherwise redact every number.
    """
    custom = []
    skipped = []
    for p in iter_portable_patterns(entities, min_score):
        problem = check_contextforge_pattern(p.regex)
        if problem:
            skipped.append(f"{p.name}: {problem}")
            continue
        custom.append(
            {
                "pattern": p.regex,
                "description": f"{p.entity} - {p.name} (canpii; regex only, no checksum)",
                "mask_strategy": None,
                "enabled": True,
            }
        )
    header = (
        f"# ContextForge PIIFilterPlugin custom_patterns generated by canpii "
        f"{__version__}\n"
        f"# Only patterns with base score >= {min_score} are included (no context support).\n"
        "# Regex only: checksum / structure validation is lost. Merge under your\n"
        "# PIIFilterPlugin 'config:' block.\n"
    )
    for s in skipped:
        header += f"# skipped: {s}\n"
    return header + yaml.safe_dump({"custom_patterns": custom}, sort_keys=False)


def to_generic(entities: Iterable[str] | None = None, min_score: float = 0.0) -> dict[str, Any]:
    """Gateway-neutral JSON: entity, regex, score, context and what is lost."""
    meta = {e.recognizer.__name__: e for e in CATALOG}
    items = []
    for p in iter_portable_patterns(entities, min_score):
        entry = meta.get(p.recognizer)
        items.append(
            {
                "entity": p.entity,
                "recognizer": p.recognizer,
                "province": p.province,
                "pattern_name": p.name,
                "regex": p.regex,
                "flags": "i",
                "score": p.score,
                "context": list(p.context),
                "validation_lost": entry.lost_in_regex_export if entry else "Luhn checksum",
            }
        )
    return {
        "generator": f"canpii {__version__}",
        "notes": (
            "Regexes avoid look-around and back-references (portable to Rust regex). "
            "Apply case-insensitively. Inline (?-i:...) groups must stay case-sensitive. "
            "Checksum/structure validation is NOT included; patterns with low scores "
            "need context words to be useful."
        ),
        "patterns": items,
    }


# --------------------------------------------------------------------------
# Presidio YAML (full validation, requires this package installed)
# --------------------------------------------------------------------------


def to_presidio_yaml(
    entities: Iterable[str] | None = None, languages: Sequence[str] = ("en", "fr")
) -> str:
    """Build a recognizer-registry YAML for ``RecognizerRegistryProvider``.

    Uses ``type: predefined`` entries, so ``import canpii`` must run
    before the YAML is loaded - in exchange, validation is fully preserved.
    """
    wanted = set(entities) if entities is not None else None
    recs: list[dict[str, Any]] = []
    for cls in ALL_RECOGNIZERS:
        if wanted is not None and cls.ENTITY not in wanted:
            continue
        recs.append(
            {
                "name": cls.__name__,
                "supported_languages": list(languages),
                "type": "predefined",
                "country_code": "ca",
            }
        )
    for upstream, entity in (
        ("CaSinRecognizer", "CA_SIN"),
        ("CaPostalCodeRecognizer", "CA_POSTAL_CODE"),
    ):
        if wanted is None or entity in wanted:
            recs.append(
                {
                    "name": upstream,
                    "supported_languages": list(languages),
                    "type": "predefined",
                    "enabled": True,
                    "country_code": "ca",
                }
            )
    builtin = {
        "PERSON": "SpacyRecognizer",
        "LOCATION": "SpacyRecognizer",
        "DATE_TIME": "SpacyRecognizer",
        "EMAIL_ADDRESS": "EmailRecognizer",
        "PHONE_NUMBER": "PhoneRecognizer",
        "CREDIT_CARD": "CreditCardRecognizer",
        "IBAN_CODE": "IbanRecognizer",
        "IP_ADDRESS": "IpRecognizer",
        "MEDICAL_LICENSE": "MedicalLicenseRecognizer",
    }
    seen: set[str] = set()
    for entity, rec_name in builtin.items():
        if wanted is not None and entity not in wanted:
            continue
        if rec_name in seen:
            continue
        seen.add(rec_name)
        recs.append(
            {"name": rec_name, "supported_languages": list(languages), "type": "predefined"}
        )
    conf = {
        "supported_languages": list(languages),
        "global_regex_flags": 26,
        "recognizers": recs,
    }
    header = (
        f"# Presidio recognizer registry generated by canpii {__version__}.\n"
        "# Load with RecognizerRegistryProvider(conf_file=...) AFTER `import canpii`.\n"
    )
    return header + yaml.safe_dump(conf, sort_keys=False)


def export(
    fmt: str,
    preset: Preset | None = None,
    languages: Sequence[str] | None = None,
    min_score: float | None = None,
) -> str:
    """Render an export as text. ``fmt`` is one of :data:`FORMATS`."""
    entities = preset.entities if preset else None
    langs = tuple(languages) if languages else (preset.languages if preset else ("en", "fr"))
    if fmt == "litellm":
        data = to_litellm_ad_hoc(entities, langs, min_score or 0.0)
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if fmt == "litellm-config":
        if preset is None:
            raise ValueError("litellm-config requires --preset")
        return to_litellm_config(preset, language=langs[0])
    if fmt == "contextforge":
        return to_contextforge(entities, 0.3 if min_score is None else min_score)
    if fmt == "generic":
        return json.dumps(to_generic(entities, min_score or 0.0), indent=2) + "\n"
    if fmt == "presidio-yaml":
        return to_presidio_yaml(entities, langs)
    raise ValueError(f"Unknown format {fmt!r}; choose one of {FORMATS}")
