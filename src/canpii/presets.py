"""Canadian privacy-law policy presets.

A preset is a named list of Presidio entity types that is a reasonable
*starting point* for redacting or blocking data covered by a given privacy
law. **Presets are not legal advice.** Whether information is "personal
information" or "personal health information" depends on context; no list
of regexes and NER labels can decide that for you. Review presets with your
privacy officer or counsel and adapt them to your data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["PRESETS", "Preset", "get_preset"]


@dataclass(frozen=True)
class Preset:
    """A named list of entities plus the reasoning behind it."""

    name: str
    title: str
    jurisdiction: str
    law_url: str
    entities: tuple[str, ...]
    languages: tuple[str, ...]
    summary: str
    notes: tuple[str, ...] = field(default_factory=tuple)

    def entity_list(self) -> list[str]:
        """Return the entities as a list (convenient for ``analyzer.analyze``)."""
        return list(self.entities)


_CORE_IDENTITY = (
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CA_SIN",
    "CA_POSTAL_CODE",
    "CA_PASSPORT",
    "CA_DRIVER_LICENSE",
    "CA_HEALTH_NUMBER",
)
_FINANCIAL = ("CREDIT_CARD", "IBAN_CODE", "CA_BANK_ACCOUNT")
_TECHNICAL = ("IP_ADDRESS",)

PIPEDA = Preset(
    name="pipeda",
    title="PIPEDA (federal private sector)",
    jurisdiction="Canada (federal)",
    law_url="https://laws-lois.justice.gc.ca/eng/acts/P-8.6/",
    entities=(*_CORE_IDENTITY, *_FINANCIAL, *_TECHNICAL, "CA_BN"),
    languages=("en", "fr"),
    summary=(
        "Personal Information Protection and Electronic Documents Act. Covers "
        "information about an identifiable individual collected in the course of "
        "commercial activity. The preset targets direct identifiers and "
        "government/financial numbers that are routinely redacted before data "
        "leaves a controlled environment (e.g. before an LLM call)."
    ),
    notes=(
        "CA_BN is included because a sole proprietor's BN can identify an "
        "individual; drop it if you only process incorporated-business data.",
        "LOCATION and DATE_TIME are not included by default: they are noisy, but "
        "addresses and birth dates are personal information - add them if your data "
        "contains them.",
    ),
)

PHIPA = Preset(
    name="phipa",
    title="PHIPA (Ontario health information)",
    jurisdiction="Ontario",
    law_url="https://www.ontario.ca/laws/statute/04p03",
    entities=(
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "DATE_TIME",
        "LOCATION",
        "CA_POSTAL_CODE",
        "CA_HEALTH_NUMBER",
        "CA_SIN",
        "CA_DRIVER_LICENSE",
        "CA_PASSPORT",
        "MEDICAL_LICENSE",
    ),
    languages=("en", "fr"),
    summary=(
        "Personal Health Information Protection Act, 2004. Its definition of "
        "personal health information expressly includes an individual's health "
        "number. The preset is tuned for de-identifying clinical or health-service "
        "text: health numbers (OHIP and other provinces), names, contact details, "
        "dates and locations."
    ),
    notes=(
        "DATE_TIME and LOCATION are included because dates of service/birth and "
        "addresses are classic re-identification vectors in health data; expect "
        "more false positives.",
        "MEDICAL_LICENSE is Presidio's US-oriented built-in; it does not detect "
        "Ontario CPSO numbers (see docs/roadmap.md).",
    ),
)

QUEBEC_LAW25 = Preset(
    name="quebec_law25",
    title="Quebec Law 25 (private sector act, P-39.1)",
    jurisdiction="Quebec",
    law_url="https://www.legisquebec.gouv.qc.ca/en/document/cs/P-39.1",
    entities=(*_CORE_IDENTITY, *_FINANCIAL, *_TECHNICAL, "CA_BN", "DATE_TIME"),
    languages=("fr", "en"),
    summary=(
        "Act respecting the protection of personal information in the private "
        "sector, as amended by Law 25 (2021, c. 25). Personal information is any "
        "information relating to a natural person that allows them to be "
        "identified, directly or indirectly; information of a medical, biometric "
        "or otherwise intimate nature is sensitive. French is listed first because "
        "Quebec data is predominantly French."
    ),
    notes=(
        "The RAMQ health insurance number (NAM) encodes the holder's name initials, "
        "birth date and biological sex, so it is both an identifier and sensitive "
        "information.",
        "DATE_TIME is included because a birth date combined with a name is "
        "identifying; remove it if it causes too much noise.",
        "CA_BN is included for the same reason as in the pipeda preset: "
        "a sole proprietor's BN identifies a natural person.",
    ),
)

PRESETS: dict[str, Preset] = {p.name: p for p in (PIPEDA, PHIPA, QUEBEC_LAW25)}


def get_preset(name: str) -> Preset:
    """Return a preset by name (``pipeda``, ``phipa``, ``quebec_law25``)."""
    key = name.lower().replace("-", "_")
    try:
        return PRESETS[key]
    except KeyError:
        raise KeyError(f"Unknown preset {name!r}; choose one of {sorted(PRESETS)}") from None
