"""Recognizer for Canadian bank routing and account numbers."""

from __future__ import annotations

from presidio_analyzer import Pattern

from canpii.recognizers._base import CanadianPatternRecognizer
from canpii.recognizers._context import BANK_EN, BANK_FR


class CaBankAccountRecognizer(CanadianPatternRecognizer):
    """Recognize Canadian bank routing / account numbers (CA_BANK_ACCOUNT).

    Formats:

    * MICR transit field ``TTTTT-III`` - 5-digit branch transit number, dash,
      3-digit financial institution number (official, Payments Canada
      Standard 006 s. 4.4.3).
    * Electronic routing number ``0IIITTTTT`` - leading zero, institution,
      transit (secondary source).
    * Account number - 7 to 12 digits. Account number formats are set by each
      institution and are not standardized, so this pattern is purely
      context-dependent (score 0.01).

    No checksum is applied: there is no public institution-agnostic check
    digit for Canadian account numbers.

    References:
    https://www.payments.ca/sites/default/files/standard006eng.pdf ,
    https://en.wikipedia.org/wiki/Routing_number_(Canada)

    """

    ENTITY = "CA_BANK_ACCOUNT"
    LABEL = "Bank transit / institution / account number"

    PATTERNS = [
        Pattern("CA bank MICR transit-institution (weak)", r"\b\d{5}-\d{3}\b", 0.15),
        Pattern("CA bank electronic routing (weak)", r"\b0\d{8}\b", 0.05),
        Pattern("CA bank account number (very weak)", r"\b\d{7,12}\b", 0.01),
    ]

    CONTEXT = [*BANK_EN, *BANK_FR]
