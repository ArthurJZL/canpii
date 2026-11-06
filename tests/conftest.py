"""Shared fixtures.

Pattern-level tests call ``recognizer.analyze`` directly and need no NLP
model. Tests marked ``nlp`` build a full ``AnalyzerEngine`` and are skipped
when the spaCy small models are not installed (e.g. offline CI).
"""

from __future__ import annotations

import importlib.util
import random

import pytest

from canpii.recognizers import CanadianPatternRecognizer

MODELS = {"en": "en_core_web_sm", "fr": "fr_core_news_sm"}
HAVE_MODELS = all(importlib.util.find_spec(m) is not None for m in MODELS.values())

CA_ENTITIES = [
    "CA_HEALTH_NUMBER",
    "CA_PASSPORT",
    "CA_BN",
    "CA_BANK_ACCOUNT",
    "CA_DRIVER_LICENSE",
    "CA_SIN",
]


def pytest_collection_modifyitems(config, items):
    if HAVE_MODELS:
        return
    skip = pytest.mark.skip(reason="spaCy models en_core_web_sm / fr_core_news_sm not installed")
    for item in items:
        if "nlp" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def rng() -> random.Random:
    return random.Random(20261105)


def matches(recognizer: CanadianPatternRecognizer, text: str) -> list[tuple[str, float]]:
    """Run a recognizer without NLP and return (matched text, score) pairs."""
    results = recognizer.analyze(text, recognizer.supported_entities)
    return [(text[r.start : r.end], r.score) for r in results]


def best(recognizer: CanadianPatternRecognizer, text: str, value: str) -> float | None:
    """Highest score for an exact match of ``value`` in ``text``, or None."""
    scores = [s for t, s in matches(recognizer, text) if t == value]
    return max(scores) if scores else None


@pytest.fixture(scope="session")
def analyzer():
    if not HAVE_MODELS:
        pytest.skip("spaCy models not installed")
    from canpii import create_analyzer

    return create_analyzer(languages=["en", "fr"], score_threshold=0.4)
