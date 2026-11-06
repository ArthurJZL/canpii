"""Recognizer for British Columbia Personal Health Numbers (PHN)."""

from __future__ import annotations

from presidio_analyzer import Pattern

from canpii import validators
from canpii.recognizers._base import CanadianPatternRecognizer
from canpii.recognizers._context import HEALTH_EN, HEALTH_FR


class CaBcPhnRecognizer(CanadianPatternRecognizer):
    """Recognize BC Personal Health Numbers (CA_HEALTH_NUMBER, province BC).

    Format: 10 digits, first digit always 9, e.g. ``9123 456 789``.

    Validation (official): MOD-11 check digit, weights 2,4,8,5,10,9,7,3 applied
    to digits 2-9; matches that fail are rejected.

    Reference: BC Ministry of Health, Conformance Standards Vol. 4B
    (Client Registry application rules), section 1.3,
    https://www2.gov.bc.ca/assets/gov/health/practitioner-pro/software-development-guidelines/conformance-standards/vol-4b-app-rules-client-registry.pdf
    """

    ENTITY = "CA_HEALTH_NUMBER"
    PROVINCE = "BC"
    LABEL = "British Columbia personal health number (PHN)"

    PATTERNS = [
        Pattern("BC PHN (medium, 4-3-3 grouped)", r"\b9\d{3}[- ]\d{3}[- ]\d{3}\b", 0.4),
        Pattern("BC PHN (weak, 10 digits)", r"\b9\d{9}\b", 0.1),
    ]

    CONTEXT = ["phn", "msp", "carecard", "services", *HEALTH_EN, *HEALTH_FR]

    def verified_check(self, pattern_text: str) -> bool | None:
        """Official MOD-11 check digit."""
        return validators.bc_phn_valid(pattern_text)
