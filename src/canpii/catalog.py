"""Machine-readable catalogue of what each recognizer detects and how well-sourced it is.

``docs/entities.md`` is the human-readable version of this table; a test
keeps the two in sync.
"""

from __future__ import annotations

from dataclasses import dataclass

from canpii.recognizers import (
    CaAbPhnRecognizer,
    CaBankAccountRecognizer,
    CaBcDriverLicenseRecognizer,
    CaBcPhnRecognizer,
    CaBusinessNumberRecognizer,
    CanadianPatternRecognizer,
    CaOnDriverLicenseRecognizer,
    CaOnOhipRecognizer,
    CaPassportRecognizer,
    CaQcDriverLicenseRecognizer,
    CaQcRamqRecognizer,
)

__all__ = ["CATALOG", "CatalogEntry"]


@dataclass(frozen=True)
class CatalogEntry:
    """Metadata about one recognizer."""

    recognizer: type[CanadianPatternRecognizer]
    format: str
    #: "checksum", "structure" or "context-only"
    validation: str
    #: Provenance of the *format*: "official", "secondary" or "community"
    source_confidence: str
    #: What is lost when exported as regex only (LiteLLM / gateways)
    lost_in_regex_export: str

    @property
    def entity(self) -> str:
        """Entity name emitted by the recognizer."""
        return self.recognizer.ENTITY

    @property
    def province(self) -> str:
        """Province code, or "federal"."""
        return self.recognizer.PROVINCE or "federal"


CATALOG: tuple[CatalogEntry, ...] = (
    CatalogEntry(
        CaOnOhipRecognizer,
        "10 digits (+ optional 1-2 letter version code)",
        "structure (+ Luhn bonus, community)",
        "official",
        "Luhn bonus",
    ),
    CatalogEntry(
        CaQcRamqRecognizer,
        "4 letters + 8 digits (embedded birth date)",
        "structure (birth-date check)",
        "official",
        "birth-date check (impossible dates will match)",
    ),
    CatalogEntry(
        CaBcPhnRecognizer,
        "10 digits starting with 9",
        "checksum (MOD-11)",
        "official",
        "MOD-11 checksum",
    ),
    CatalogEntry(
        CaAbPhnRecognizer,
        "9 digits",
        "context-only",
        "official",
        "nothing (no checksum exists)",
    ),
    CatalogEntry(
        CaPassportRecognizer,
        "2 letters + 6 digits",
        "context-only",
        "secondary",
        "nothing",
    ),
    CatalogEntry(
        CaBusinessNumberRecognizer,
        "9 digits, or 9 digits + program id (RT, RP, ...) + 4 digits",
        "structure (+ Luhn bonus, community)",
        "official",
        "Luhn bonus",
    ),
    CatalogEntry(
        CaBankAccountRecognizer,
        "TTTTT-III transit, 0IIITTTTT routing, 7-12 digit account",
        "context-only",
        "official (MICR) / secondary (EFT)",
        "nothing",
    ),
    CatalogEntry(
        CaOnDriverLicenseRecognizer,
        "1 letter + 14 digits (A1234-56789-01234)",
        "structure (+ birth-date bonus, community)",
        "secondary",
        "birth-date bonus",
    ),
    CatalogEntry(
        CaQcDriverLicenseRecognizer,
        "1 letter + 12 digits",
        "context-only",
        "secondary",
        "nothing",
    ),
    CatalogEntry(
        CaBcDriverLicenseRecognizer,
        "7 digits",
        "context-only",
        "secondary",
        "nothing",
    ),
)
