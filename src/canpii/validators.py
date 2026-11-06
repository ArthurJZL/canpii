"""Pure-Python structure and checksum validators for Canadian identifiers.

This module has **no dependency on Presidio** (standard library only) so that
other tools - gateways, ETL jobs, form validators - can reuse the same rules.

Every rule is tagged with the provenance documented in ``docs/entities.md``:

* ``official``  - published by the issuing authority (government / regulator).
* ``secondary`` - published by a reputable third party (e.g. a vendor's DLP
  documentation, an encyclopaedia), but not by the issuer.
* ``community`` - widely implemented in open-source / EMR software, but no
  authoritative publication was found.

Recognizers in this package only *reject* a match based on ``official`` rules.
``secondary`` / ``community`` rules raise confidence when they pass and are
ignored when they fail, unless the recognizer is created with ``strict=True``.

A passing check never means an identifier was *issued*; it only means the
string is structurally plausible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Provenance = Literal["official", "secondary", "community"]

__all__ = [
    "BN_PROGRAM_IDENTIFIERS",
    "Provenance",
    "RamqInfo",
    "ab_phn_structure_valid",
    "bc_dl_structure_valid",
    "bc_phn_check_digit",
    "bc_phn_valid",
    "bn_luhn_valid",
    "bn_structure_valid",
    "digits_only",
    "electronic_routing_structure_valid",
    "luhn_check_digit",
    "luhn_valid",
    "micr_transit_structure_valid",
    "ohip_luhn_valid",
    "ohip_structure_valid",
    "on_dl_birthdate_plausible",
    "on_dl_structure_valid",
    "passport_structure_valid",
    "qc_dl_structure_valid",
    "ramq_parse",
    "ramq_valid",
    "split_bn",
]

_SEPARATORS = re.compile(r"[\s\-.]")


def digits_only(text: str) -> str:
    """Return only the ASCII digits contained in ``text``."""
    return "".join(c for c in text if "0" <= c <= "9")


def _compact(text: str) -> str:
    """Remove spaces, dashes and dots, and upper-case the result."""
    return _SEPARATORS.sub("", text).upper()


# --------------------------------------------------------------------------
# Generic checksums
# --------------------------------------------------------------------------


def luhn_valid(digits: str) -> bool:
    """Return True if ``digits`` (digits only) passes the Luhn (mod 10) check."""
    if not digits or not digits.isdigit():
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def luhn_check_digit(partial: str) -> str:
    """Return the Luhn check digit to append to ``partial`` (digits only)."""
    for d in "0123456789":
        if luhn_valid(partial + d):
            return d
    raise ValueError("partial must contain only digits")  # pragma: no cover


# --------------------------------------------------------------------------
# Health numbers
# --------------------------------------------------------------------------

# Ontario OHIP. 10-digit health number: official (MOH Health Card Validation
# Reference Manual). Optional 1-2 letter version code: official (same manual).
# Luhn check digit: community-sourced only (EMR software); not published by MOH.
_OHIP_RE = re.compile(r"^(\d{10})([A-Z]{1,2})?$")


def ohip_structure_valid(text: str) -> bool:
    """10 digits, optionally followed by a 1-2 letter version code. [official]"""
    return _OHIP_RE.match(_compact(text)) is not None


def ohip_luhn_valid(text: str) -> bool:
    """Luhn over the 10 digits of the health number. [community]"""
    m = _OHIP_RE.match(_compact(text))
    return bool(m) and luhn_valid(m.group(1))


# British Columbia PHN: 10 digits, first digit 9, MOD-11 check digit with
# weights 2,4,8,5,10,9,7,3 on digits 2-9. [official] BC Ministry of Health,
# Conformance Standards Vol. 4B, section 1.3 (Table 13).
_BC_PHN_WEIGHTS = (2, 4, 8, 5, 10, 9, 7, 3)


def bc_phn_check_digit(first_nine: str) -> int | None:
    """Return the BC PHN check digit for the first nine digits, or None.

    ``None`` means no valid PHN can be formed with this prefix (the computed
    value would be 10 or 11).
    """
    if len(first_nine) != 9 or not first_nine.isdigit() or first_nine[0] != "9":
        return None
    total = sum((int(d) * w) % 11 for d, w in zip(first_nine[1:], _BC_PHN_WEIGHTS, strict=True))
    check = 11 - (total % 11)
    return check if check <= 9 else None


def bc_phn_valid(text: str) -> bool:
    """Validate a BC Personal Health Number (structure + MOD-11). [official]"""
    digits = _compact(text)
    if len(digits) != 10 or not digits.isdigit():
        return False
    check = bc_phn_check_digit(digits[:9])
    return check is not None and check == int(digits[9])


def ab_phn_structure_valid(text: str) -> bool:
    """Alberta PHN: exactly 9 digits. [official] (no checksum is published)."""
    digits = _compact(text)
    return len(digits) == 9 and digits.isdigit()


@dataclass(frozen=True)
class RamqInfo:
    """Parsed structure of a Quebec RAMQ health insurance number (NAM)."""

    letters: str
    birth_year_2d: int
    birth_month: int
    birth_day: int
    female: bool
    admin_code: str


_RAMQ_RE = re.compile(r"^([A-Z]{4})(\d{2})(\d{2})(\d{2})(\d{2})$")
_DAYS_IN_MONTH = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _plausible_day(month: int, day: int) -> bool:
    # February accepts 29 because the century (and therefore leap year) of a
    # two-digit year is unknown.
    return 1 <= month <= 12 and 1 <= day <= _DAYS_IN_MONTH[month - 1]


def ramq_parse(text: str) -> RamqInfo | None:
    """Parse a RAMQ NAM into its documented components, or return None.

    Structure [official, Quebec MSSS]: first three letters of the surname,
    first letter of the given name, last two digits of the birth year, birth
    month (+50 for biological sex female), birth day, RAMQ administrative code.
    """
    m = _RAMQ_RE.match(_compact(text))
    if not m:
        return None
    letters, yy, mm, dd, admin = m.groups()
    month = int(mm)
    female = month > 50
    if female:
        month -= 50
    day = int(dd)
    if not _plausible_day(month, day):
        return None
    return RamqInfo(letters, int(yy), month, day, female, admin)


def ramq_valid(text: str) -> bool:
    """Return True if ``text`` has a structurally valid RAMQ NAM. [official]"""
    return ramq_parse(text) is not None


# --------------------------------------------------------------------------
# Passport
# --------------------------------------------------------------------------

_PASSPORT_RE = re.compile(r"^[A-Z]{2}\d{6}$")


def passport_structure_valid(text: str) -> bool:
    """Two letters followed by six digits. [secondary] (Microsoft Purview)."""
    return _PASSPORT_RE.match(_compact(text)) is not None


# --------------------------------------------------------------------------
# Business Number (CRA)
# --------------------------------------------------------------------------

# Program identifiers [official]: CRA, "Program accounts you may need".
BN_PROGRAM_IDENTIFIERS: frozenset[str] = frozenset(
    {"RT", "RP", "RC", "RZ", "RR", "RG", "RD", "RE", "RM", "RN", "LT", "RU", "PT"}
)
_BN_RE = re.compile(r"^(\d{9})(?:([A-Z]{2})(\d{4}))?$")


def split_bn(text: str) -> tuple[str, str | None, str | None] | None:
    """Split ``123456789 RT 0001`` into ``("123456789", "RT", "0001")``."""
    m = _BN_RE.match(_compact(text))
    if not m:
        return None
    bn, program, ref = m.groups()
    return bn, program, ref


def bn_structure_valid(text: str) -> bool:
    """9-digit BN, optionally + known program identifier + 4 digits. [official]"""
    parts = split_bn(text)
    if parts is None:
        return False
    _, program, _ = parts
    return program is None or program in BN_PROGRAM_IDENTIFIERS


def bn_luhn_valid(text: str) -> bool:
    """Luhn over the 9-digit BN root. [community] (not published by CRA)."""
    parts = split_bn(text)
    return parts is not None and luhn_valid(parts[0])


# --------------------------------------------------------------------------
# Bank routing (Payments Canada)
# --------------------------------------------------------------------------

_MICR_RE = re.compile(r"^(\d{5})-(\d{3})$")


def micr_transit_structure_valid(text: str) -> bool:
    """``TTTTT-III``: 5-digit branch + dash + 3-digit institution. [official]

    Payments Canada Standard 006, section 4.4.3.
    """
    return _MICR_RE.match(text.strip()) is not None


def electronic_routing_structure_valid(text: str) -> bool:
    """``0IIITTTTT``: leading zero + institution + transit. [secondary]"""
    digits = _compact(text)
    return len(digits) == 9 and digits.isdigit() and digits[0] == "0"


# --------------------------------------------------------------------------
# Driver's licences
# --------------------------------------------------------------------------

_ON_DL_RE = re.compile(r"^[A-Z]\d{14}$")


def on_dl_structure_valid(text: str) -> bool:
    """Ontario: one letter followed by 14 digits. [secondary] (Purview)."""
    return _ON_DL_RE.match(_compact(text)) is not None


def on_dl_birthdate_plausible(text: str) -> bool:
    """Last six digits read as YYMMDD (month +50 for female). [community]

    Corroborated by the digit constraints in Microsoft Purview's Ontario
    driver's licence definition; not published by the Ontario MTO.
    """
    compact = _compact(text)
    if _ON_DL_RE.match(compact) is None:
        return False
    month = int(compact[-4:-2])
    day = int(compact[-2:])
    if month > 50:
        month -= 50
    return _plausible_day(month, day)


_QC_DL_RE = re.compile(r"^[A-Z]\d{12}$")


def qc_dl_structure_valid(text: str) -> bool:
    """Quebec: one letter followed by 12 digits. [secondary] (Purview)."""
    return _QC_DL_RE.match(_compact(text)) is not None


def bc_dl_structure_valid(text: str) -> bool:
    """British Columbia: 7 digits. [secondary] (Purview)."""
    digits = _compact(text)
    return len(digits) == 7 and digits.isdigit()
