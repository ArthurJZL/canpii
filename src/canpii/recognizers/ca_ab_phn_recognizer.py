"""Recognizer for Alberta Personal Health Numbers (AHCIP)."""

from __future__ import annotations

from presidio_analyzer import Pattern

from canpii import validators
from canpii.recognizers._base import CanadianPatternRecognizer
from canpii.recognizers._context import HEALTH_EN, HEALTH_FR


class CaAbPhnRecognizer(CanadianPatternRecognizer):
    """Recognize Alberta Personal Health Numbers (CA_HEALTH_NUMBER, province AB).

    Format: 9 digits (official). Alberta Health asks for the number "without
    spaces or dashes"; a ``12345-6789`` grouping is sometimes seen in
    practice (community-sourced) and is matched with an equally weak score.

    Validation: no check digit is published, so this recognizer is
    **context-dependent**: its base score is far below a typical threshold
    and only context words such as "AHCIP" or "Alberta health" lift it. A bare
    9-digit number also collides with SIN and the CRA Business Number.

    Reference: Government of Alberta, AHCIP Patient Information Update form,
    https://www.alberta.ca/system/files/custom_downloaded_images/ahcip-patient-information-update-form.pdf
    """

    ENTITY = "CA_HEALTH_NUMBER"
    PROVINCE = "AB"
    LABEL = "Alberta personal health number (AHCIP)"

    PATTERNS = [
        Pattern("AB PHN (very weak, 9 digits)", r"\b\d{9}\b", 0.01),
        Pattern("AB PHN (very weak, 5-4 grouped)", r"\b\d{5}-\d{4}\b", 0.01),
    ]

    # "assurance"/"insurance" are deliberately absent: they also introduce SINs
    # ("numéro d'assurance sociale", "social insurance number").
    CONTEXT = ["ahcip", "alberta", "phn", *HEALTH_EN, *HEALTH_FR]

    def verified_check(self, pattern_text: str) -> bool | None:
        """Exactly 9 digits."""
        return validators.ab_phn_structure_valid(pattern_text)
