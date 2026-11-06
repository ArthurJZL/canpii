"""canpii: Canadian PII recognizers for Microsoft Presidio.

Quick start::

    from canpii import create_analyzer

    analyzer = create_analyzer(languages=["en", "fr"])
    analyzer.analyze("OHIP: 1234-567-897", language="en")

Or add the recognizers to an analyzer you already have::

    from canpii import register_all

    register_all(analyzer.registry, languages=("en",))
"""

from __future__ import annotations

__version__ = "0.1.0"

from canpii.presets import PRESETS, Preset, get_preset
from canpii.recognizers import *  # noqa: F403
from canpii.recognizers import ALL_RECOGNIZERS
from canpii.registry import (
    DEFAULT_LANGUAGES,
    ENTITIES,
    UPSTREAM_ENTITIES,
    create_analyzer,
    get_recognizers,
    recognizer_registry_yaml,
    register_all,
    upstream_recognizers,
)

__all__ = [
    "ALL_RECOGNIZERS",
    "DEFAULT_LANGUAGES",
    "ENTITIES",
    "PRESETS",
    "UPSTREAM_ENTITIES",
    "Preset",
    "__version__",
    "create_analyzer",
    "get_preset",
    "get_recognizers",
    "recognizer_registry_yaml",
    "register_all",
    "upstream_recognizers",
]
