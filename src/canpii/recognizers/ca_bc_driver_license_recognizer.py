"""Recognizer for British Columbia driver's licence numbers."""

from __future__ import annotations

from presidio_analyzer import Pattern

from canpii import validators
from canpii.recognizers._base import CanadianPatternRecognizer
from canpii.recognizers._context import DRIVER_EN, DRIVER_FR


class CaBcDriverLicenseRecognizer(CanadianPatternRecognizer):
    """Recognize British Columbia driver's licence numbers (CA_DRIVER_LICENSE, BC).

    Format: 7 digits (secondary source: Microsoft Purview). Seven bare digits
    are extremely common, so this recognizer is **context-only**: its base
    score (0.01) is meant to stay below any sensible threshold unless a
    context word ("driver's licence", "ICBC", "permis de conduire") is nearby.

    Reference: https://learn.microsoft.com/en-us/purview/sit-defn-canada-drivers-license-number
    """

    ENTITY = "CA_DRIVER_LICENSE"
    PROVINCE = "BC"
    LABEL = "British Columbia driver's licence number"

    PATTERNS = [
        Pattern("BC driver's licence (very weak)", r"\b\d{7}\b", 0.01),
    ]

    CONTEXT = [*DRIVER_EN, *DRIVER_FR, "icbc"]

    def verified_check(self, pattern_text: str) -> bool | None:
        """Exactly 7 digits."""
        return validators.bc_dl_structure_valid(pattern_text)
