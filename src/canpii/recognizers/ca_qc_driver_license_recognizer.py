"""Recognizer for Quebec driver's licence numbers."""

from __future__ import annotations

from presidio_analyzer import Pattern

from canpii import validators
from canpii.recognizers._base import CanadianPatternRecognizer
from canpii.recognizers._context import DRIVER_EN, DRIVER_FR


class CaQcDriverLicenseRecognizer(CanadianPatternRecognizer):
    """Recognize Quebec driver's licence numbers (CA_DRIVER_LICENSE, QC).

    Format: one letter + 12 digits (secondary source: Microsoft Purview). The
    ``A1234-123456-12`` grouping seen on SAAQ cards is community-sourced and
    matched as well. No checksum or embedded-date rule is applied because none
    is documented; the recognizer is context-dependent.

    Reference: https://learn.microsoft.com/en-us/purview/sit-defn-canada-drivers-license-number
    """

    ENTITY = "CA_DRIVER_LICENSE"
    PROVINCE = "QC"
    LABEL = "Quebec driver's licence number"

    PATTERNS = [
        Pattern(
            "QC driver's licence (weak, grouped)",
            r"\b[A-Z]\d{4}[- ]\d{6}[- ]\d{2}\b",
            0.2,
        ),
        Pattern("QC driver's licence (weak)", r"\b[A-Z]\d{12}\b", 0.1),
    ]

    CONTEXT = [*DRIVER_EN, *DRIVER_FR, "saaq"]

    def verified_check(self, pattern_text: str) -> bool | None:
        """One letter + 12 digits."""
        return validators.qc_dl_structure_valid(pattern_text)
