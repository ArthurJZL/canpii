"""Recognizer for Canada Revenue Agency Business Numbers (BN)."""

from __future__ import annotations

from presidio_analyzer import Pattern

from canpii import validators
from canpii.recognizers._base import CanadianPatternRecognizer

_PROGRAMS = "RT|RP|RC|RZ|RR|RG|RD|RE|RM|RN|LT|RU|PT"


class CaBusinessNumberRecognizer(CanadianPatternRecognizer):
    """Recognize CRA Business Numbers and program accounts (CA_BN).

    Formats (official, CRA):

    * 9-digit BN, e.g. ``123456789``.
    * 15-character program account: BN + 2-letter program identifier + 4-digit
      reference number, e.g. ``123456789 RT 0001`` (GST/HST).

    Validation:

    * The program identifier must be one CRA lists (official).
    * Luhn check digit on the 9-digit root - community-sourced (used by
      open-source validators such as python-stdnum, not published by CRA).
      A pass adds a bonus; a failure is ignored unless ``strict=True``.

    The bare 9-digit form is indistinguishable from a SIN, so it has a very low
    base score and relies on context. Upstream Presidio has an open proposal
    for this entity (issue #2206, PR #2207); this is an independent
    implementation that uses the same ``CA_BN`` entity name.

    Reference: https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/business-registration/business-number-program-account/need-program-accounts.html
    """

    ENTITY = "CA_BN"
    LABEL = "CRA Business Number / program account"

    PATTERNS = [
        Pattern(
            "BN program account (strong)",
            r"\b\d{9}[ -]?(?:" + _PROGRAMS + r")[ -]?\d{4}\b",
            0.6,
        ),
        Pattern("BN (weak, 9 digits)", r"\b\d{9}\b", 0.05),
    ]

    CONTEXT = [
        "business",
        "entreprise",
        "bn",
        "gst",
        "hst",
        "tvh",
        "payroll",
        "corporation",
        "société",
        "charity",
        "bienfaisance",
        "revenue",
        "revenu",
    ]

    def verified_check(self, pattern_text: str) -> bool | None:
        """Known CRA program identifier (if present)."""
        return validators.bn_structure_valid(pattern_text)

    def unverified_check(self, pattern_text: str) -> bool | None:
        """Community-sourced Luhn check on the 9-digit root."""
        return validators.bn_luhn_valid(pattern_text)
