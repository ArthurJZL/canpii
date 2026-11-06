"""Recognizer for Ontario driver's licence numbers."""

from __future__ import annotations

from presidio_analyzer import Pattern

from canpii import validators
from canpii.recognizers._base import CanadianPatternRecognizer
from canpii.recognizers._context import DRIVER_EN, DRIVER_FR


class CaOnDriverLicenseRecognizer(CanadianPatternRecognizer):
    """Recognize Ontario driver's licence numbers (CA_DRIVER_LICENSE, ON).

    Format: one letter + 14 digits, usually printed ``A1234-56789-01234``
    (secondary source: Microsoft Purview). The last six digits are commonly
    described as the holder's birth date ``YYMMDD`` with 50 added to the month
    for women (community-sourced; consistent with Purview's digit
    constraints). A plausible embedded date adds a bonus; an implausible one is
    ignored unless ``strict=True``.

    Reference: https://learn.microsoft.com/en-us/purview/sit-defn-canada-drivers-license-number
    """

    ENTITY = "CA_DRIVER_LICENSE"
    PROVINCE = "ON"
    LABEL = "Ontario driver's licence number"

    PATTERNS = [
        Pattern(
            "ON driver's licence (medium)",
            r"\b[A-Z]\d{4}[- ]?\d{5}[- ]?\d{5}\b",
            0.3,
        ),
    ]

    CONTEXT = [*DRIVER_EN, *DRIVER_FR, "mto", "serviceontario"]

    def verified_check(self, pattern_text: str) -> bool | None:
        """One letter + 14 digits."""
        return validators.on_dl_structure_valid(pattern_text)

    def unverified_check(self, pattern_text: str) -> bool | None:
        """Plausible embedded YYMMDD birth date."""
        return validators.on_dl_birthdate_plausible(pattern_text)
