"""Recognizer for Canadian passport numbers."""

from __future__ import annotations

from presidio_analyzer import Pattern

from canpii import validators
from canpii.recognizers._base import CanadianPatternRecognizer


class CaPassportRecognizer(CanadianPatternRecognizer):
    """Recognize Canadian passport numbers (CA_PASSPORT).

    Format: two uppercase letters followed by six digits, e.g. ``AB123456``.
    IRCC does not publish the number format; this follows Microsoft Purview's
    "Canada passport number" definition (secondary source). There is no
    checksum on the passport number itself (the MRZ check digit is not
    present in free text), so the recognizer is context-dependent.

    The letters are matched case-sensitively to reduce false positives
    against lowercase product or order codes.

    Reference: https://learn.microsoft.com/en-us/purview/sit-defn-canada-passport-number
    """

    ENTITY = "CA_PASSPORT"
    LABEL = "Canadian passport number"

    PATTERNS = [
        Pattern("CA passport (weak)", r"\b(?-i:[A-Z]{2})\d{6}\b", 0.1),
    ]

    CONTEXT = ["passport", "passeport", "travel", "voyage", "ircc"]

    def verified_check(self, pattern_text: str) -> bool | None:
        """Two letters + six digits."""
        return validators.passport_structure_valid(pattern_text)
