"""Helpers to register canpii recognizers with Presidio."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

from presidio_analyzer import EntityRecognizer

from canpii.recognizers import ALL_RECOGNIZERS, CanadianPatternRecognizer

if TYPE_CHECKING:
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry

__all__ = [
    "DEFAULT_LANGUAGES",
    "ENTITIES",
    "SPACY_MODELS",
    "UPSTREAM_ENTITIES",
    "create_analyzer",
    "get_recognizers",
    "recognizer_registry_yaml",
    "register_all",
    "upstream_recognizers",
]

DEFAULT_LANGUAGES: tuple[str, ...] = ("en", "fr")

#: Entities provided by this package.
ENTITIES: tuple[str, ...] = tuple(dict.fromkeys(cls.ENTITY for cls in ALL_RECOGNIZERS))

#: Canadian entities that upstream Presidio already ships (disabled by default).
UPSTREAM_ENTITIES: tuple[str, ...] = ("CA_SIN", "CA_POSTAL_CODE")

#: spaCy models used by :func:`create_analyzer` (small models; swap for _lg in production).
SPACY_MODELS: dict[str, str] = {"en": "en_core_web_sm", "fr": "fr_core_news_sm"}


def get_recognizers(
    languages: Iterable[str] = DEFAULT_LANGUAGES,
    entities: Iterable[str] | None = None,
    provinces: Iterable[str] | None = None,
    strict: bool = False,
) -> list[CanadianPatternRecognizer]:
    """Instantiate canpii recognizers, one instance per language.

    :param languages: Language codes to create instances for (Presidio
        recognizers are single-language).
    :param entities: Restrict to these entity names (e.g. ``["CA_HEALTH_NUMBER"]``).
    :param provinces: Restrict province-specific recognizers to these
        province codes (e.g. ``["ON", "QC"]``). Federal recognizers
        (passport, BN, bank) are always included.
    :param strict: Also reject matches that fail secondary/community rules.
    """
    wanted_entities = set(entities) if entities is not None else None
    wanted_provinces = {p.upper() for p in provinces} if provinces is not None else None
    out: list[CanadianPatternRecognizer] = []
    for cls in ALL_RECOGNIZERS:
        if wanted_entities is not None and cls.ENTITY not in wanted_entities:
            continue
        if (
            wanted_provinces is not None
            and cls.PROVINCE is not None
            and cls.PROVINCE not in wanted_provinces
        ):
            continue
        for lang in languages:
            out.append(cls(supported_language=lang, strict=strict))
    return out


def upstream_recognizers(languages: Iterable[str] = DEFAULT_LANGUAGES) -> list[EntityRecognizer]:
    """Instantiate upstream Presidio's own Canadian recognizers (SIN, postal code).

    Upstream ships them disabled by default; this enables them for the given
    languages. Returns an empty list on Presidio versions that predate them.
    """
    try:
        from presidio_analyzer.predefined_recognizers import (
            CaPostalCodeRecognizer,
            CaSinRecognizer,
        )
    except ImportError:  # pragma: no cover - older presidio-analyzer
        return []
    out: list[EntityRecognizer] = []
    for lang in languages:
        out.append(CaSinRecognizer(supported_language=lang))
        out.append(CaPostalCodeRecognizer(supported_language=lang))
    return out


def register_all(
    registry: RecognizerRegistry,
    languages: Sequence[str] = DEFAULT_LANGUAGES,
    *,
    entities: Iterable[str] | None = None,
    provinces: Iterable[str] | None = None,
    include_upstream: bool = True,
    strict: bool = False,
) -> list[EntityRecognizer]:
    """Add canpii recognizers to an existing Presidio registry.

    :param registry: ``AnalyzerEngine().registry`` or any ``RecognizerRegistry``.
    :param languages: Languages to register (default English and French).
    :param entities: Optional entity filter.
    :param provinces: Optional province filter for province-specific recognizers.
    :param include_upstream: Also enable upstream ``CaSinRecognizer`` and
        ``CaPostalCodeRecognizer`` if they are not registered yet.
    :param strict: Reject matches failing secondary/community rules too.
    :return: The recognizers that were added.
    """
    added: list[EntityRecognizer] = list(
        get_recognizers(languages, entities=entities, provinces=provinces, strict=strict)
    )
    if include_upstream:
        existing = {(r.name, r.supported_language) for r in registry.recognizers}
        for rec in upstream_recognizers(languages):
            if (rec.name, rec.supported_language) in existing:
                continue
            if entities is not None and rec.supported_entities[0] not in set(entities):
                continue
            added.append(rec)
    for rec in added:
        registry.add_recognizer(rec)
    return added


def recognizer_registry_yaml() -> Path:
    """Path to the bundled YAML for ``RecognizerRegistryProvider``.

    ``import canpii`` must happen before loading it, so that the
    ``type: predefined`` entries can be resolved to this package's classes.
    """
    return Path(str(resources.files("canpii").joinpath("conf/recognizers.yaml")))


def create_analyzer(
    languages: Sequence[str] = DEFAULT_LANGUAGES,
    *,
    models: dict[str, str] | None = None,
    score_threshold: float = 0.4,
    strict: bool = False,
    context_matching_mode: str | None = "whole_word",
) -> AnalyzerEngine:
    """Build an ``AnalyzerEngine`` with spaCy models and all Canadian recognizers.

    Uses the *small* spaCy models by default (``en_core_web_sm``,
    ``fr_core_news_sm``), which must be installed beforehand.

    :param languages: Languages to support.
    :param models: Override the spaCy model per language.
    :param score_threshold: Default minimum score. 0.4 is recommended: weak,
        context-dependent patterns score below it unless context is found.
    :param strict: Reject matches failing secondary/community rules too.
    :param context_matching_mode: ``"whole_word"`` (default here) or
        ``"substring"`` (Presidio's own default). Whole-word matching avoids
        accidental boosts such as upstream CA_SIN's context word "sin"
        matching inside "business". On presidio-analyzer versions without
        this option, Presidio's default enhancer is used. ``None`` also means
        Presidio's default.
    """
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
    from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    model_map = {**SPACY_MODELS, **(models or {})}
    nlp_conf = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": lang, "model_name": model_map[lang]} for lang in languages],
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_conf).create_engine()
    registry = RecognizerRegistry(supported_languages=list(languages))
    registry.load_predefined_recognizers(languages=list(languages), nlp_engine=nlp_engine)
    register_all(registry, languages, strict=strict)
    enhancer = None
    if context_matching_mode is not None:
        try:
            enhancer = LemmaContextAwareEnhancer(context_matching_mode=context_matching_mode)
        except TypeError:  # pragma: no cover - presidio-analyzer without the option
            enhancer = None
    return AnalyzerEngine(
        registry=registry,
        nlp_engine=nlp_engine,
        supported_languages=list(languages),
        default_score_threshold=score_threshold,
        context_aware_enhancer=enhancer,
    )
