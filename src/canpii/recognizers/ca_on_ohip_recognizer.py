"""Recognizer for Ontario Health Insurance Plan (OHIP) health numbers."""

from __future__ import annotations

from presidio_analyzer import Pattern

from canpii import validators
from canpii.recognizers._base import CanadianPatternRecognizer
from canpii.recognizers._context import HEALTH_EN, HEALTH_FR


class CaOnOhipRecognizer(CanadianPatternRecognizer):
    """Recognize Ontario health numbers (CA_HEALTH_NUMBER, province ON).

    Format: a 10-digit lifetime health number, optionally followed by a one-
    or two-letter version code, e.g. ``1234-567-890 AB``. The 4-3-3 grouping is
    how numbers are commonly printed; the bare 10-digit form collides with
    phone numbers and therefore has a very low base score.

    Validation:

    * Structure (10 digits + optional version code) - official.
    * Luhn check digit - community-sourced only (implemented by EMR software
      but not published by the Ministry of Health). A pass adds a bonus; a
      failure is ignored unless ``strict=True``.

    The version code is matched case-sensitively (``(?-i:...)``) so that an
    English word such as "is" after the number is not swallowed into the match.

    Reference: Ontario Ministry of Health, Health Card Validation Reference
    Manual (2024-10), https://www.ontario.ca/files/2024-10/moh-health-card-validation-reference-manual-en-2024-10-10.pdf
    """

    ENTITY = "CA_HEALTH_NUMBER"
    PROVINCE = "ON"
    LABEL = "Ontario health number (OHIP)"

    PATTERNS = [
        Pattern(
            "OHIP (medium, 4-3-3 grouped)",
            r"\b\d{4}[- ]\d{3}[- ]\d{3}(?:[- ]?(?-i:[A-Z]{1,2}))?\b",
            0.3,
        ),
        Pattern(
            "OHIP (weak, 10 digits)",
            r"\b\d{10}(?:[- ]?(?-i:[A-Z]{1,2}))?\b",
            0.05,
        ),
    ]

    CONTEXT = ["ohip", "hcn", *HEALTH_EN, "assurance", "ontarienne", *HEALTH_FR]

    def verified_check(self, pattern_text: str) -> bool | None:
        """Reject anything that is not 10 digits + optional version code."""
        return validators.ohip_structure_valid(pattern_text)

    def unverified_check(self, pattern_text: str) -> bool | None:
        """Community-sourced Luhn check digit."""
        return validators.ohip_luhn_valid(pattern_text)
