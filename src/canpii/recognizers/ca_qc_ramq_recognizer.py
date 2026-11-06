"""Recognizer for Quebec RAMQ health insurance numbers (NAM)."""

from __future__ import annotations

from presidio_analyzer import Pattern

from canpii import validators
from canpii.recognizers._base import CanadianPatternRecognizer
from canpii.recognizers._context import HEALTH_EN, HEALTH_FR


class CaQcRamqRecognizer(CanadianPatternRecognizer):
    """Recognize Quebec health insurance numbers (CA_HEALTH_NUMBER, province QC).

    Format: 4 letters + 8 digits, e.g. ``ABCD 1234 5678`` - first three letters
    of the surname, first letter of the given name, YY, MM (+50 for biological
    sex female), DD, and a 2-digit RAMQ administrative code.

    Validation (official): the embedded birth month (01-12 or 51-62) and day
    must be plausible; otherwise the match is rejected. An all-uppercase match
    (as printed on the card) receives a small bonus.

    Reference: Gouvernement du Québec (MSSS), "Carte d'assurance maladie avec
    le marqueur de genre X", https://cdn-contenu.quebec.ca/cdn-contenu/sante/documents/Systeme_et_services_de_sante/regimes-assurance/feuillet_marqueur_X.pdf
    """

    ENTITY = "CA_HEALTH_NUMBER"
    PROVINCE = "QC"
    LABEL = "Quebec health insurance number (RAMQ / NAM)"
    UNVERIFIED_BONUS = 0.15

    PATTERNS = [
        Pattern(
            "RAMQ NAM (medium)",
            r"\b[A-Z]{4}[ -]?\d{4}[ -]?\d{4}\b",
            0.35,
        ),
    ]

    CONTEXT = [
        "ramq",
        "régie",
        "regie",
        "assurance",
        "insurance",
        "québec",
        "quebec",
        *HEALTH_EN,
        *HEALTH_FR,
    ]

    def verified_check(self, pattern_text: str) -> bool | None:
        """Reject if the embedded birth date is impossible."""
        return validators.ramq_valid(pattern_text)

    def unverified_check(self, pattern_text: str) -> bool | None:
        """Bonus when the letters are uppercase, as printed on the card."""
        letters = pattern_text[:4]
        return letters.isupper()
